"""
version.py
Single source of truth for the application version and its GitHub coordinates.

Bump __version__ when cutting a release and tag the repo to match
(e.g. v1.1.0). The in-app update check compares this value against the latest
GitHub release tag.
"""

__version__ = "2.0.0"

GITHUB_OWNER = "LoloAbdo"
GITHUB_REPO = "budget_app"

RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
