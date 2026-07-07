"""
routes/admin_routes.py
========================
Every route here is protected by @admin_required (RBAC) on top of the
normal JWT check -- a regular "user"-role account gets a 403 even with a
perfectly valid token.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import User, Upload, AuditLog
from app.middleware.rbac import admin_required
from app.services import audit_service, storage_service

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """GET /api/admin/users -- view all registered users."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    pagination = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "success": True,
        "data": [u.to_dict() for u in pagination.items],
        "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
    }), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """DELETE /api/admin/users/<id> -- removes a user and (via cascade) all their uploads/files."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    for upload in user.uploads:
        for file_row in upload.files:
            storage_service.delete_file(file_row.storage_path, file_row.storage_type)

    db.session.delete(user)
    db.session.commit()

    audit_service.record(int(get_jwt_identity()), "ADMIN_DELETE_USER", f"Deleted user #{user_id} ({user.email})")
    return jsonify({"success": True, "message": "User deleted"}), 200


@admin_bp.route("/uploads", methods=["GET"])
@admin_required
def list_all_uploads():
    """GET /api/admin/uploads -- every upload across every user, for platform-wide monitoring."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    pagination = Upload.query.order_by(Upload.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "success": True,
        "data": [u.to_dict() for u in pagination.items],
        "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
    }), 200


@admin_bp.route("/storage-stats", methods=["GET"])
@admin_required
def storage_stats():
    """GET /api/admin/storage-stats -- platform-wide storage totals and savings."""
    uploads = Upload.query.all()
    total_records = sum(u.total_records for u in uploads)
    total_duplicates = sum(u.duplicate_records for u in uploads)
    total_storage_saved = sum(u.storage_saved_bytes() for u in uploads)

    return jsonify({
        "success": True,
        "data": {
            "total_users": User.query.count(),
            "total_uploads": len(uploads),
            "total_records": total_records,
            "total_duplicates": total_duplicates,
            "total_storage_saved_bytes": total_storage_saved,
        },
    }), 200


@admin_bp.route("/activity-logs", methods=["GET"])
@admin_required
def activity_logs():
    """GET /api/admin/activity-logs -- platform-wide audit trail (Search & Filter: by user, date)."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    query = AuditLog.query

    user_id_filter = request.args.get("user_id", type=int)
    if user_id_filter:
        query = query.filter_by(user_id=user_id_filter)

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "success": True,
        "data": [log.to_dict() for log in pagination.items],
        "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
    }), 200
