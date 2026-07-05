"""
tests/conftest.py
Shared pytest fixtures + import-path setup for the Budget Manager test suite.
"""

import os
import sys
import tempfile
import pytest

# Make the project root importable regardless of how pytest is invoked.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def _fast_bcrypt(monkeypatch):
    """Drop bcrypt to its minimum cost (4 rounds) for every test.

    Production code always calls ``bcrypt.gensalt()`` with the default 12
    rounds (~250 ms per hash); tests hash dozens of passwords and recovery
    codes, so at full cost the auth suite alone takes ~30 s. Verification is
    cost-agnostic (the salt embeds the rounds), so this changes nothing about
    what the tests prove.
    """
    import bcrypt
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(bcrypt, "gensalt", lambda rounds=4, prefix=b"2b": real_gensalt(4))


@pytest.fixture
def db():
    """A fresh, isolated DatabaseManager backed by a temp file per test."""
    from database.schema import DatabaseManager
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    mgr = DatabaseManager(path)
    yield mgr
    # Close the connection so Windows can release the file, then clean up.
    try:
        mgr._conn().close()
    except Exception:
        pass
    for ext in ("", "-wal", "-shm"):
        try:
            os.unlink(path + ext)
        except OSError:
            pass


@pytest.fixture
def user_id(db):
    """Create a test user and return their id."""
    from services.auth_service import AuthService
    AuthService(db).register("Test User", "test@example.com", "password123", "CAD")
    return db.get_user_by_email("test@example.com")["id"]


@pytest.fixture
def account_id(db, user_id):
    """A Checking account with a 1000 starting balance."""
    return db.create_account(user_id, "Test Checking", "Checking", 1000.0)


@pytest.fixture
def savings_id(db, user_id):
    """A Savings account with a 1000 starting balance."""
    return db.create_account(user_id, "Test Savings", "Savings", 1000.0)
