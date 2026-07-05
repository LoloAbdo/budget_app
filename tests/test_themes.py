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
    # "auto" is a virtual entry offered first; the real palettes follow.
    assert keys == [theme.AUTO_THEME] + list(theme.THEMES.keys())
    assert "dark" in keys and "light" in keys


class TestAutoTheme:
    def test_resolves_to_dark_when_os_is_dark(self, monkeypatch):
        monkeypatch.setattr(theme, "system_prefers_dark", lambda: True)
        assert theme.resolve_theme("auto") == "dark"
        assert theme.is_dark_theme("auto") is True
        assert theme.theme_qss("auto") == theme.theme_qss("dark")

    def test_resolves_to_light_when_os_is_light(self, monkeypatch):
        monkeypatch.setattr(theme, "system_prefers_dark", lambda: False)
        assert theme.resolve_theme("auto") == "light"
        assert theme.is_dark_theme("auto") is False
        assert theme.theme_qss("auto") == theme.theme_qss("light")

    def test_real_theme_names_pass_through(self):
        for key in theme.THEMES:
            assert theme.resolve_theme(key) == key

    def test_no_qt_app_defaults_to_dark(self):
        # In a bare test process (no QGuiApplication), the OS scheme is
        # unknowable — the fallback must be dark, the app's historic default.
        assert theme.system_prefers_dark() is True

    def test_chart_colors_follow_auto(self, monkeypatch):
        monkeypatch.setattr(theme, "system_prefers_dark", lambda: False)
        theme.set_active_theme("auto")
        assert theme.chart_colors() == _chart_colors_for("light")
        theme.set_active_theme("dark")   # restore for other tests


def test_theme_labels_are_translated_in_french():
    from views import i18n
    for _key, label in theme.available_themes():
        assert label in i18n._FR, f"theme label '{label}' missing from the French table"


def _chart_colors_for(key: str) -> dict:
    theme.set_active_theme(key)
    return theme.chart_colors()
