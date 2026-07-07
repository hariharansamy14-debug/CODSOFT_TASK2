# Database Design

## Entity-Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ UPLOADS : "makes"
    USERS ||--o{ AUDIT_LOGS : "generates"
    USERS ||--o{ DEDUPLICATION_HISTORY : "performs"
    USERS ||--o{ REPORTS : "generates"
    UPLOADS ||--o{ FILES : "contains"
    UPLOADS ||--o{ REPORTS : "summarized by"
    FILES ||--o{ VALIDATION_LOGS : "has issues"
    FILES ||--o{ DUPLICATE_LOGS : "has duplicates"
    DUPLICATE_LOGS ||--o{ DEDUPLICATION_HISTORY : "resolved by"

    USERS {
        int id PK
        string full_name
        string email UK
        string password_hash
        enum role
        boolean is_active
    }
    UPLOADS {
        int id PK
        int user_id FK
        string upload_name
        int total_files
        int total_records
        int duplicate_records
        int unique_records
        enum status
    }
    FILES {
        int id PK
        int upload_id FK
        string original_filename
        string stored_filename UK
        string storage_path
        enum storage_type
        enum file_type
        string checksum_sha256
    }
    VALIDATION_LOGS {
        int id PK
        int file_id FK
        int row_number
        string field_name
        enum issue_type
    }
    DUPLICATE_LOGS {
        int id PK
        int file_id FK
        int new_row_number
        string match_field
        enum detection_method
        decimal similarity_score
        enum status
    }
    DEDUPLICATION_HISTORY {
        int id PK
        int duplicate_log_id FK
        enum action_taken
        int performed_by FK
    }
    REPORTS {
        int id PK
        int upload_id FK
        enum report_type
        string file_path
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string details
    }
```

## Why this shape?

**One upload -> many files -> many validation/duplicate rows.** A user might drag-and-drop
5 CSVs at once. We don't want to re-ask "which user uploaded this?" on every single file row,
so that fact lives once, on `uploads`, and everything else hangs off it. This is what
**3rd Normal Form (3NF)** means in practice: every column in a table depends on that table's
primary key, the whole key, and nothing else.

**Why `duplicate_logs` is separate from `validation_logs`.** They answer different questions:
validation asks "is this row well-formed?" (missing email, bad phone format), duplication asks
"have I seen this data before?". Keeping them apart means each table stays small, fast to query,
and easy to reason about — you can generate a "validation report" or a "duplicate report"
independently.

**Why `deduplication_history` is separate from `duplicate_logs`.** `duplicate_logs.status`
tells you the *current* state of a duplicate (pending/merged/ignored/...). But if an admin
later asks "who deleted this record and when?", you need history, not just current state.
Splitting "current state" from "history of changes" is a common and important pattern —
it's the same idea behind audit trails in banking and healthcare systems.

## Indexes — why these specifically

| Table | Index | Reason |
|---|---|---|
| users | `email` | Every login looks up by email — without an index this becomes a full table scan as users grow |
| uploads | `user_id`, `created_at` | Dashboard queries are always "this user's uploads, newest first" |
| files | `checksum_sha256` | Lets us answer "has this exact file been uploaded before?" in O(1) instead of scanning file contents |
| duplicate_logs | `status` | The UI constantly filters "show me only *pending* duplicates" |
| audit_logs | `user_id`, `created_at` | Security audits query "what did user X do, and when?" |

## Normalization note

We stop at 3NF (not push to BCNF/4NF) deliberately — this is a **practical engineering
tradeoff**. Going further would split tables in ways that require more JOINs for the
dashboard's most common queries, hurting read performance for very little real-world benefit
here, since we have no columns that violate BCNF in this schema.
