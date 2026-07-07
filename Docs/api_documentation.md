# API Documentation

Base URL: `http://localhost:5000/api` (or `/api` behind the nginx proxy in Docker)

All responses follow one shape:
```json
{ "success": true, "data": { ... } }
```
or on error:
```json
{ "success": false, "error": "human readable message" }
```

Authenticated routes require a header: `Authorization: Bearer <access_token>`

---

## Auth — `/api/auth`

### POST `/register`
Body: `{ "full_name": str, "email": str, "password": str (min 8 chars) }`
→ `201` with the created user. `409` if email already registered.

### POST `/login`
Body: `{ "email": str, "password": str }`
→ `200` with `{ user, access_token, refresh_token }`. Rate-limited to 5/minute.

### POST `/refresh` *(requires refresh token)*
→ `200` with a new `access_token`.

### POST `/logout` *(requires access token)*
Revokes the current access token.

### POST `/forgot-password`
Body: `{ "email": str }` → always `200` (doesn't reveal whether the email exists).

### POST `/reset-password`
Body: `{ "token": str, "new_password": str }`

### POST `/change-password` *(auth required)*
Body: `{ "current_password": str, "new_password": str }`

### GET `/profile` *(auth required)* — current user's details.
### PUT `/profile` *(auth required)* — Body: `{ "full_name": str }`

---

## Uploads — `/api/uploads`

### POST `` *(auth required)*
`multipart/form-data`: `files` (one or more), `upload_name` (optional).
Runs the full pipeline: parse → validate → detect duplicates.
→ `201` with `{ upload: {...}, files: [{ file_id, filename, record_count, validation_issues, duplicates_found }] }`

### GET `?page=1&per_page=20` *(auth required)* — paginated upload history.
### GET `/<upload_id>` *(auth required)* — one upload's detail, including files.
### DELETE `/<upload_id>` *(auth required)* — deletes the upload, its files (from storage too), and related logs.

---

## Validation — `/api/validation`

### GET `/file/<file_id>?page=1&per_page=50` *(auth required)* — paginated list of validation issues.
### GET `/file/<file_id>/report` *(auth required)* — issue counts grouped by type.

---

## Duplicates — `/api/duplicates`

### GET `/file/<file_id>?status=pending` *(auth required)*
`status` optional filter: `pending|merged|replaced|ignored|deleted|kept_latest|kept_oldest`

### POST `/<duplicate_id>/resolve` *(auth required)*
Body: `{ "action": "merge"|"replace"|"ignore"|"delete"|"keep_latest"|"keep_oldest", "notes": str (optional) }`

### POST `/file/<file_id>/auto-resolve` *(auth required)*
Automatically resolves every `pending` duplicate with similarity ≥ 0.95.
→ `{ "auto_resolved": int, "left_for_manual_review": int, "threshold_used": float }`

### GET `/<duplicate_id>/history` *(auth required)* — full resolution audit trail.

---

## Dashboard — `/api/dashboard`

### GET `/summary` *(auth required)* — total files/records/duplicates/unique/storage saved.
### GET `/upload-history` *(auth required)* — last 10 uploads.
### GET `/duplicate-trend` *(auth required)* — duplicate counts grouped by detection method (for charts).
### GET `/recent-activity` *(auth required)* — last 15 audit log entries.

---

## Reports — `/api/reports`

### POST `/upload/<upload_id>/generate` *(auth required)*
Body: `{ "format": "pdf"|"xlsx"|"csv" }` → creates and stores a report artifact.

### GET `/<report_id>/download` *(auth required)* — streams the file back.
### GET `/upload/<upload_id>` *(auth required)* — list previously generated reports.

---

## Admin — `/api/admin` *(all routes require `role: admin`)*

### GET `/users?page=1` — every registered user.
### DELETE `/users/<user_id>` — deletes a user and all their data.
### GET `/uploads?page=1` — every upload, across all users.
### GET `/storage-stats` — platform-wide totals.
### GET `/activity-logs?user_id=<optional>` — platform-wide audit trail.

---

## Common error codes

| Code | Meaning |
|---|---|
| 400 | Bad request (missing/invalid fields) |
| 401 | Not authenticated / invalid credentials / expired token |
| 403 | Authenticated but not authorized (e.g. non-admin hitting an admin route) |
| 404 | Resource not found (or not owned by the requesting user) |
| 409 | Conflict (e.g. email already registered) |
| 413 | File too large (over 50 MB) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
