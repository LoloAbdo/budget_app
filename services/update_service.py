"""
services/update_service.py
Keyless 'check for updates' against the GitHub Releases API.

Pure Python (no Qt) so it can run on a worker thread and be unit-tested in
isolation. Network failures and missing releases never raise — they return an
UpdateInfo with available=False (and an error string when relevant).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from version import __version__, GITHUB_OWNER, GITHUB_REPO, RELEASES_URL

_TIMEOUT = 6
_DL_TIMEOUT = 60
_UA = "BudgetManager/1.0 (+local desktop app)"

# The installer asset published on each GitHub release (see .github/workflows/
# release.yml). This is the file the auto-updater downloads and runs.
INSTALLER_ASSET_NAME = "BudgetManagerSetup.exe"

# Checksums file published alongside the binaries (sha256sum format:
# "<hex digest> *<filename>", one line per asset). The updater refuses to run
# an installer whose hash doesn't match its entry.
CHECKSUMS_ASSET_NAME = "SHA256SUMS.txt"

# Silent-upgrade flags for the Inno Setup installer. /CLOSEAPPLICATIONS lets it
# close this running app to replace its files; the installer's postinstall [Run]
# entry then relaunches the new version. /NORESTART suppresses any reboot prompt.
INSTALLER_SILENT_ARGS = ["/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART"]


@dataclass
class UpdateInfo:
    available: bool = False
    current: str = __version__
    latest: Optional[str] = None
    url: str = RELEASES_URL
    error: str = ""
    installer_url: Optional[str] = None   # direct download link for the installer
    installer_size: int = 0               # bytes, for a download progress bar
    checksums_url: Optional[str] = None   # SHA256SUMS.txt asset, when published


def parse_version(tag: str) -> tuple[int, ...]:
    """Turn a tag like 'v1.10.2' into a comparable tuple (1, 10, 2)."""
    if not tag:
        return ()
    cleaned = tag.strip().lstrip("vV")
    parts = re.split(r"[.\-+]", cleaned)
    out: list[int] = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
        else:
            break   # stop at the first non-numeric segment (e.g. '1.0.0rc1')
    return tuple(out)


def is_newer(latest: str, current: str) -> bool:
    """True if *latest* is a strictly higher version than *current*."""
    lv, cv = parse_version(latest), parse_version(current)
    if not lv:
        return False
    # Pad to equal length for a fair tuple comparison
    n = max(len(lv), len(cv))
    lv += (0,) * (n - len(lv))
    cv += (0,) * (n - len(cv))
    return lv > cv


def check_for_update(
    current_version: str = __version__,
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
) -> UpdateInfo:
    """
    Query GitHub for the latest release and compare it to *current_version*.

    Returns an UpdateInfo. A 404 (no releases yet) or any network error is
    treated as 'no update available', never an exception.
    """
    info = UpdateInfo(current=current_version)
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _UA, "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # network error, 404 (no releases), bad JSON …
        info.error = str(exc)
        return info

    tag = data.get("tag_name") if isinstance(data, dict) else None
    if not tag:
        info.error = "no release tag"
        return info

    info.latest = tag.lstrip("vV")
    info.url = data.get("html_url") or RELEASES_URL
    info.available = is_newer(tag, current_version)

    assets = data.get("assets") or []
    asset = select_installer_asset(assets)
    if asset:
        info.installer_url = asset.get("browser_download_url")
        info.installer_size = int(asset.get("size") or 0)
    sums = select_checksums_asset(assets)
    if sums:
        info.checksums_url = sums.get("browser_download_url")
    return info


def select_installer_asset(assets: list[dict]) -> Optional[dict]:
    """Pick the installer asset from a release's asset list.

    Prefers the exact ``BudgetManagerSetup.exe`` name, falling back to any asset
    ending in ``Setup.exe`` so a future rename doesn't silently break updates.
    """
    lowered = [(a, (a.get("name") or "").lower()) for a in assets]
    for a, name in lowered:
        if name == INSTALLER_ASSET_NAME.lower():
            return a
    for a, name in lowered:
        if name.endswith("setup.exe"):
            return a
    return None


def select_checksums_asset(assets: list[dict]) -> Optional[dict]:
    """Pick the SHA256SUMS.txt asset from a release's asset list, if present."""
    for a in assets:
        if (a.get("name") or "").lower() == CHECKSUMS_ASSET_NAME.lower():
            return a
    return None


# ── Integrity verification ────────────────────────────────────────────────────

def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse sha256sum-style lines ("<hex> *<filename>") into {filename: hex}.

    Filenames are lowercased for case-insensitive lookup; both the binary
    ("*name") and text (" name") markers are accepted. Malformed lines are
    skipped rather than failing the whole file.
    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", line.strip())
        if m:
            out[m.group(2).lower()] = m.group(1).lower()
    return out


def sha256_of_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    """Hex SHA-256 of *path*, streamed so large installers don't load into RAM."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def fetch_text(url: str, timeout: int = _TIMEOUT) -> str:
    """Fetch a small text asset (the checksums file). Raises on any error."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def verify_installer(
    path: str,
    expected_size: int = 0,
    checksums_url: Optional[str] = None,
    asset_name: str = INSTALLER_ASSET_NAME,
) -> None:
    """Verify a downloaded installer before it is executed.

    Checks, in order:
      1. Size matches what the release API reported (when known) — catches
         truncated/corrupted downloads for free.
      2. SHA-256 matches the release's published SHA256SUMS.txt (when the
         release ships one — all releases from v2.4.0 on do). A missing or
         unfetchable checksums file on a release that advertised one, or a
         missing entry for the installer, FAILS the check: better to make the
         user download manually than to silently skip verification.

    Raises ValueError with a user-displayable message on any mismatch.
    Releases published before checksums existed (checksums_url=None) get the
    size check only, so updating from an old version keeps working.
    """
    if expected_size:
        actual = os.path.getsize(path)
        if actual != expected_size:
            raise ValueError(
                f"Downloaded size ({actual} bytes) does not match the release "
                f"asset ({expected_size} bytes)."
            )

    if not checksums_url:
        return

    try:
        sums = parse_sha256sums(fetch_text(checksums_url))
    except Exception as exc:
        raise ValueError(f"Could not fetch the release checksums: {exc}") from exc

    expected = sums.get(asset_name.lower())
    if not expected:
        raise ValueError(f"No checksum published for {asset_name}.")

    actual_hash = sha256_of_file(path)
    if actual_hash != expected:
        raise ValueError(
            "Installer checksum mismatch — the download may be corrupted or "
            "tampered with. Expected "
            f"{expected[:12]}…, got {actual_hash[:12]}…"
        )


# ── Download ──────────────────────────────────────────────────────────────────

def download_file(
    url: str,
    dest: str,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = 64 * 1024,
) -> str:
    """Stream *url* to *dest*, invoking ``progress_cb(bytes_done, total)``.

    ``total`` is 0 when the server doesn't report a Content-Length. Raises on any
    network/IO error so the caller can surface it; the partial file is removed.
    """
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=_DL_TIMEOUT) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb:
                        progress_cb(done, total)
    except Exception:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise
    return dest


# ── Install / relaunch (packaged Windows build only) ──────────────────────────

def is_frozen() -> bool:
    """True when running as a PyInstaller-packaged executable."""
    return bool(getattr(sys, "frozen", False))


def is_one_file_build() -> bool:
    """True for the portable one-file exe (unpacked into a temp dir at launch).

    PyInstaller extracts a one-file build into ``sys._MEIPASS`` under the system
    temp directory; a one-folder (installed) build keeps ``_MEIPASS`` inside the
    install folder. That difference is what tells the two apart.
    """
    if not is_frozen():
        return False
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return False
    try:
        temp = os.path.realpath(tempfile.gettempdir())
        return os.path.commonpath([os.path.realpath(meipass), temp]) == temp
    except Exception:
        return False


def can_auto_update() -> bool:
    """Auto-update is supported only for the installed (one-folder) build.

    Source runs update via git; the portable one-file exe can't safely replace
    itself while running, so it keeps the plain download link.
    """
    return is_frozen() and not is_one_file_build()


def installer_launch_command(installer_path: str) -> list[str]:
    """The command used to run the downloaded installer silently."""
    return [installer_path, *INSTALLER_SILENT_ARGS]


def launch_installer(installer_path: str) -> "subprocess.Popen":
    """Start the silent installer as a detached process and return the handle.

    The caller should quit the app immediately after: the installer closes any
    remaining instance (/CLOSEAPPLICATIONS), upgrades the files in place, and
    relaunches the new version via its postinstall [Run] entry.
    """
    cmd = installer_launch_command(installer_path)
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    return subprocess.Popen(cmd, close_fds=True, creationflags=creationflags)
