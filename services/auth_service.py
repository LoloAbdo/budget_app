"""
services/auth_service.py
Handles password hashing (bcrypt) and user authentication.
"""

import bcrypt
from typing import Optional
from database import DatabaseManager


class AuthService:
    """Provides sign-up, login, and password utilities."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ── Password helpers ──────────────────────────────────────────────────────

    @staticmethod
    def hash_password(plain: str) -> str:
        """Hash a plain-text password with bcrypt; return str."""
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Return True if *plain* matches the stored *hashed* value."""
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    # ── Public API ────────────────────────────────────────────────────────────

    def register(self, name: str, email: str, password: str, currency: str = "CAD") -> tuple[bool, str]:
        """
        Create a new user account.
        Returns (success, message).
        """
        if not name.strip():
            return False, "Name cannot be empty."
        if "@" not in email or "." not in email:
            return False, "Invalid e-mail address."
        if len(password) < 6:
            return False, "Password must be at least 6 characters."
        if self._db.get_user_by_email(email):
            return False, "An account with that e-mail already exists."

        hashed = self.hash_password(password)
        self._db.create_user(name, email, hashed, currency)
        return True, "Account created successfully."

    def login(self, email: str, password: str) -> tuple[bool, Optional[dict], str]:
        """
        Validate credentials.
        Returns (success, user_dict_or_None, message).
        """
        user = self._db.get_user_by_email(email)
        if not user:
            return False, None, "No account found for that e-mail."
        if not self.verify_password(password, user["password"]):
            return False, None, "Incorrect password."
        return True, user, "Login successful."
