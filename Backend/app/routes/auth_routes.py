"""
routes/auth_routes.py
======================
Every route here is deliberately thin: it (1) validates input shape,
(2) calls a model/service to do the real work, (3) returns JSON. Business
logic (password hashing, token creation) lives in the User model and
Flask-JWT-Extended -- routes just orchestrate.
"""

import re
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt,
)

from app.extensions import db, limiter, revoked_tokens
from app.models import User
from app.services import audit_service

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")  # slow down bot sign-up spam
def register():
    """
    POST /api/auth/register
    Body: { "full_name": str, "email": str, "password": str }
    """
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # --- Input Validation (Security requirement #15) ---
    if not full_name or not email or not password:
        return jsonify({"success": False, "error": "full_name, email and password are required"}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({"success": False, "error": "Invalid email format"}), 400
    if len(password) < 8:
        return jsonify({"success": False, "error": "Password must be at least 8 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "Email already registered"}), 409

    user = User(full_name=full_name, email=email)
    user.set_password(password)   # hashes the password -- never store raw text
    db.session.add(user)
    db.session.commit()

    audit_service.record(user.id, "REGISTER", f"New account created: {email}")
    return jsonify({"success": True, "data": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")  # brute-force login protection
def login():
    """
    POST /api/auth/login
    Body: { "email": str, "password": str }
    Returns JWT access + refresh tokens on success.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    # Deliberately generic error message ("Invalid credentials") for both
    # "no such user" and "wrong password" -- specific messages let an
    # attacker enumerate which emails are registered.
    if not user or not user.check_password(password):
        audit_service.record(None, "LOGIN_FAILED", f"Failed login attempt for {email}")
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    if not user.is_active:
        return jsonify({"success": False, "error": "Account is disabled"}), 403

    # `identity` becomes `get_jwt_identity()` on every future request.
    # We also stash the role as a custom claim so routes can check
    # permissions without another DB query.
    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    refresh_token = create_refresh_token(identity=str(user.id))

    audit_service.record(user.id, "LOGIN_SUCCESS")
    return jsonify({
        "success": True,
        "data": {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """POST /api/auth/refresh -- exchange a valid refresh token for a new access token."""
    identity = get_jwt_identity()
    user = User.query.get(identity)
    new_access_token = create_access_token(identity=identity, additional_claims={"role": user.role})
    return jsonify({"success": True, "data": {"access_token": new_access_token}}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    POST /api/auth/logout
    JWTs are stateless by design (the server doesn't normally track them),
    so "logout" means adding this token's unique ID (jti) to a revocation
    list that jwt_required() checks on every request (see extensions setup).
    """
    jti = get_jwt()["jti"]
    revoked_tokens.add(jti)
    audit_service.record(get_jwt_identity(), "LOGOUT")
    return jsonify({"success": True, "message": "Logged out"}), 200


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    """
    POST /api/auth/forgot-password
    Body: { "email": str }
    Generates a one-time reset token. In production this triggers an email
    (see services/notification_service.py); here we return it directly only
    because there's no mail server configured in local dev.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()

    # Always respond success, even if the email doesn't exist -- otherwise
    # this endpoint becomes a way to check which emails are registered.
    if user:
        user.reset_token = secrets.token_urlsafe(32)
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        audit_service.record(user.id, "PASSWORD_RESET_REQUESTED")
        # notification_service.send_password_reset_email(user, user.reset_token)

    return jsonify({"success": True, "message": "If that email exists, a reset link was sent"}), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    POST /api/auth/reset-password
    Body: { "token": str, "new_password": str }
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    new_password = data.get("new_password") or ""

    if len(new_password) < 8:
        return jsonify({"success": False, "error": "Password must be at least 8 characters"}), 400

    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        return jsonify({"success": False, "error": "Invalid or expired reset token"}), 400

    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()

    audit_service.record(user.id, "PASSWORD_RESET_COMPLETED")
    return jsonify({"success": True, "message": "Password reset successful"}), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    """POST /api/auth/change-password -- for a logged-in user changing their own password."""
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    user = User.query.get(get_jwt_identity())
    if not user.check_password(current_password):
        return jsonify({"success": False, "error": "Current password is incorrect"}), 401
    if len(new_password) < 8:
        return jsonify({"success": False, "error": "Password must be at least 8 characters"}), 400

    user.set_password(new_password)
    db.session.commit()
    audit_service.record(user.id, "PASSWORD_CHANGED")
    return jsonify({"success": True, "message": "Password changed successfully"}), 200


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    """GET /api/auth/profile -- the logged-in user's own details."""
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    return jsonify({"success": True, "data": user.to_dict()}), 200


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """PUT /api/auth/profile -- update full_name (email changes intentionally excluded for simplicity/security)."""
    data = request.get_json(silent=True) or {}
    user = User.query.get(get_jwt_identity())

    full_name = (data.get("full_name") or "").strip()
    if full_name:
        user.full_name = full_name
        db.session.commit()

    return jsonify({"success": True, "data": user.to_dict()}), 200
