"""
tests/test_auth_service.py
Tests for AuthService — focused on change_password (the change/reset flow).
"""

import pytest

from services.auth_service import AuthService


@pytest.fixture
def auth(db):
    return AuthService(db)


def test_change_password_success_and_relogin(auth, db, user_id):
    ok, msg = auth.change_password(user_id, "password123", "newsecret")
    assert ok is True
    assert msg == "Password updated successfully."

    # Old password no longer works; new one does.
    user = db.get_user(user_id)
    assert auth.verify_password("newsecret", user["password"]) is True
    assert auth.verify_password("password123", user["password"]) is False

    success, _, _ = auth.login("test@example.com", "newsecret")
    assert success is True


def test_change_password_wrong_current(auth, db, user_id):
    ok, msg = auth.change_password(user_id, "wrongpass", "newsecret")
    assert ok is False
    assert msg == "Current password is incorrect."
    # Password unchanged.
    assert auth.verify_password("password123", db.get_user(user_id)["password"])


def test_change_password_too_short(auth, user_id):
    ok, msg = auth.change_password(user_id, "password123", "abc")
    assert ok is False
    assert msg == "New password must be at least 6 characters."


def test_change_password_same_as_current(auth, user_id):
    ok, msg = auth.change_password(user_id, "password123", "password123")
    assert ok is False
    assert msg == "New password must be different from the current one."


def test_change_password_unknown_user(auth):
    ok, msg = auth.change_password(99999, "whatever", "newsecret")
    assert ok is False
    assert msg == "Account not found."


# ── Recovery codes ────────────────────────────────────────────────────────────

def test_generate_recovery_codes_format_and_count(auth, user_id):
    codes = auth.generate_recovery_codes(user_id)
    assert len(codes) == 8
    assert len(set(codes)) == 8          # all distinct
    for code in codes:
        groups = code.split("-")
        assert len(groups) == 3
        assert all(len(g) == 4 for g in groups)
        # No lookalike characters in the alphabet
        assert not set(code.replace("-", "")) & set("0O1IL")
    assert auth.recovery_codes_remaining(user_id) == 8


def test_codes_are_stored_hashed_not_plaintext(auth, db, user_id):
    codes = auth.generate_recovery_codes(user_id)
    rows = db.get_unused_recovery_codes(user_id)
    stored = {r["code_hash"] for r in rows}
    for code in codes:
        assert code not in stored
        assert code.replace("-", "") not in stored
    assert all(h.startswith("$2") for h in stored)   # bcrypt hashes


def test_reset_password_with_valid_code(auth, db, user_id):
    codes = auth.generate_recovery_codes(user_id)
    ok, msg = auth.reset_password_with_code("test@example.com", codes[0], "brandnewpw")
    assert ok is True
    assert msg == "Password updated successfully."

    # New password works, old doesn't.
    assert auth.login("test@example.com", "brandnewpw")[0] is True
    assert auth.login("test@example.com", "password123")[0] is False

    # The code is burned…
    assert auth.recovery_codes_remaining(user_id) == 7
    ok, msg = auth.reset_password_with_code("test@example.com", codes[0], "anotherpw")
    assert ok is False
    assert msg == "Invalid e-mail or recovery code."
    # …but the others still work.
    ok, _ = auth.reset_password_with_code("test@example.com", codes[1], "anotherpw")
    assert ok is True


def test_reset_code_input_is_forgiving(auth, user_id):
    """Case, dashes, and stray spaces in the typed code must not matter."""
    codes = auth.generate_recovery_codes(user_id)
    mangled = " " + codes[0].lower().replace("-", " ") + " "
    ok, _ = auth.reset_password_with_code("test@example.com", mangled, "brandnewpw")
    assert ok is True


def test_reset_password_wrong_code(auth, user_id):
    auth.generate_recovery_codes(user_id)
    ok, msg = auth.reset_password_with_code("test@example.com", "AAAA-BBBB-CCCC", "newpw123")
    assert ok is False
    assert msg == "Invalid e-mail or recovery code."
    # Password unchanged.
    assert auth.login("test@example.com", "password123")[0] is True


def test_reset_password_unknown_email_same_message(auth, user_id):
    """Unknown e-mail and wrong code must be indistinguishable."""
    auth.generate_recovery_codes(user_id)
    ok, msg = auth.reset_password_with_code("nobody@example.com", "AAAA-BBBB-CCCC", "newpw123")
    assert ok is False
    assert msg == "Invalid e-mail or recovery code."


def test_reset_password_no_codes_generated(auth, user_id):
    ok, msg = auth.reset_password_with_code("test@example.com", "AAAA-BBBB-CCCC", "newpw123")
    assert ok is False
    assert msg == "Invalid e-mail or recovery code."


def test_reset_password_too_short(auth, user_id):
    codes = auth.generate_recovery_codes(user_id)
    ok, msg = auth.reset_password_with_code("test@example.com", codes[0], "abc")
    assert ok is False
    assert msg == "New password must be at least 6 characters."
    # The code must NOT be burned by a rejected attempt.
    assert auth.recovery_codes_remaining(user_id) == 8


def test_regenerate_invalidates_old_codes(auth, user_id):
    old = auth.generate_recovery_codes(user_id)
    new = auth.generate_recovery_codes(user_id)
    assert auth.recovery_codes_remaining(user_id) == 8
    ok, _ = auth.reset_password_with_code("test@example.com", old[0], "newpw123")
    assert ok is False
    ok, _ = auth.reset_password_with_code("test@example.com", new[0], "newpw123")
    assert ok is True


def test_audit_log_never_contains_codes(auth, db, user_id):
    codes = auth.generate_recovery_codes(user_id)
    auth.reset_password_with_code("test@example.com", codes[0], "brandnewpw")
    log_text = str(db.get_audit_log())
    for code in codes:
        assert code not in log_text
        assert code.replace("-", "") not in log_text
    # But the events themselves are recorded.
    assert "recovery_codes" in log_text
    assert "used for password reset" in log_text
