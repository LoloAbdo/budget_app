"""
services/update_service.py
Keyless 'check for updates' against the GitHub Releases API.

Pure Python (no Qt) so it can run on a worker thread and be unit-tested in
isolation. Network failures and missing releases never raise — they return an
UpdateInfo with available=False (and an error string when relevant).
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Optional

from version import __version__, GITHUB_OWNER, GITHUB_REPO, RELEASES_URL

_TIMEOUT = 6
_UA = "BudgetManager/1.0 (+local desktop app)"


@dataclass
class UpdateInfo:
    available: bool = False
    current: str = __version__
    latest: Optional[str] = None
    url: str = RELEASES_URL
    error: str = ""


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
    return info
