"""
app/__init__.py
================
This is the "Application Factory" pattern. Instead of creating one giant
global `app = Flask(__name__)` at import time (which makes testing painful
and can cause circular imports), we wrap creation in a function,
`create_app()`. Each call produces a fresh, fully-configured Flask app --
one for running the real server, a different one (with TestingConfig) for
pytest, etc.
"""

import os
from flask import Flask, jsonify
from config import config_by_name
from app.extensions import db, jwt, cors, limiter


def create_app(config_name=None):
    app = Flask(__name__)

    # Decide which config class to use: explicit argument > FLASK_ENV > default
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_by_name[config_name])

    # --- Bind extensions to this specific app instance ---
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})  # tighten origins in production
    limiter.init_app(app)

    # --- Register blueprints (each is one REST API "module") ---
    from app.routes.auth_routes import auth_bp
    from app.routes.upload_routes import upload_bp
    from app.routes.validation_routes import validation_bp
    from app.routes.duplicate_routes import duplicate_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.report_routes import report_bp
    from app.routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(upload_bp, url_prefix="/api/uploads")
    app.register_blueprint(validation_bp, url_prefix="/api/validation")
    app.register_blueprint(duplicate_bp, url_prefix="/api/duplicates")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(report_bp, url_prefix="/api/reports")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # --- Make sure the local upload folder exists ---
    os.makedirs(app.config["LOCAL_STORAGE_PATH"], exist_ok=True)

    # --- Global error handlers so the API always returns clean JSON,
    #     never an HTML stack-trace page (important for a REST API) ---
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Resource not found"}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"success": False, "error": "File too large"}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    @app.route("/api/health")
    def health_check():
        """Simple endpoint to verify the API is running (used by Docker healthchecks)."""
        return jsonify({"status": "ok", "service": "cloud-dedup-backend"})

    return app
