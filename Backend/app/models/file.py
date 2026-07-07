"""
models/file.py
==============
One row per physical file (CSV/Excel/JSON/TXT) belonging to an Upload.
`stored_filename` is a UUID-based name (see storage_service.py) so that two
users uploading files both named "data.csv" never collide on disk/S3.
"""

from datetime import datetime
from app.extensions import db


class File(db.Model):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    storage_path = db.Column(db.String(500), nullable=False)
    storage_type = db.Column(db.Enum("local", "s3", name="storage_type"), default="local", nullable=False)
    file_type = db.Column(db.Enum("csv", "xlsx", "json", "txt", name="file_type"), nullable=False)
    file_size_bytes = db.Column(db.BigInteger, default=0, nullable=False)
    record_count = db.Column(db.Integer, default=0, nullable=False)
    checksum_sha256 = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    validation_logs = db.relationship("ValidationLog", backref="file", lazy=True, cascade="all, delete-orphan")
    duplicate_logs = db.relationship("DuplicateLog", backref="file", lazy=True, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "upload_id": self.upload_id,
            "original_filename": self.original_filename,
            "storage_type": self.storage_type,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "record_count": self.record_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
