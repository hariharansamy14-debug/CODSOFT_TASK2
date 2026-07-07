# Cloud Data Deduplication System

A full-stack application that detects, validates, and removes duplicate data
before it's stored — combining exact, hash-based, fuzzy, and phonetic
matching algorithms behind a REST API and React dashboard.

Built as a learning project: every file is commented to explain not just
*what* the code does, but *why* it's built that way.

## What it does

1. **Upload** CSV / Excel / JSON / TXT files (drag-and-drop, multiple at once).
2. **Validate** every record — missing values, malformed emails/phones/dates,
   extra whitespace, special characters.
3. **Detect duplicates** using six algorithms: exact matching, SHA-256/MD5
   hashing, Levenshtein distance, Jaccard similarity, Cosine similarity
   (TF-IDF), and Soundex/Metaphone phonetic matching.
4. **Resolve** duplicates manually (merge / replace / ignore / delete / keep
   latest / keep oldest) or automatically for high-confidence matches.
5. **Report** on what was found, via PDF/Excel/CSV exports and a live dashboard.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Bootstrap 5, Chart.js |
| Backend | Python, Flask, Flask-JWT-Extended |
| Database | MySQL (production), SQLite (automated tests) |
| Storage | Local disk by default; AWS S3-ready (one config flag) |
| Deployment | Docker, Docker Compose, gunicorn, nginx |
| Testing | Pytest (37 tests covering auth, validation, and every dedup algorithm) |

## Project structure

```
cloud-dedup-system/
├── Backend/            Flask REST API
│   ├── app/
│   │   ├── models/          SQLAlchemy models (mirrors Database/schema.sql)
│   │   ├── routes/          REST API endpoints, grouped by feature
│   │   ├── services/        Business logic (validation, dedup engine, storage, reports)
│   │   │   └── dedup_engine/  The 6 duplicate-detection algorithms + orchestrator
│   │   ├── middleware/      Role-based access control
│   │   └── utils/           File parsing helpers
│   ├── tests/                Pytest suite (37 tests)
│   ├── config.py             Environment-driven configuration
│   ├── requirements.txt
│   └── run.py / wsgi.py      Dev / production entry points
├── Frontend/            React SPA (Vite + Bootstrap 5)
├── Database/            schema.sql (MySQL DDL)
├── Docker/              Dockerfiles + docker-compose.yml
├── Docs/                Every guide listed below
└── Screenshots/         (add your own once you run it locally)
```

## Quickstart (Docker — recommended)

```bash
cd Docker
cp ../Backend/.env.example ../Backend/.env   # then edit DB_PASSWORD, SECRET_KEY, JWT_SECRET_KEY
docker compose up --build
```

- Frontend: http://localhost
- Backend API: http://localhost:5000/api/health
- MySQL: localhost:3306 (schema auto-loads from `Database/schema.sql` on first boot)

## Quickstart (without Docker)

See **[Docs/installation_guide.md](Docs/installation_guide.md)** for full manual setup
(Python venv, MySQL, npm install) — useful if you want to see each moving
part before containerizing it.

## Try it with sample data

`Docs/sample_dataset.csv` contains 10 rows with intentional duplicates:
an exact repeat, a phonetic name match (Robert/Rupert, Catherine/Kathryn),
and near-identical addresses. Upload it after logging in to see all the
detection methods fire in one go.

## Documentation

| Guide | What's in it |
|---|---|
| [Installation Guide](Docs/installation_guide.md) | Manual setup without Docker |
| [Database Design](Docs/database_design.md) | ER diagram, normalization, indexing rationale |
| [API Documentation](Docs/api_documentation.md) | Every endpoint: method, body, response, errors |
| [Algorithm Explanation](Docs/algorithm_explanation.md) | How each dedup algorithm works, complexity, tradeoffs |
| [Deployment Guide](Docs/deployment_guide.md) | Going from Docker Compose to real production |
| [Testing Guide](Docs/testing_guide.md) | Running and extending the pytest suite |
| [User Manual](Docs/user_manual.md) | Using the app as an end user |
| [Admin Manual](Docs/admin_manual.md) | Admin panel walkthrough |

## Running tests

```bash
cd Backend
pip install -r requirements.txt
pytest -v
```

37 tests currently pass, covering authentication, the validation engine,
all six duplicate-detection algorithms individually, and the full
upload → validate → detect pipeline end-to-end via the API.

## Security notes

- Passwords are hashed with bcrypt — never stored in plain text.
- JWT access tokens expire in 30 minutes by default; refresh tokens handle re-auth.
- Every route that touches user data checks that the requesting user actually
  owns that data (see `_authorize_file` / `_authorize_duplicate` helpers).
- Rate limiting is applied to login/register/password-reset to slow brute-force attempts.
- File uploads are restricted by extension and size (50 MB default cap).

## License

MIT — see [LICENSE](LICENSE).
