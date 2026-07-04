"""
tests/test_themes.py
Theme registry: every palette is complete, every theme builds a stylesheet,
and unknown theme names fall back to dark instead of crashing.
"""

from views import theme


def test_all_palettes_have_identical_token_sets():
    """A missing token would raise KeyError deep inside QSS generation."""
    reference = set(theme.DARK.keys())
    for key, (_label, palette) in theme.THEMES.items():
        assert set(palette.keys()) == reference, f"palette '{key}' token mismatch"


def test_theme_qss_builds_for_every_registered_theme():
    for key, (_label, palette) in theme.THEMES.items():
        qss = theme.theme_qss(key)
        assert palette["bg"] in qss
        assert palette["accent_a"] in qss


def test_unknown_theme_falls_back_to_dark():
    assert theme.theme_qss("no-such-theme") == theme.theme_qss("dark")
    theme.set_active_theme("no-such-theme")
    assert theme.chart_colors() == _chart_colors_for("dark")
    theme.set_active_theme("dark")   # restore for other tests


def test_chart_colors_complete_for_every_theme():
    expected = {"bg", "fg", "muted", "grid", "income", "expense", "accent"}
    for key in theme.THEMES:
        theme.set_active_theme(key)
        colors = theme.chart_colors()
        assert set(colors.keys()) == expected
        assert all(v.startswith("#") for v in colors.values())
    theme.set_active_theme("dark")


def test_available_themes_matches_registry():
    keys = [k for k, _ in theme.available_themes()]
    assert keys == list(theme.THEMES.keys())
    assert "dark" in keys and "light" in keys


def test_theme_labels_are_translated_in_french():
    from views import i18n
    for _key, label in theme.available_themes():
        assert label in i18n._FR, f"theme label '{label}' missing from the French table"


def _chart_colors_for(key: str) -> dict:
    theme.set_active_theme(key)
    return theme.chart_colors()
