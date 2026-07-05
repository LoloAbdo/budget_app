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


class _FakeDownloadResp:
    """Serves *data* in chunks and reports Content-Length, mimicking urlopen."""
    def __init__(self, data: bytes):
        self._buf = data
        self._pos = 0
        self.headers = {"Content-Length": str(len(data))}
    def read(self, size=-1):
        if size is None or size < 0:
            chunk, self._pos = self._buf[self._pos:], len(self._buf)
        else:
            chunk = self._buf[self._pos:self._pos + size]
            self._pos += len(chunk)
        return chunk
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

    def test_installer_asset_is_captured(self, monkeypatch):
        payload = {
            "tag_name": "v2.0.0",
            "html_url": "https://example/r/2",
            "assets": [
                {"name": "BudgetManager.exe", "browser_download_url": "https://x/p.exe", "size": 10},
                {"name": "BudgetManagerSetup.exe", "browser_download_url": "https://x/s.exe", "size": 4096},
            ],
        }
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _FakeResp(payload))
        info = us.check_for_update("1.0.0")
        assert info.installer_url == "https://x/s.exe"
        assert info.installer_size == 4096


class TestSelectInstallerAsset:
    def test_prefers_exact_name(self):
        assets = [
            {"name": "BudgetManager.exe", "browser_download_url": "a"},
            {"name": "BudgetManagerSetup.exe", "browser_download_url": "b"},
        ]
        assert us.select_installer_asset(assets)["browser_download_url"] == "b"

    def test_falls_back_to_setup_suffix(self):
        assets = [{"name": "MyAppSetup.exe", "browser_download_url": "c"}]
        assert us.select_installer_asset(assets)["browser_download_url"] == "c"

    def test_none_when_no_installer(self):
        assert us.select_installer_asset([{"name": "portable.exe"}]) is None
        assert us.select_installer_asset([]) is None


class TestDownloadFile:
    def test_writes_bytes_and_reports_progress(self, monkeypatch, tmp_path):
        data = b"x" * 1000
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda *a, **k: _FakeDownloadResp(data))
        dest = tmp_path / "out.bin"
        seen = []
        us.download_file("https://x/f", str(dest),
                         progress_cb=lambda d, t: seen.append((d, t)), chunk_size=256)
        assert dest.read_bytes() == data
        assert seen[-1] == (1000, 1000)          # final callback = full size
        assert all(t == 1000 for _, t in seen)   # total reported throughout

    def test_partial_file_removed_on_error(self, monkeypatch, tmp_path):
        def boom(*a, **k):
            raise OSError("connection reset")
        monkeypatch.setattr(urllib.request, "urlopen", boom)
        dest = tmp_path / "out.bin"
        with pytest.raises(OSError):
            us.download_file("https://x/f", str(dest))
        assert not dest.exists()


class TestBuildDetection:
    def test_source_run_cannot_auto_update(self, monkeypatch):
        monkeypatch.setattr(us.sys, "frozen", False, raising=False)
        assert us.is_frozen() is False
        assert us.can_auto_update() is False

    def test_one_file_build_detected(self, monkeypatch, tmp_path):
        # _MEIPASS under the temp dir → portable one-file build.
        meipass = tmp_path / "_MEI12345"
        meipass.mkdir()
        monkeypatch.setattr(us.sys, "frozen", True, raising=False)
        monkeypatch.setattr(us.sys, "_MEIPASS", str(meipass), raising=False)
        monkeypatch.setattr(us.tempfile, "gettempdir", lambda: str(tmp_path))
        assert us.is_one_file_build() is True
        assert us.can_auto_update() is False   # portable is not auto-updated

    def test_installed_build_can_auto_update(self, monkeypatch, tmp_path):
        # _MEIPASS inside an install folder (not temp) → one-folder install.
        install = tmp_path / "Program Files" / "Budget Manager"
        install.mkdir(parents=True)
        monkeypatch.setattr(us.sys, "frozen", True, raising=False)
        monkeypatch.setattr(us.sys, "_MEIPASS", str(install), raising=False)
        monkeypatch.setattr(us.tempfile, "gettempdir", lambda: str(tmp_path / "temp"))
        assert us.is_one_file_build() is False
        assert us.can_auto_update() is True


class TestInstallerCommand:
    def test_silent_flags(self):
        cmd = us.installer_launch_command(r"C:\tmp\Setup.exe")
        assert cmd[0] == r"C:\tmp\Setup.exe"
        assert cmd[1:] == ["/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART"]


class _FakeTextResp:
    def __init__(self, text: str):
        self._data = text.encode()
    def read(self):
        return self._data
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class TestChecksums:
    DATA = b"installer bytes"
    # sha256 of DATA
    import hashlib as _h
    DIGEST = _h.sha256(DATA).hexdigest()

    def _installer(self, tmp_path):
        p = tmp_path / "BudgetManagerSetup.exe"
        p.write_bytes(self.DATA)
        return str(p)

    def test_parse_sha256sums(self):
        text = (
            f"{self.DIGEST} *BudgetManagerSetup.exe\n"
            f"{'a' * 64}  BudgetManager.exe\n"
            "garbage line\n"
            "deadbeef *tooshort.exe\n"
        )
        sums = us.parse_sha256sums(text)
        assert sums["budgetmanagersetup.exe"] == self.DIGEST
        assert sums["budgetmanager.exe"] == "a" * 64
        assert "tooshort.exe" not in sums     # digest not 64 hex chars

    def test_sha256_of_file(self, tmp_path):
        assert us.sha256_of_file(self._installer(tmp_path)) == self.DIGEST

    def test_verify_ok(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: _FakeTextResp(f"{self.DIGEST} *BudgetManagerSetup.exe\n"),
        )
        # Both size and hash match → no exception.
        us.verify_installer(
            self._installer(tmp_path),
            expected_size=len(self.DATA),
            checksums_url="https://x/SHA256SUMS.txt",
        )

    def test_verify_rejects_wrong_hash(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: _FakeTextResp(f"{'0' * 64} *BudgetManagerSetup.exe\n"),
        )
        with pytest.raises(ValueError, match="checksum mismatch"):
            us.verify_installer(self._installer(tmp_path),
                                checksums_url="https://x/SHA256SUMS.txt")

    def test_verify_rejects_wrong_size(self, tmp_path):
        with pytest.raises(ValueError, match="size"):
            us.verify_installer(self._installer(tmp_path), expected_size=999_999)

    def test_verify_rejects_missing_entry(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: _FakeTextResp(f"{self.DIGEST} *SomethingElse.exe\n"),
        )
        with pytest.raises(ValueError, match="No checksum published"):
            us.verify_installer(self._installer(tmp_path),
                                checksums_url="https://x/SHA256SUMS.txt")

    def test_verify_fails_closed_when_sums_unfetchable(self, monkeypatch, tmp_path):
        def boom(*a, **k):
            raise OSError("offline")
        monkeypatch.setattr(urllib.request, "urlopen", boom)
        with pytest.raises(ValueError, match="Could not fetch"):
            us.verify_installer(self._installer(tmp_path),
                                checksums_url="https://x/SHA256SUMS.txt")

    def test_verify_skips_hash_for_old_releases(self, tmp_path):
        # No checksums_url (pre-2.4.0 release) → only the size check runs.
        us.verify_installer(self._installer(tmp_path),
                            expected_size=len(self.DATA), checksums_url=None)

    def test_check_for_update_captures_checksums_asset(self, monkeypatch):
        payload = {
            "tag_name": "v9.9.9",
            "assets": [
                {"name": "BudgetManagerSetup.exe", "browser_download_url": "https://x/s.exe", "size": 1},
                {"name": "SHA256SUMS.txt", "browser_download_url": "https://x/sums.txt", "size": 200},
            ],
        }
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _FakeResp(payload))
        info = us.check_for_update("1.0.0")
        assert info.checksums_url == "https://x/sums.txt"
