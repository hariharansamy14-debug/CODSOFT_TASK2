"""
models/deduplication_history.py
================================
Immutable audit trail of actions taken on duplicates. Rows here are NEVER
updated or deleted (except via cascade if the parent duplicate_log is
removed) -- we only ever INSERT, so this table is a true history log.
"""

from datetime import datetime
from app.extensions import db


class DeduplicationHistory(db.Model):
    __tablename__ = "deduplication_history"

    id = db.Column(db.Integer, primary_key=True)
    duplicate_log_id = db.Column(
        db.Integer, db.ForeignKey("duplicate_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_taken = db.Column(
        db.Enum(
            "merge", "replace", "ignore", "delete", "keep_latest", "keep_oldest", "auto",
            name="dedup_action",
        ),
        nullable=False,
    )
    # NULL performed_by means the system took the action automatically
    # (Auto Deduplication feature), not a human.
    performed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "duplicate_log_id": self.duplicate_log_id,
            "action_taken": self.action_taken,
            "performed_by": self.performed_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
