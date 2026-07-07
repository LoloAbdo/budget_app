"""
tests/test_credential_store.py
The login screen's "Remember me" storage. QSettings is redirected to a temp
INI file so tests never touch the real registry, and password encryption
(Windows DPAPI) is exercised only where it's available.
"""

import sys
import pytest
from PyQt6.QtCore import QSettings

from services import credential_store as cs


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Redirect credential_store to an isolated INI file."""
    ini = str(tmp_path / "creds.ini")
    monkeypatch.setattr(
        cs, "_settings", lambda: QSettings(ini, QSettings.Format.IniFormat)
    )
    return cs


def test_nothing_saved_by_default(store):
    assert store.load() == ("", "")
    assert store.is_remembered() is False


def test_email_is_remembered_and_forgotten(store):
    store.remember("me@example.com", "hunter2")
    assert store.is_remembered() is True
    email, _pw = store.load()
    assert email == "me@example.com"

    store.forget()
    assert store.is_remembered() is False
    assert store.load() == ("", "")


def test_password_is_never_stored_in_plaintext(store, tmp_path):
    store.remember("me@example.com", "PlAiNtExT123")
    store._settings().sync()  # flush QSettings to disk before reading the file
    # The raw on-disk value must not contain the password.
    raw = (tmp_path / "creds.ini").read_text(encoding="utf-8", errors="ignore")
    assert "PlAiNtExT123" not in raw


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="DPAPI is Windows-only"
)
def test_password_roundtrips_on_windows(store):
    store.remember("me@example.com", "s3cr3t-π-pw")
    email, pw = store.load()
    assert email == "me@example.com"
    assert pw == "s3cr3t-π-pw"


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="checks the no-DPAPI fallback"
)
def test_password_not_stored_without_dpapi(store):
    # Off Windows there is no DPAPI, so the password must not be persisted
    # (email still is) — we never fall back to plaintext.
    store.remember("me@example.com", "whatever")
    email, pw = store.load()
    assert email == "me@example.com"
    assert pw == ""


def test_encrypt_decrypt_roundtrip():
    enc = cs._encrypt("hello world")
    if enc is None:            # no DPAPI on this platform
        pytest.skip("DPAPI unavailable")
    assert cs._decrypt(enc) == "hello world"


def test_decrypt_garbage_returns_none():
    assert cs._decrypt("not-valid-base64!!") is None
    assert cs._decrypt("") is None
