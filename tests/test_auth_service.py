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
