"""
routes/dashboard_routes.py
============================
Aggregation queries for the frontend's dashboard widgets and charts.
Every number here is computed with SQL aggregate functions (SUM, COUNT)
rather than pulling all rows into Python and summing in a loop -- letting
MySQL do aggregation is dramatically faster as data grows.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from app.extensions import db
from app.models import Upload, File, DuplicateLog

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    """
    GET /api/dashboard/summary
    Returns the headline numbers: Total Uploaded Files, Total Records,
    Duplicate Records, Unique Records, Storage Saved.
    """
    user_id = int(get_jwt_identity())

    totals = (
        db.session.query(
            func.coalesce(func.sum(Upload.total_files), 0),
            func.coalesce(func.sum(Upload.total_records), 0),
            func.coalesce(func.sum(Upload.duplicate_records), 0),
            func.coalesce(func.sum(Upload.unique_records), 0),
        )
        .filter(Upload.user_id == user_id)
        .first()
    )
    total_files, total_records, duplicate_records, unique_records = totals

    storage_saved = sum(u.storage_saved_bytes() for u in Upload.query.filter_by(user_id=user_id).all())

    return jsonify({
        "success": True,
        "data": {
            "total_uploaded_files": int(total_files),
            "total_records": int(total_records),
            "duplicate_records": int(duplicate_records),
            "unique_records": int(unique_records),
            "storage_saved_bytes": storage_saved,
        },
    }), 200


@dashboard_bp.route("/upload-history", methods=["GET"])
@jwt_required()
def upload_history():
    """GET /api/dashboard/upload-history -- last 10 uploads, for the dashboard's history widget/chart."""
    user_id = int(get_jwt_identity())
    uploads = (
        Upload.query.filter_by(user_id=user_id)
        .order_by(Upload.created_at.desc())
        .limit(10)
        .all()
    )
    return jsonify({"success": True, "data": [u.to_dict() for u in uploads]}), 200


@dashboard_bp.route("/duplicate-trend", methods=["GET"])
@jwt_required()
def duplicate_trend():
    """
    GET /api/dashboard/duplicate-trend
    Duplicates found, grouped by detection method -- feeds a pie/bar chart
    showing which algorithm is catching the most duplicates.
    """
    user_id = int(get_jwt_identity())

    results = (
        db.session.query(DuplicateLog.detection_method, func.count(DuplicateLog.id))
        .join(File, File.id == DuplicateLog.file_id)
        .join(Upload, Upload.id == File.upload_id)
        .filter(Upload.user_id == user_id)
        .group_by(DuplicateLog.detection_method)
        .all()
    )

    return jsonify({
        "success": True,
        "data": [{"detection_method": method, "count": count} for method, count in results],
    }), 200


@dashboard_bp.route("/recent-activity", methods=["GET"])
@jwt_required()
def recent_activity():
    """GET /api/dashboard/recent-activity -- last 15 audit log entries for this user."""
    from app.models import AuditLog
    user_id = int(get_jwt_identity())
    logs = (
        AuditLog.query.filter_by(user_id=user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(15)
        .all()
    )
    return jsonify({"success": True, "data": [log.to_dict() for log in logs]}), 200
