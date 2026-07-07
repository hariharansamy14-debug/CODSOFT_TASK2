"""
extensions.py
=============
WHY THIS FILE EXISTS:
Flask extensions like SQLAlchemy or JWTManager need to be created as objects,
but they must NOT be tied to a specific Flask app when first created -- that
happens later via `.init_app(app)` in the app factory. This avoids a classic
Python problem called a "circular import": models.py needs `db`, routes need
`db` too, and app/__init__.py needs both models and routes. By putting the
bare extension objects in their own file with no other imports, everyone can
safely `from app.extensions import db` without import loops.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()             # the ORM: turns Python classes into MySQL tables/rows
jwt = JWTManager()            # issues/validates JWT tokens for authentication
cors = CORS()                 # lets the React frontend (different origin) call this API
limiter = Limiter(key_func=get_remote_address)  # rate limiting, keyed by requester's IP

# --- JWT revocation set (for logout) ---
# NOTE: a plain Python set only works because we run ONE server process in
# dev. In production (multiple gunicorn workers/containers), this MUST be
# backed by Redis instead, or logout on worker A won't affect worker B.
# See Docs/deployment_guide.md for the Redis-backed version.
revoked_tokens: set = set()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """Called automatically by Flask-JWT-Extended on every @jwt_required() route."""
    return jwt_payload["jti"] in revoked_tokens
