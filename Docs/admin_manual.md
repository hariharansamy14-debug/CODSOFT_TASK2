# Admin Manual

Admin routes live under `/api/admin` and require a user account with
`role = 'admin'`. There's no self-service way to become an admin (by
design — see Security section below) — promote a user directly in MySQL:

```sql
UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
```

## What admins can do

### View and manage users
`GET /api/admin/users` lists every registered account. `DELETE
/api/admin/users/<id>` removes a user and (via cascading deletes) all
their uploads, files, and logs — this is destructive and cannot be undone,
so confirm before calling it from any admin UI you build on top of this API.

### View all uploads platform-wide
`GET /api/admin/uploads` lists every upload from every user — useful for
spotting unusually large uploads or users hitting quota issues.

### Storage statistics
`GET /api/admin/storage-stats` returns platform totals: total users, total
uploads, total records, total duplicates found, and total estimated
storage saved. Good for a "platform health" dashboard.

### Activity / audit logs
`GET /api/admin/activity-logs?user_id=<optional>` returns the full audit
trail (every login, upload, deletion, and duplicate resolution across the
platform), optionally filtered to one user. Useful for investigating
"who deleted this record?" or spotting repeated failed login attempts
(`action = "LOGIN_FAILED"`) that might indicate a brute-force attempt.

## Security notes for admins

- Every admin route is protected by `@admin_required` (see
  `app/middleware/rbac.py`), which checks the `role` claim embedded in the
  JWT at login time — a regular user's token is rejected with `403` even
  if they somehow reach these URLs directly.
- There is intentionally no API endpoint to promote a user to admin —
  this must be done directly against the database, so that a compromised
  regular-user account can never escalate itself to admin through the API.
- All admin actions that delete data are recorded to `audit_logs` with the
  acting admin's `user_id`, so admin activity is itself auditable.
