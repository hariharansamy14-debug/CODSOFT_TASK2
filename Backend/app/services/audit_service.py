"""
services/audit_service.py
==========================
A tiny helper so that logging "who did what" is a ONE-LINE call from any
route, instead of every route manually building an AuditLog row. This is
the DRY (Don't Repeat Yourself) principle in action.
"""

from flask import request
from app.extensions import db
from app.models import AuditLog


def record(user_id, action: str, details: str = None):
    """
    Writes one row to audit_logs. Called after logins, uploads, deletions,
    duplicate resolutions, etc.

    Args:
        user_id: the acting user's id, or None for anonymous/system actions.
        action: short machine-readable label, e.g. "LOGIN_SUCCESS", "UPLOAD_FILE".
        details: optional human-readable context, e.g. "uploaded payroll.csv".
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(entry)
    db.session.commit()
