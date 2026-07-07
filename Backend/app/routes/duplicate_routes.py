"""
routes/duplicate_routes.py
============================
Retrieving duplicate findings (from the Detection Engine) and applying
resolution actions (via the Deduplication Engine's service layer).
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import DuplicateLog, File, Upload
from app.services import deduplication_service, audit_service

duplicate_bp = Blueprint("duplicates", __name__)


def _authorize_duplicate(duplicate_id: int, user_id: int) -> DuplicateLog | None:
    duplicate = DuplicateLog.query.get(duplicate_id)
    if not duplicate:
        return None
    file_row = File.query.get(duplicate.file_id)
    upload = Upload.query.get(file_row.upload_id) if file_row else None
    if not upload or upload.user_id != user_id:
        return None
    return duplicate


@duplicate_bp.route("/file/<int:file_id>", methods=["GET"])
@jwt_required()
def list_duplicates(file_id):
    """
    GET /api/duplicates/file/<file_id>?status=pending
    Lists duplicate findings for a file, optionally filtered by status
    (Search & Filter requirement #12: filter by Duplicate Status).
    """
    user_id = int(get_jwt_identity())
    file_row = File.query.get(file_id)
    if not file_row:
        return jsonify({"success": False, "error": "File not found"}), 404
    upload = Upload.query.get(file_row.upload_id)
    if not upload or upload.user_id != user_id:
        return jsonify({"success": False, "error": "File not found"}), 404

    query = DuplicateLog.query.filter_by(file_id=file_id)
    status_filter = request.args.get("status")
    if status_filter:
        query = query.filter_by(status=status_filter)

    duplicates = query.order_by(DuplicateLog.similarity_score.desc()).all()
    return jsonify({"success": True, "data": [d.to_dict() for d in duplicates]}), 200


@duplicate_bp.route("/<int:duplicate_id>/resolve", methods=["POST"])
@jwt_required()
def resolve_duplicate(duplicate_id):
    """
    POST /api/duplicates/<id>/resolve
    Body: { "action": "merge"|"replace"|"ignore"|"delete"|"keep_latest"|"keep_oldest", "notes": str }
    Manual deduplication -- a human reviewing the UI decides what happens
    to one specific duplicate finding.
    """
    user_id = int(get_jwt_identity())
    duplicate = _authorize_duplicate(duplicate_id, user_id)
    if not duplicate:
        return jsonify({"success": False, "error": "Duplicate record not found"}), 404

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    notes = data.get("notes")

    try:
        updated = deduplication_service.resolve_duplicate(duplicate_id, action, user_id, notes)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    audit_service.record(user_id, "RESOLVE_DUPLICATE", f"Duplicate #{duplicate_id} resolved as '{action}'")
    return jsonify({"success": True, "data": updated.to_dict()}), 200


@duplicate_bp.route("/file/<int:file_id>/auto-resolve", methods=["POST"])
@jwt_required()
def auto_resolve(file_id):
    """
    POST /api/duplicates/file/<file_id>/auto-resolve
    Auto Deduplication -- resolves every high-confidence pending duplicate
    for a file without requiring a human click per row.
    """
    user_id = int(get_jwt_identity())
    file_row = File.query.get(file_id)
    if not file_row:
        return jsonify({"success": False, "error": "File not found"}), 404
    upload = Upload.query.get(file_row.upload_id)
    if not upload or upload.user_id != user_id:
        return jsonify({"success": False, "error": "File not found"}), 404

    summary = deduplication_service.auto_resolve_pending_duplicates(file_id)
    audit_service.record(user_id, "AUTO_RESOLVE", f"Auto-resolved duplicates for file #{file_id}: {summary}")
    return jsonify({"success": True, "data": summary}), 200


@duplicate_bp.route("/<int:duplicate_id>/history", methods=["GET"])
@jwt_required()
def get_history(duplicate_id):
    """GET /api/duplicates/<id>/history -- full audit trail of actions on one duplicate."""
    user_id = int(get_jwt_identity())
    duplicate = _authorize_duplicate(duplicate_id, user_id)
    if not duplicate:
        return jsonify({"success": False, "error": "Duplicate record not found"}), 404

    return jsonify({"success": True, "data": [h.to_dict() for h in duplicate.history]}), 200
