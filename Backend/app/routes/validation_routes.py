"""
routes/validation_routes.py
=============================
Validation itself RUNS during upload (see upload_routes.py). These routes
are for RETRIEVING the results afterward -- viewing the validation report,
filtering issues, etc.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import File, ValidationLog, Upload
from app.services.validation_service import summarize

validation_bp = Blueprint("validation", __name__)


def _authorize_file(file_id: int, user_id: int) -> File | None:
    """Ensures the requesting user actually owns the upload this file belongs to."""
    file_row = File.query.get(file_id)
    if not file_row:
        return None
    upload = Upload.query.get(file_row.upload_id)
    if not upload or upload.user_id != user_id:
        return None
    return file_row


@validation_bp.route("/file/<int:file_id>", methods=["GET"])
@jwt_required()
def get_validation_issues(file_id):
    """GET /api/validation/file/<file_id> -- all validation issues for one file, paginated."""
    user_id = int(get_jwt_identity())
    file_row = _authorize_file(file_id, user_id)
    if not file_row:
        return jsonify({"success": False, "error": "File not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)

    pagination = ValidationLog.query.filter_by(file_id=file_id).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "success": True,
        "data": [v.to_dict() for v in pagination.items],
        "pagination": {"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages},
    }), 200


@validation_bp.route("/file/<int:file_id>/report", methods=["GET"])
@jwt_required()
def get_validation_report(file_id):
    """GET /api/validation/file/<file_id>/report -- issue counts grouped by type."""
    user_id = int(get_jwt_identity())
    file_row = _authorize_file(file_id, user_id)
    if not file_row:
        return jsonify({"success": False, "error": "File not found"}), 404

    all_issues = [v.to_dict() for v in ValidationLog.query.filter_by(file_id=file_id).all()]
    return jsonify({
        "success": True,
        "data": {
            "file_id": file_id,
            "total_records": file_row.record_count,
            "total_issues": len(all_issues),
            "issues_by_type": summarize(all_issues),
        },
    }), 200
