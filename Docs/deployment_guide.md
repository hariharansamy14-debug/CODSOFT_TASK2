# Deployment Guide

`docker compose up` (see main README) gets the full stack running locally
or on a single server. This guide covers what to change for a real
production deployment.

## 1. Secrets

Never use the `.env.example` placeholder values in production.
- Generate real secrets: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- In cloud environments, prefer a secrets manager (AWS Secrets Manager, GCP
  Secret Manager, HashiCorp Vault) over a `.env` file baked into the image.

## 2. Switch to AWS S3 storage

The storage layer (`app/services/storage_service.py`) already supports S3 —
it's a config flip, not a code change:

```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
```

Recommended bucket setup: enable versioning, block public access, and set a
lifecycle rule if you want old uploaded files auto-archived to cheaper
storage classes after N days.

## 3. Multi-worker JWT revocation

`app/extensions.py`'s `revoked_tokens` set is an in-memory Python set — it
only works correctly with ONE gunicorn worker process, because "logout" on
worker A's memory doesn't affect worker B. For production with multiple
workers/containers, replace it with Redis:

```python
# extensions.py (production version)
import redis
redis_client = redis.from_url(os.getenv("REDIS_URL"))

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return redis_client.exists(f"revoked:{jwt_payload['jti']}") == 1

# and in auth_routes.py's logout():
redis_client.setex(f"revoked:{jti}", app.config["JWT_ACCESS_TOKEN_EXPIRES"], "1")
```

## 4. Rate limiter storage

Same issue as above — switch `RATELIMIT_STORAGE_URI` from `memory://` to
`redis://<your-redis-host>:6379/1` so limits are enforced correctly across
multiple worker processes.

## 5. MySQL

- Use a managed MySQL service (AWS RDS, GCP Cloud SQL) rather than the
  `mysql:8.0` container in `docker-compose.yml` for anything beyond a demo —
  you get automated backups, failover, and patching.
- Run `Database/schema.sql` once against the managed instance, then point
  `DB_HOST`/`DB_USER`/`DB_PASSWORD` at it.
- Enable automated backups and point-in-time recovery.

## 6. HTTPS

Terminate TLS in front of nginx (a load balancer, Cloudflare, or
Let's Encrypt via certbot) — never serve production traffic over plain HTTP.
Update `Docker/nginx.conf` to redirect HTTP → HTTPS once you have a certificate.

## 7. CORS

`app/__init__.py` currently allows `origins: "*"` for convenience during
development. In production, restrict this to your actual frontend domain:

```python
cors.init_app(app, resources={r"/api/*": {"origins": "https://your-domain.com"}})
```

## 8. Logging & monitoring

- Ship gunicorn/Flask logs to a centralized log system (CloudWatch, Datadog,
  ELK) rather than relying on `docker logs`.
- The `audit_logs` table already captures security-relevant events
  (logins, uploads, deletions, resolutions) — consider alerting on spikes
  in `LOGIN_FAILED` entries (possible brute-force attempts).

## 9. Background processing for large files

Right now, duplicate detection runs synchronously inside the upload
request — fine for files with a few thousand rows, but a 500,000-row CSV
would time out an HTTP request. `requirements.txt` already includes Celery
+ Redis for exactly this: move the `parse → validate → detect` pipeline in
`upload_routes.py` into a Celery task, return `202 Accepted` immediately
with a job ID, and let the frontend poll (or use a websocket) for completion.

## 10. Zero-downtime deploys

With multiple gunicorn workers behind a load balancer, deploy new code by
spinning up new containers, waiting for their `/api/health` checks to pass,
then draining traffic from the old containers — avoids any user-facing
downtime during a release.
