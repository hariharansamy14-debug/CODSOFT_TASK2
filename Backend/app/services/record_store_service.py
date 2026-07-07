"""
services/record_store_service.py
==================================
WHY THIS FILE EXISTS:
The duplicate detection engine needs something to compare NEW records
against: "existing records". This service is responsible for gathering
that comparison set for a given user, by re-reading their previously
uploaded (and already-validated) files from storage.

BEGINNER-FRIENDLY DESIGN NOTE:
A larger production system would maintain one canonical "records" table
(the deduplicated master dataset) that gets updated after every resolution
decision, so comparisons are O(existing unique records) instead of
O(all historical file rows). We keep it simple here -- re-reading past
files -- and call that out clearly so you understand the tradeoff you'd
revisit as the system scales (see Docs/algorithm_explanation.md, Bloom
Filter section, for how large-scale systems solve exactly this problem).
"""

from app.models import Upload, File
from app.services import storage_service
from app.utils.file_parser import parse_file


def get_existing_records_for_user(user_id: int, limit_files: int = 25) -> list[dict]:
    """
    Returns a flat list of records from this user's most recent previous
    file uploads, to serve as the "existing data" a new upload is checked
    against. `limit_files` caps how many past files we re-read, so a user
    with thousands of historical uploads doesn't cause a slow request --
    this is a simple, explicit performance guardrail rather than a
    complex caching layer, appropriate for a learning project.
    """
    past_uploads = (
        Upload.query.filter_by(user_id=user_id, status="completed")
        .order_by(Upload.created_at.desc())
        .limit(limit_files)
        .all()
    )

    existing_records = []
    for upload in past_uploads:
        for file in upload.files:
            try:
                content = storage_service.read_file_bytes(file.storage_path, file.storage_type)
                # parse_file expects a path; write bytes to a temp copy so we
                # can reuse the same parser for local AND S3-backed files.
                records = _parse_bytes(content, file.file_type)
                existing_records.extend(records)
            except Exception:
                # A single unreadable historical file shouldn't crash a new
                # upload -- skip it and continue (this gets surfaced in logs).
                continue

    return existing_records


def _parse_bytes(content: bytes, file_type: str) -> list[dict]:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=f".{file_type}", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        return parse_file(tmp.name, file_type)
