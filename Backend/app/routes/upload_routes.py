"""
routes/upload_routes.py
========================
This blueprint is where the whole pipeline comes together for a single
file upload:

    1. Accept the file(s) via multipart/form-data (multi-file + drag/drop
       are both just "multiple files in one POST" from the backend's view --
       the frontend's drag-and-drop UI is what makes it feel special).
    2. Save via storage_service (local disk today, S3-ready later).
    3. Parse into records via file_parser.
    4. Validate every record via validation_service -> ValidationLog rows.
    5. Gather this user's existing records via record_store_service.
    6. Run the Duplicate Detection Engine -> DuplicateLog rows.
    7. Update the parent Upload's running totals for the dashboard.
"""

import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Upload, File, ValidationLog, DuplicateLog
from app.services import storage_service, validation_service, record_store_service, audit_service
from app.services.dedup_engine import detect_duplicates
from app.utils.file_parser import parse_file

upload_bp = Blueprint("uploads", __name__)


def _allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@upload_bp.route("", methods=["POST"])
@jwt_required()
def upload_files():
    """
    POST /api/uploads
    multipart/form-data:
        - files: one or more files (CSV/Excel/JSON/TXT)
        - upload_name: optional friendly label

    Returns the created Upload record (with totals) plus per-file detail.
    """
    user_id = int(get_jwt_identity())
    incoming_files = request.files.getlist("files")

    if not incoming_files:
        return jsonify({"success": False, "error": "No files provided"}), 400

    # --- Secure File Upload (Security requirement #15) ---
    # Reject anything that isn't an allowed extension BEFORE touching disk.
    for f in incoming_files:
        filename = secure_filename(f.filename)
        if not filename or not _allowed_file(filename):
            return jsonify({
                "success": False,
                "error": f"'{f.filename}' has an unsupported file type. "
                         f"Allowed: {sorted(current_app.config['ALLOWED_EXTENSIONS'])}",
            }), 400

    upload_name = request.form.get("upload_name") or f"Upload by user {user_id}"
    upload = Upload(user_id=user_id, upload_name=upload_name, status="processing")
    db.session.add(upload)
    db.session.flush()  # assigns upload.id without committing yet, so File rows can reference it

    # Gather this user's prior records ONCE, up front, and reuse it for
    # every file in this batch (avoids re-reading old files N times).
    existing_records = record_store_service.get_existing_records_for_user(user_id)

    file_results = []
    running_total_records = 0
    running_duplicate_records = 0

    for f in incoming_files:
        filename = secure_filename(f.filename)
        ext = filename.rsplit(".", 1)[-1].lower()
        file_type = "xlsx" if ext in ("xlsx", "xls") else ext

        saved = storage_service.save_file(f, subfolder=f"user_{user_id}")

        file_row = File(
            upload_id=upload.id,
            original_filename=filename,
            stored_filename=saved["stored_filename"],
            storage_path=saved["storage_path"],
            storage_type=saved["storage_type"],
            file_type=file_type,
            file_size_bytes=saved["file_size_bytes"],
        )
        db.session.add(file_row)
        db.session.flush()

        try:
            records = parse_file(saved["storage_path"], file_type) if saved["storage_type"] == "local" \
                else _parse_from_s3(saved, file_type)
        except ValueError as exc:
            file_row.record_count = 0
            file_results.append({"file_id": file_row.id, "filename": filename, "error": str(exc)})
            continue

        file_row.record_count = len(records)

        # --- Step 4: Validation ---
        issues = validation_service.validate_records(records)
        for issue in issues:
            db.session.add(ValidationLog(file_id=file_row.id, **issue))

        # --- Step 6: Duplicate Detection ---
        duplicate_findings = detect_duplicates(records, existing_records)
        for finding in duplicate_findings:
            db.session.add(DuplicateLog(file_id=file_row.id, **finding))

        running_total_records += len(records)
        running_duplicate_records += len(duplicate_findings)

        # This file's clean records become part of "existing" data for the
        # NEXT file in this same batch (so file 2 can catch dupes of file 1).
        existing_records = existing_records + records

        file_results.append({
            "file_id": file_row.id,
            "filename": filename,
            "record_count": len(records),
            "validation_issues": len(issues),
            "duplicates_found": len(duplicate_findings),
        })

    upload.total_files = len(incoming_files)
    upload.total_records = running_total_records
    upload.duplicate_records = running_duplicate_records
    upload.unique_records = running_total_records - running_duplicate_records
    upload.status = "completed"
    db.session.commit()

    audit_service.record(user_id, "UPLOAD_FILE", f"Uploaded {len(incoming_files)} file(s) as '{upload_name}'")

    return jsonify({
        "success": True,
        "data": {
            "upload": upload.to_dict(),
            "files": file_results,
        },
    }), 201


def _parse_from_s3(saved: dict, file_type: str) -> list[dict]:
    """Small helper: S3-backed files must be pulled to a temp file to reuse the same parser."""
    import tempfile
    content = storage_service.read_file_bytes(saved["storage_path"], saved["storage_type"])
    with tempfile.NamedTemporaryFile(suffix=f".{file_type}", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        return parse_file(tmp.name, file_type)


@upload_bp.route("", methods=["GET"])
@jwt_required()
def list_uploads():
    """GET /api/uploads -- paginated upload history for the logged-in user (requirement #16: Pagination)."""
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)  # cap to prevent abuse

    pagination = (
        Upload.query.filter_by(user_id=user_id)
        .order_by(Upload.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "success": True,
        "data": [u.to_dict() for u in pagination.items],
        "pagination": {
            "page": page, "per_page": per_page,
            "total": pagination.total, "pages": pagination.pages,
        },
    }), 200


@upload_bp.route("/<int:upload_id>", methods=["GET"])
@jwt_required()
def get_upload(upload_id):
    """GET /api/uploads/<id> -- detail view of one upload, including its files."""
    user_id = int(get_jwt_identity())
    upload = Upload.query.filter_by(id=upload_id, user_id=user_id).first()
    if not upload:
        return jsonify({"success": False, "error": "Upload not found"}), 404

    return jsonify({
        "success": True,
        "data": {**upload.to_dict(), "files": [f.to_dict() for f in upload.files]},
    }), 200


@upload_bp.route("/<int:upload_id>", methods=["DELETE"])
@jwt_required()
def delete_upload(upload_id):
    """DELETE /api/uploads/<id> -- removes an upload, its files (from storage too), and all related logs."""
    user_id = int(get_jwt_identity())
    upload = Upload.query.filter_by(id=upload_id, user_id=user_id).first()
    if not upload:
        return jsonify({"success": False, "error": "Upload not found"}), 404

    for file_row in upload.files:
        storage_service.delete_file(file_row.storage_path, file_row.storage_type)

    db.session.delete(upload)  # cascades to files/validation_logs/duplicate_logs via relationship config
    db.session.commit()

    audit_service.record(user_id, "DELETE_UPLOAD", f"Deleted upload #{upload_id}")
    return jsonify({"success": True, "message": "Upload deleted"}), 200
