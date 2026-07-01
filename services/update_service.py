"""
services/update_service.py
Keyless 'check for updates' against the GitHub Releases API.

Pure Python (no Qt) so it can run on a worker thread and be unit-tested in
isolation. Network failures and missing releases never raise — they return an
UpdateInfo with available=False (and an error string when relevant).
"""

from __future__ import annotations

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

    asset = select_installer_asset(data.get("assets") or [])
    if asset:
        info.installer_url = asset.get("browser_download_url")
        info.installer_size = int(asset.get("size") or 0)
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
