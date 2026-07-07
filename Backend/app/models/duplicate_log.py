"""
models/duplicate_log.py
=======================
One row per duplicate PAIR the detection engine finds: "row N in this new
file looks like it already exists, according to algorithm X, with confidence
score Y". `status` tracks the CURRENT resolution state; the full history of
how it got there lives in DeduplicationHistory.
"""

from datetime import datetime
from app.extensions import db


class DuplicateLog(db.Model):
    __tablename__ = "duplicate_logs"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    new_row_number = db.Column(db.Integer, nullable=False)
    existing_record_ref = db.Column(db.String(255), nullable=True)
    match_field = db.Column(db.String(100), nullable=False)
    detection_method = db.Column(
        db.Enum(
            "exact", "sha256", "md5", "levenshtein", "jaccard", "cosine",
            "soundex", "metaphone", name="detection_method",
        ),
        nullable=False,
    )
    similarity_score = db.Column(db.Numeric(5, 4), default=1.0, nullable=False)
    status = db.Column(
        db.Enum(
            "pending", "merged", "replaced", "ignored", "deleted",
            "kept_latest", "kept_oldest", name="duplicate_status",
        ),
        default="pending",
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    history = db.relationship(
        "DeduplicationHistory", backref="duplicate_log", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_id": self.file_id,
            "new_row_number": self.new_row_number,
            "existing_record_ref": self.existing_record_ref,
            "match_field": self.match_field,
            "detection_method": self.detection_method,
            "similarity_score": float(self.similarity_score),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
