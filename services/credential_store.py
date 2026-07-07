"""
services/credential_store.py
Optional "Remember me" credential storage for the login screen.

Credentials live in QSettings (same org/app as the window state), with the
password encrypted at rest via Windows DPAPI (``CryptProtectData``) — tied to
the current Windows user account, so it is never written in plaintext and can't
be read by another user or copied to another machine. If DPAPI is unavailable
(non-Windows, or the call fails), the password is simply not stored — we never
fall back to plaintext. The email is stored as-is (it isn't a secret).
"""

import base64
import ctypes
import sys
from ctypes import wintypes
from typing import Optional

from PyQt6.QtCore import QSettings

# Same location as the window-state settings (main.py sets these app-wide).
_ORG = "BudgetApp"
_APP = "Budget Manager"

_KEY_REMEMBER = "auth/remember"
_KEY_EMAIL    = "auth/email"
_KEY_PASSWORD = "auth/password"   # DPAPI-encrypted, base64-encoded


def _settings() -> QSettings:
    return QSettings(_ORG, _APP)


# ── Windows DPAPI (via ctypes; no pywin32 dependency) ───────────────────────────

class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(func, data: bytes) -> Optional[bytes]:
    """Run CryptProtectData/CryptUnprotectData; None on any failure/non-Windows."""
    if not sys.platform.startswith("win"):
        return None
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    try:
        ok = func(ctypes.byref(blob_in), None, None, None, None, 0,
                  ctypes.byref(blob_out))
    except (OSError, AttributeError):
        return None
    if not ok:
        return None
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _encrypt(text: str) -> Optional[str]:
    raw = _dpapi(ctypes.windll.crypt32.CryptProtectData, text.encode("utf-8")) \
        if sys.platform.startswith("win") else None
    return base64.b64encode(raw).decode("ascii") if raw else None


def _decrypt(token: str) -> Optional[str]:
    if not token:
        return None
    try:
        raw = base64.b64decode(token.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return None
    out = _dpapi(ctypes.windll.crypt32.CryptUnprotectData, raw) \
        if sys.platform.startswith("win") else None
    if out is None:
        return None
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return None


# ── Public API ──────────────────────────────────────────────────────────────────

def remember(email: str, password: str) -> None:
    """Save credentials for next launch. Password is stored only if it can be
    encrypted; otherwise just the email is kept (never plaintext)."""
    s = _settings()
    s.setValue(_KEY_REMEMBER, True)
    s.setValue(_KEY_EMAIL, email)
    enc = _encrypt(password)
    if enc:
        s.setValue(_KEY_PASSWORD, enc)
    else:
        s.remove(_KEY_PASSWORD)


def forget() -> None:
    """Erase any saved credentials."""
    s = _settings()
    for key in (_KEY_REMEMBER, _KEY_EMAIL, _KEY_PASSWORD):
        s.remove(key)


def is_remembered() -> bool:
    return bool(_settings().value(_KEY_REMEMBER, False, type=bool))


def load() -> tuple[str, str]:
    """Return the saved (email, password); either may be '' if not stored."""
    s = _settings()
    if not s.value(_KEY_REMEMBER, False, type=bool):
        return "", ""
    email = s.value(_KEY_EMAIL, "", type=str) or ""
    token = s.value(_KEY_PASSWORD, "", type=str) or ""
    return email, (_decrypt(token) or "")
