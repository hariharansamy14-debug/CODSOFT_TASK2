"""
wsgi.py
=======
Production entry point. gunicorn is told to run `wsgi:app` (see
Docker/Dockerfile.backend's CMD) instead of Flask's dev server, because
Flask's built-in server is single-threaded and not hardened for real
traffic -- gunicorn manages multiple worker processes properly.
"""

from app import create_app

app = create_app("production")
