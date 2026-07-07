"""
models/user.py
==============
Represents one row in the `users` table. This class does double duty:
1. It IS the database table definition (SQLAlchemy reads this class and
   creates/matches the `users` table from it).
2. It carries password hashing logic, so "how do I safely check a password?"
   lives right next to the data it protects, instead of scattered in routes.
"""

from datetime import datetime
import bcrypt
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "user", name="user_role"), default="user", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # --- Relationships ---
    # `backref` lets us go the other direction too, e.g. `some_upload.user`
    uploads = db.relationship("Upload", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        """
        Hashes a plain-text password with bcrypt before storing it.
        WHY bcrypt: unlike a plain hash (e.g. SHA-256), bcrypt is deliberately
        SLOW and includes a random "salt" automatically. Slowness is a
        FEATURE here -- it makes brute-force password guessing impractical.
        """
        salt = bcrypt.gensalt()  # random salt -> same password never produces the same hash twice
        self.password_hash = bcrypt.hashpw(raw_password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        """Verifies a login attempt's password against the stored hash."""
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        """
        Converts the model into a plain dict for JSON responses.
        NOTE: password_hash is deliberately excluded -- it must never be
        sent to the client, even hashed.
        """
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
