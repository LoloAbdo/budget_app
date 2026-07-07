"""
tests/test_changelog.py
The About tab shows the full changelog so users can see what changed after an
update. These guard that the changelog is loadable, follows the app language,
and stays in sync with the current version.
"""

from version import __version__
from views.settings_view import load_changelog


def test_changelog_loads():
    text = load_changelog("en")
    assert text.startswith("# Changelog")
    # A few landmark versions from the start should always be present.
    assert "## [1.0.0]" in text
    assert "## [2.0.0]" in text


def test_changelog_documents_current_version_in_every_language():
    # The shipped version must appear in each changelog, so the About tab never
    # shows a release with no notes whatever the language.
    for lang in ("en", "fr"):
        assert f"## [{__version__}]" in load_changelog(lang), lang


def test_french_changelog_is_localized():
    fr = load_changelog("fr")
    assert fr.startswith("# Journal des modifications")
    assert fr != load_changelog("en")


def test_unknown_language_falls_back_to_english():
    assert load_changelog("de") == load_changelog("en")
