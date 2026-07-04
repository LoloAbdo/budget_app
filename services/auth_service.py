"""
services/auth_service.py
Handles password hashing (bcrypt) and user authentication.
"""

import re
import secrets

import bcrypt
from typing import Optional
from database import DatabaseManager

# Recovery-code format: 3 groups of 4, e.g. "K7PM-4Q2X-9RTF". The alphabet
# drops lookalike characters (0/O, 1/I/L) so codes survive being hand-copied.
RECOVERY_CODE_COUNT = 8
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_GROUPS = 3
_CODE_GROUP_LEN = 4


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

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> tuple[bool, str]:
        """
        Change a user's password after verifying the current one.

        Returns (success, message). The message is an English source string so
        the UI can localize it via tr().
        """
        user = self._db.get_user(user_id)
        if not user:
            return False, "Account not found."
        if not self.verify_password(current_password, user["password"]):
            return False, "Current password is incorrect."
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters."
        if new_password == current_password:
            return False, "New password must be different from the current one."

        self._db.update_user_password(user_id, self.hash_password(new_password))
        return True, "Password updated successfully."

    # ── Recovery codes ────────────────────────────────────────────────────────

    @staticmethod
    def _new_recovery_code() -> str:
        groups = (
            "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_GROUP_LEN))
            for _ in range(_CODE_GROUPS)
        )
        return "-".join(groups)

    @staticmethod
    def _normalize_code(code: str) -> str:
        """Canonical form used for hashing/checking: uppercase, alphanumerics only.

        Users may type codes with or without dashes/spaces, in any case.
        """
        return re.sub(r"[^A-Z0-9]", "", (code or "").upper())

    def generate_recovery_codes(self, user_id: int) -> list[str]:
        """Create a fresh set of one-time recovery codes for *user_id*.

        Replaces any existing codes (used or not). Returns the plaintext codes —
        this is the only time they exist outside the caller's hands; the DB
        stores bcrypt hashes of the normalized form.
        """
        codes = [self._new_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
        hashes = [
            bcrypt.hashpw(self._normalize_code(c).encode(), bcrypt.gensalt()).decode()
            for c in codes
        ]
        self._db.replace_recovery_codes(user_id, hashes)
        return codes

    def recovery_codes_remaining(self, user_id: int) -> int:
        return self._db.count_unused_recovery_codes(user_id)

    def reset_password_with_code(
        self, email: str, code: str, new_password: str
    ) -> tuple[bool, str]:
        """Reset a forgotten password using a one-time recovery code.

        The failure message is deliberately identical for "unknown e-mail",
        "no codes set up", and "wrong code" so the flow can't be used to probe
        which e-mails have accounts.
        """
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters."

        generic = "Invalid e-mail or recovery code."
        user = self._db.get_user_by_email(email.strip())
        if not user:
            return False, generic

        normalized = self._normalize_code(code)
        if not normalized:
            return False, generic

        for row in self._db.get_unused_recovery_codes(user["id"]):
            if bcrypt.checkpw(normalized.encode(), row["code_hash"].encode()):
                self._db.mark_recovery_code_used(row["id"], user_id=user["id"])
                self._db.update_user_password(user["id"], self.hash_password(new_password))
                return True, "Password updated successfully."
        return False, generic
