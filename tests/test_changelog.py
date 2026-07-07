"""
tests/test_changelog.py
The About tab shows the full changelog so users can see what changed after an
update. These guard that CHANGELOG.md is loadable and stays in sync with the
current version.
"""

from version import __version__
from views.settings_view import load_changelog


def test_changelog_loads():
    text = load_changelog()
    assert text.startswith("# Changelog")
    # A few landmark versions from the start should always be present.
    assert "## [1.0.0]" in text
    assert "## [2.0.0]" in text


def test_changelog_documents_current_version():
    # The shipped version must appear in the changelog, so the About tab never
    # shows a release with no notes.
    assert f"## [{__version__}]" in load_changelog()
