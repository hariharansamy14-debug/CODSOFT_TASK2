-- ============================================================================
-- Cloud Data Deduplication System - MySQL Database Schema
-- ============================================================================
-- WHY THIS DESIGN?
-- We use 3rd Normal Form (3NF) normalization: every table stores facts about
-- ONE entity only, and every non-key column depends on the whole primary key
-- and nothing but the key. This avoids storing the same fact twice (which is
-- ironic to get wrong in a system whose whole job is removing duplicates!).
--
-- Relationships (high level):
--   users (1) ----< uploads (many)          a user makes many uploads
--   uploads (1) ----< files (many)           an upload can contain many files
--   files (1) ----< validation_logs (many)   each file gets validated row by row
--   files (1) ----< duplicate_logs (many)    each file can have many dup findings
--   duplicate_logs (1) --- deduplication_history (1..many) actions taken on a dup
--   uploads (1) ----< reports (many)         a report summarizes one upload
--   users (1) ----< audit_logs (many)        every user action is audited
-- ============================================================================

CREATE DATABASE IF NOT EXISTS cloud_dedup_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE cloud_dedup_db;

-- ----------------------------------------------------------------------------
-- Table: users
-- Stores login credentials and profile info. Passwords are NEVER stored in
-- plain text -- only a bcrypt hash (see backend `password_service.py`).
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    full_name           VARCHAR(150)  NOT NULL,
    email               VARCHAR(150)  NOT NULL UNIQUE,
    password_hash       VARCHAR(255)  NOT NULL,       -- bcrypt hash, not raw password
    role                ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    is_active           BOOLEAN       NOT NULL DEFAULT TRUE,
    reset_token         VARCHAR(255)  NULL,            -- for "forgot password" flow
    reset_token_expiry  DATETIME      NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                       ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_users_email (email)                     -- login is always by email -> index it
);

-- ----------------------------------------------------------------------------
-- Table: uploads
-- One row per "upload session" (a user may upload several files at once,
-- e.g. drag-and-drop of 5 CSVs -> that is ONE upload with 5 file rows).
-- ----------------------------------------------------------------------------
CREATE TABLE uploads (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT           NOT NULL,
    upload_name         VARCHAR(255)  NOT NULL,        -- friendly label, e.g. "March Payroll"
    total_files         INT           NOT NULL DEFAULT 0,
    total_records        INT           NOT NULL DEFAULT 0,
    duplicate_records    INT           NOT NULL DEFAULT 0,
    unique_records       INT           NOT NULL DEFAULT 0,
    status              ENUM('processing','completed','failed') NOT NULL DEFAULT 'processing',
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_uploads_user (user_id),
    INDEX idx_uploads_created (created_at)             -- dashboard sorts/filters by date
);

-- ----------------------------------------------------------------------------
-- Table: files
-- One row per physical file inside an upload (CSV/Excel/JSON/TXT).
-- ----------------------------------------------------------------------------
CREATE TABLE files (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    upload_id           INT           NOT NULL,
    original_filename   VARCHAR(255)  NOT NULL,
    stored_filename     VARCHAR(255)  NOT NULL UNIQUE, -- UUID-based unique name on disk/S3
    storage_path        VARCHAR(500)  NOT NULL,        -- local path OR S3 key
    storage_type        ENUM('local','s3') NOT NULL DEFAULT 'local',
    file_type           ENUM('csv','xlsx','json','txt') NOT NULL,
    file_size_bytes     BIGINT        NOT NULL DEFAULT 0,
    record_count        INT           NOT NULL DEFAULT 0,
    checksum_sha256     CHAR(64)      NULL,            -- whole-file hash (detect identical re-uploads)
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
    INDEX idx_files_upload (upload_id),
    INDEX idx_files_checksum (checksum_sha256)          -- instant "is this exact file already here?" check
);

-- ----------------------------------------------------------------------------
-- Table: validation_logs
-- One row per validation ISSUE found in a record (not per record -- a clean
-- record produces zero rows here, keeping the table small).
-- ----------------------------------------------------------------------------
CREATE TABLE validation_logs (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    file_id             INT           NOT NULL,
    row_number           INT           NOT NULL,
    field_name          VARCHAR(100)  NOT NULL,
    issue_type          ENUM('missing_value','invalid_email','invalid_phone',
                              'invalid_date','null_value','extra_spaces',
                              'special_characters','invalid_type') NOT NULL,
    raw_value           TEXT          NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    INDEX idx_validation_file (file_id)
);

-- ----------------------------------------------------------------------------
-- Table: duplicate_logs
-- One row per duplicate PAIR found (candidate record vs. the existing record
-- it matches). Stores which algorithm found it and how confident it is.
-- ----------------------------------------------------------------------------
CREATE TABLE duplicate_logs (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    file_id             INT           NOT NULL,
    new_row_number       INT           NOT NULL,        -- row in the newly uploaded file
    existing_record_ref  VARCHAR(255)  NULL,            -- pointer to the pre-existing record
    match_field          VARCHAR(100)  NOT NULL,        -- e.g. "email", "employee_id"
    detection_method     ENUM('exact','sha256','md5','levenshtein',
                               'jaccard','cosine','soundex','metaphone') NOT NULL,
    similarity_score     DECIMAL(5,4)  NOT NULL DEFAULT 1.0000,  -- 1.0 = exact match
    status               ENUM('pending','merged','replaced','ignored',
                               'deleted','kept_latest','kept_oldest') NOT NULL DEFAULT 'pending',
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    INDEX idx_duplicate_file (file_id),
    INDEX idx_duplicate_status (status)
);

-- ----------------------------------------------------------------------------
-- Table: deduplication_history
-- Immutable audit trail: every ACTION taken on a duplicate_logs row. We keep
-- duplicate_logs.status as "current state" and this table as "full history",
-- so an admin can always see who changed what and when.
-- ----------------------------------------------------------------------------
CREATE TABLE deduplication_history (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    duplicate_log_id    INT           NOT NULL,
    action_taken        ENUM('merge','replace','ignore','delete',
                              'keep_latest','keep_oldest','auto') NOT NULL,
    performed_by        INT           NULL,             -- NULL = system/auto action
    notes               VARCHAR(500)  NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (duplicate_log_id) REFERENCES duplicate_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_dedup_history_log (duplicate_log_id)
);

-- ----------------------------------------------------------------------------
-- Table: reports
-- Generated report artifacts (PDF/Excel/CSV) tied to an upload.
-- ----------------------------------------------------------------------------
CREATE TABLE reports (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    upload_id           INT           NOT NULL,
    report_type         ENUM('pdf','xlsx','csv') NOT NULL,
    file_path           VARCHAR(500)  NOT NULL,
    generated_by        INT           NOT NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_reports_upload (upload_id)
);

-- ----------------------------------------------------------------------------
-- Table: audit_logs
-- Generic "who did what, when" log for security/compliance. Separate from
-- deduplication_history because this covers ALL actions (login, delete user,
-- upload, etc.), not just dedup decisions.
-- ----------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT           NULL,
    action              VARCHAR(100)  NOT NULL,          -- e.g. "LOGIN", "UPLOAD_FILE", "DELETE_USER"
    details             TEXT          NULL,
    ip_address          VARCHAR(45)   NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_created (created_at)
);
