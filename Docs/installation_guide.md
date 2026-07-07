# Installation Guide (Manual Setup)

This walks through running the system WITHOUT Docker — useful for
understanding each moving part before you containerize it. If you just want
it running quickly, use `docker compose up` instead (see main README).

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- MySQL 8.0+ (or use SQLite for a quick local trial — see note below)

## 1. Clone and set up the backend

```bash
cd Backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
- `DB_PASSWORD` — your MySQL root (or app user) password
- `SECRET_KEY` and `JWT_SECRET_KEY` — any long random strings
  (generate one with `python3 -c "import secrets; print(secrets.token_hex(32))"`)

## 3. Create the MySQL database

```bash
mysql -u root -p < ../Database/schema.sql
```

This creates the `cloud_dedup_db` database and all 8 tables (see
`Docs/database_design.md` for the full ER diagram and rationale).

**Quick-trial alternative (no MySQL install needed):** run
`FLASK_ENV=testing python run.py` — this uses an in-memory SQLite database
instead. Fine for kicking the tires; use real MySQL for anything you want
to keep.

## 4. Start the backend

```bash
python run.py
```

Visit http://localhost:5000/api/health — you should see `{"status": "ok", ...}`.

## 5. Set up and start the frontend

In a **new terminal**:

```bash
cd Frontend
npm install
npm run dev
```

Visit http://localhost:5173. The dev server proxies `/api/*` calls to the
backend on port 5000 automatically (see `vite.config.js`).

## 6. Register your first user

Go to http://localhost:5173/register and create an account. The FIRST user
you register is a regular `user` role — to make yourself an `admin`, run:

```sql
UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Access denied for user 'root'@'localhost'` | Double check `DB_PASSWORD` in `.env` matches your actual MySQL password |
| `ModuleNotFoundError` on backend start | Make sure the virtualenv is activated (`source venv/bin/activate`) before `pip install` |
| Frontend shows CORS errors | Confirm you're visiting the Vite dev server URL (5173), not opening `index.html` directly |
| `python-Levenshtein` fails to install | You're missing a C compiler; on Ubuntu: `sudo apt install build-essential python3-dev` |
