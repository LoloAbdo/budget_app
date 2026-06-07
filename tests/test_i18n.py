"""
tests/test_i18n.py
Tests for the lightweight in-app translation layer.
"""

import pytest
from views import i18n


@pytest.fixture(autouse=True)
def reset_language():
    """Each test starts (and leaves) the module in English."""
    i18n.set_language("en")
    yield
    i18n.set_language("en")


class TestTranslation:
    def test_english_returns_key_verbatim(self):
        assert i18n.tr("Settings") == "Settings"
        assert i18n.tr("Dashboard") == "Dashboard"

    def test_french_translation(self):
        i18n.set_language("fr")
        assert i18n.tr("Settings") == "Paramètres"
        assert i18n.tr("Dashboard") == "Tableau de bord"
        assert i18n.tr("Markets") == "Marchés"

    def test_missing_key_falls_back_to_key(self):
        i18n.set_language("fr")
        assert i18n.tr("Some untranslated string XYZ") == "Some untranslated string XYZ"

    def test_unknown_language_falls_back_to_default(self):
        i18n.set_language("zz")
        assert i18n.get_language() == "en"
        assert i18n.tr("Settings") == "Settings"

    def test_get_set_language(self):
        assert i18n.get_language() == "en"
        i18n.set_language("fr")
        assert i18n.get_language() == "fr"

    def test_template_keys_translate(self):
        i18n.set_language("fr")
        template = i18n.tr("{n} transactions")
        assert template.format(n=5) == "5 transactions"

    def test_languages_registry(self):
        assert "en" in i18n.LANGUAGES and "fr" in i18n.LANGUAGES


class TestMonthAbbr:
    def test_twelve_months(self):
        assert len(i18n.month_abbr()) == 12

    def test_differs_by_language(self):
        en = i18n.month_abbr()
        i18n.set_language("fr")
        fr = i18n.month_abbr()
        assert en[0] == "Jan"
        assert fr[0] == "Janv"
        assert en != fr
