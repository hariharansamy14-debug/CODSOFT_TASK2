# Testing Guide

## Running the suite

```bash
cd Backend
pip install -r requirements.txt
pytest -v
```

This runs 37 tests against an **in-memory SQLite database** (see
`config.py`'s `TestingConfig` and `tests/conftest.py`) — your real MySQL
data is never touched by running tests.

Coverage report:
```bash
pytest --cov=app --cov-report=term-missing
```

## What's covered

| File | What it tests |
|---|---|
| `test_auth.py` | Registration validation, duplicate email rejection, login success/failure, JWT-protected routes, logout token revocation |
| `test_validation_service.py` | Every validation rule: missing values, invalid email/phone/date, extra spaces |
| `test_dedup_engine.py` | Every algorithm individually (exact, hash, Levenshtein, Jaccard, cosine, Soundex, Metaphone) PLUS full-engine integration tests |
| `test_upload.py` | The full pipeline end-to-end through the real HTTP API: upload → validate → detect, ownership checks, pagination |

## Test design principles used here

**Fresh database per test.** `conftest.py`'s `app` fixture creates and tears
down all tables for every single test function. This costs a little time
but guarantees one test's leftover data can never silently break another
test — a common source of "works alone, fails in the full suite" bugs.

**Test the real HTTP layer, not just functions.** `test_upload.py` doesn't
call `detect_duplicates()` directly — it POSTs a real multipart file
through `client.post(...)`, exactly like the React frontend would, so a
bug in request parsing or route wiring gets caught too, not just bugs in
the underlying logic.

**One assertion focus per test.** Each test function checks one behavior
(e.g. `test_register_duplicate_email_rejected`), so when a test fails, the
name alone tells you what broke — you don't have to read the test body to
diagnose it.

## Adding a new test

1. If it needs a logged-in user, add `client, auth_headers` as fixture
   parameters — `auth_headers` (from `conftest.py`) already handles
   register + login and returns ready `Authorization` headers.
2. Name the test function `test_<behavior_being_checked>` so failures are
   self-explanatory in CI output.
3. Prefer testing through the API (`client.post(...)`) for anything that
   touches a route; test service functions directly (like
   `test_dedup_engine.py` does) for pure-logic algorithms.

## Manual testing with Postman

Import the endpoints from `Docs/api_documentation.md` into Postman, or:
1. `POST /api/auth/register` → copy the returned user's email
2. `POST /api/auth/login` → copy `access_token`
3. Set a Postman environment variable `token` to that value
4. Add header `Authorization: Bearer {{token}}` to all subsequent requests
5. `POST /api/uploads` with `form-data`, key `files` (type: File), using
   `Docs/sample_dataset.csv`
