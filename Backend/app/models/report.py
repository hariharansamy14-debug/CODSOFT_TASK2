from datetime import datetime
from app.extensions import db


class Report(db.Model):
    """A generated report artifact (PDF/Excel/CSV) summarizing one upload."""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = db.Column(db.Enum("pdf", "xlsx", "csv", name="report_type"), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "upload_id": self.upload_id,
            "report_type": self.report_type,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
