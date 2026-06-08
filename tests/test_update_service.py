"""
tests/test_update_service.py
Unit tests for the keyless 'check for updates' service. The GitHub API is
mocked, so these tests are fully offline.
"""

import json
import urllib.request
import pytest
from services import update_service as us


class TestVersionParsing:
    def test_parse_version(self):
        assert us.parse_version("v1.2.3") == (1, 2, 3)
        assert us.parse_version("1.0") == (1, 0)
        assert us.parse_version("1.0.0rc1") == (1, 0)   # stops at the first non-numeric segment
        assert us.parse_version("") == ()

    def test_is_newer_basic(self):
        assert us.is_newer("1.0.1", "1.0.0") is True
        assert us.is_newer("1.0.0", "1.0.0") is False
        assert us.is_newer("0.9.0", "1.0.0") is False

    def test_is_newer_numeric_not_lexical(self):
        # 10 > 2 numerically, even though "10" < "2" lexically
        assert us.is_newer("1.10.0", "1.2.0") is True

    def test_is_newer_uneven_lengths(self):
        assert us.is_newer("1.0.1", "1.0") is True
        assert us.is_newer("1.0", "1.0.0") is False


class _FakeResp:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()
    def read(self):
        return self._payload
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class TestCheckForUpdate:
    def test_update_available(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda *a, **k: _FakeResp({"tag_name": "v2.0.0",
                                                       "html_url": "https://example/r/2"}))
        info = us.check_for_update("1.0.0")
        assert info.available is True
        assert info.latest == "2.0.0"
        assert info.url == "https://example/r/2"

    def test_up_to_date(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda *a, **k: _FakeResp({"tag_name": "v1.0.0"}))
        info = us.check_for_update("1.0.0")
        assert info.available is False
        assert info.latest == "1.0.0"

    def test_network_error_is_safe(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("no network")
        monkeypatch.setattr(urllib.request, "urlopen", boom)
        info = us.check_for_update("1.0.0")
        assert info.available is False
        assert info.error != ""

    def test_no_releases_yet(self, monkeypatch):
        # GitHub returns 404 for repos with no releases; our code treats the
        # resulting failure as 'no update'. Simulate an empty/garbage payload.
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda *a, **k: _FakeResp({}))
        info = us.check_for_update("1.0.0")
        assert info.available is False
