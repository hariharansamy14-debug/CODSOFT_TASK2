"""
middleware/rbac.py
====================
Role-Based Access Control (Security requirement #15). JWTs carry a "role"
claim (set at login time in auth_routes.py). This decorator checks that
claim BEFORE the route function runs at all, so admin-only endpoints can't
be reached by a regular "user" role no matter what they send.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"success": False, "error": "Admin privileges required"}), 403
        return fn(*args, **kwargs)
    return wrapper
