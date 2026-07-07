"""
config.py
=========
WHY THIS FILE EXISTS:
Hardcoding database passwords or secret keys directly in code is a serious
security mistake (they'd end up in Git history forever). Instead, every
secret/setting is read from environment variables (loaded from a `.env` file
in development, or from real environment variables in production/Docker).

This single Config class is imported by the app factory (`app/__init__.py`)
so there is exactly ONE place to look when you need to change a setting.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load variables from a .env file into the process environment.
# In production (Docker/cloud), real env vars are injected instead and this
# call is harmless (it just does nothing if no .env file is found).
load_dotenv()


class Config:
    # --- Flask core ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # --- MySQL connection string ---
    # SQLAlchemy needs one "connection URI" string. We build it from the
    # individual pieces in .env so no one has to hand-assemble it.
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "cloud_dedup_db")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # disables a feature we don't use; saves memory

    # --- Connection pooling (Performance Optimization requirement #16) ---
    # Instead of opening a brand-new MySQL connection for every request
    # (slow!), SQLAlchemy keeps a "pool" of already-open connections ready
    # to reuse.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,        # keep 10 connections open and ready
        "max_overflow": 20,     # allow up to 20 more under heavy load
        "pool_recycle": 280,    # recycle connections before MySQL's 300s timeout drops them
        "pool_pre_ping": True,  # test a connection is alive before using it (avoids stale-connection errors)
    }

    # --- JWT Authentication ---
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 30))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 30))
    )

    # --- File storage ---
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")  # "local" or "s3"
    LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "./storage/uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload size (secure file upload requirement)
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json", "txt"}

    # --- AWS S3 (kept ready for later, unused while STORAGE_BACKEND=local) ---
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "")

    # --- Redis (caching + Celery background jobs) ---
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # --- Rate limiting ---
    # Defaults to in-memory storage so the app runs out-of-the-box without
    # Redis for local development/testing. In production, set
    # RATELIMIT_STORAGE_URI=redis://... so limits are shared across
    # multiple gunicorn worker processes (an in-memory limiter is PER
    # PROCESS, so it under-counts requests once you have >1 worker).
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = "200 per hour"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    """Used by pytest -- points at SQLite in-memory so tests never touch real MySQL data."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}  # SQLite's default pool doesn't accept MySQL-style pool options
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


# Maps the FLASK_ENV string to the right config class
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
