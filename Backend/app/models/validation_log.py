"""
models/validation_log.py
========================
One row per validation ISSUE (not per record). A perfectly clean row in the
uploaded file produces zero rows here -- this keeps the table small and
every row here is directly actionable ("row 42's email is invalid").
"""

from datetime import datetime
from app.extensions import db


class ValidationLog(db.Model):
    __tablename__ = "validation_logs"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = db.Column(db.Integer, nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    issue_type = db.Column(
        db.Enum(
            "missing_value", "invalid_email", "invalid_phone", "invalid_date",
            "null_value", "extra_spaces", "special_characters", "invalid_type",
            name="validation_issue_type",
        ),
        nullable=False,
    )
    raw_value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_id": self.file_id,
            "row_number": self.row_number,
            "field_name": self.field_name,
            "issue_type": self.issue_type,
            "raw_value": self.raw_value,
        }
