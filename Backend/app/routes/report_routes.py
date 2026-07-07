import os
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Upload, Report
from app.services import report_service, audit_service

report_bp = Blueprint("reports", __name__)

GENERATORS = {
    "csv": report_service.generate_csv_report,
    "xlsx": report_service.generate_excel_report,
    "pdf": report_service.generate_pdf_report,
}


@report_bp.route("/upload/<int:upload_id>/generate", methods=["POST"])
@jwt_required()
def generate_report(upload_id):
    """
    POST /api/reports/upload/<upload_id>/generate
    Body: { "format": "pdf" | "xlsx" | "csv" }
    """
    user_id = int(get_jwt_identity())
    upload = Upload.query.filter_by(id=upload_id, user_id=user_id).first()
    if not upload:
        return jsonify({"success": False, "error": "Upload not found"}), 404

    report_format = (request.get_json(silent=True) or {}).get("format", "pdf")
    if report_format not in GENERATORS:
        return jsonify({"success": False, "error": "format must be one of: pdf, xlsx, csv"}), 400

    reports_dir = os.path.join(current_app.config["LOCAL_STORAGE_PATH"], "reports")
    os.makedirs(reports_dir, exist_ok=True)

    file_path = GENERATORS[report_format](upload_id, reports_dir)

    report = Report(upload_id=upload_id, report_type=report_format, file_path=file_path, generated_by=user_id)
    db.session.add(report)
    db.session.commit()

    audit_service.record(user_id, "GENERATE_REPORT", f"Generated {report_format} report for upload #{upload_id}")
    return jsonify({"success": True, "data": report.to_dict()}), 201


@report_bp.route("/<int:report_id>/download", methods=["GET"])
@jwt_required()
def download_report(report_id):
    """GET /api/reports/<report_id>/download -- streams the generated file back to the client."""
    user_id = int(get_jwt_identity())
    report = Report.query.get(report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found"}), 404

    upload = Upload.query.get(report.upload_id)
    if not upload or upload.user_id != user_id:
        return jsonify({"success": False, "error": "Report not found"}), 404

    if not os.path.exists(report.file_path):
        return jsonify({"success": False, "error": "Report file missing on disk"}), 410

    return send_file(report.file_path, as_attachment=True)


@report_bp.route("/upload/<int:upload_id>", methods=["GET"])
@jwt_required()
def list_reports(upload_id):
    """GET /api/reports/upload/<upload_id> -- all previously generated reports for an upload."""
    user_id = int(get_jwt_identity())
    upload = Upload.query.filter_by(id=upload_id, user_id=user_id).first()
    if not upload:
        return jsonify({"success": False, "error": "Upload not found"}), 404

    return jsonify({"success": True, "data": [r.to_dict() for r in upload.reports]}), 200
