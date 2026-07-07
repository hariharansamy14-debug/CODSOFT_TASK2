"""
models/upload.py
================
An "upload" is one session where a user drops one or more files. This model
tracks running totals (total_records, duplicate_records, unique_records) so
the dashboard can display statistics WITHOUT recomputing them from scratch
on every page load -- the numbers are updated once, when processing finishes.
"""

from datetime import datetime
from app.extensions import db


class Upload(db.Model):
    __tablename__ = "uploads"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    upload_name = db.Column(db.String(255), nullable=False)
    total_files = db.Column(db.Integer, default=0, nullable=False)
    total_records = db.Column(db.Integer, default=0, nullable=False)
    duplicate_records = db.Column(db.Integer, default=0, nullable=False)
    unique_records = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(
        db.Enum("processing", "completed", "failed", name="upload_status"),
        default="processing",
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # One upload -> many files. `cascade="all, delete-orphan"` means: if an
    # Upload row is deleted, all its File rows are automatically deleted too
    # (mirrors the ON DELETE CASCADE in schema.sql).
    files = db.relationship("File", backref="upload", lazy=True, cascade="all, delete-orphan")
    reports = db.relationship("Report", backref="upload", lazy=True, cascade="all, delete-orphan")

    def storage_saved_bytes(self) -> int:
        """
        Estimates bytes saved by NOT storing duplicate records, by taking the
        average record size in this upload and multiplying by duplicates
        avoided. Used for the "Storage Saved" dashboard widget.
        """
        if self.total_records == 0:
            return 0
        total_bytes = sum(f.file_size_bytes for f in self.files)
        avg_record_size = total_bytes / self.total_records if self.total_records else 0
        return int(avg_record_size * self.duplicate_records)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "upload_name": self.upload_name,
            "total_files": self.total_files,
            "total_records": self.total_records,
            "duplicate_records": self.duplicate_records,
            "unique_records": self.unique_records,
            "storage_saved_bytes": self.storage_saved_bytes(),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
