"""
models/__init__.py
===================
Re-exports every model from one place so the rest of the app can do:
    from app.models import User, Upload, File, ...
instead of importing from 8 different sub-files. It also ensures every
model class is registered with SQLAlchemy's metadata BEFORE `db.create_all()`
or Flask-Migrate tries to build/compare the schema -- if a model is never
imported, SQLAlchemy doesn't know it exists.
"""

from app.models.user import User
from app.models.upload import Upload
from app.models.file import File
from app.models.validation_log import ValidationLog
from app.models.duplicate_log import DuplicateLog
from app.models.deduplication_history import DeduplicationHistory
from app.models.report import Report
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "Upload",
    "File",
    "ValidationLog",
    "DuplicateLog",
    "DeduplicationHistory",
    "Report",
    "AuditLog",
]
