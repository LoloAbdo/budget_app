"""
tests/test_personalization.py
Font scale, custom accent color, and the bundled Inter font.
"""

import os
from pathlib import Path

import pytest

from views import theme

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _reset_theme_state():
    """Each test starts from defaults and never leaks scale/accent changes."""
    yield
    theme.set_font_scale(1.0)
    theme.set_accent(None)


# ── Migration v1.0.10 ─────────────────────────────────────────────────────────

def test_users_have_font_scale_and_accent(db, user_id):
    user = db.get_user(user_id)
    assert user["font_scale"] == 1.0
    assert user["accent"] is None


def test_update_font_scale_and_accent(db, user_id):
    db.update_user_font_scale(user_id, 1.25)
    db.update_user_accent(user_id, "#FF8800")
    user = db.get_user(user_id)
    assert user["font_scale"] == 1.25
    assert user["accent"] == "#FF8800"
    db.update_user_accent(user_id, None)
    assert db.get_user(user_id)["accent"] is None


# ── Font scale in generated QSS ───────────────────────────────────────────────

def test_qss_scales_font_sizes():
    theme.set_font_scale(1.0)
    assert "font-size: 13px" in theme.theme_qss("dark")
    assert "font-size: 24px" in theme.theme_qss("dark")   # heading
    theme.set_font_scale(1.25)
    scaled = theme.theme_qss("dark")
    assert "font-size: 16px" in scaled                    # round(13 * 1.25)
    assert "font-size: 30px" in scaled                    # round(24 * 1.25)


def test_font_scale_is_clamped():
    theme.set_font_scale(3.0)
    assert "font-size: 16px" in theme.theme_qss("dark")   # clamped to 1.25
    theme.set_font_scale(0.1)
    assert "font-size: 12px" in theme.theme_qss("dark")   # clamped to 0.9


def test_fonts_module_scaling():
    from views import fonts
    fonts.set_scale(1.25)
    assert fonts.scaled(13) == 16
    fonts.set_scale(1.0)
    assert fonts.scaled(13) == 13


# ── Custom accent ─────────────────────────────────────────────────────────────

def test_accent_override_reaches_qss_and_charts():
    theme.set_accent("#FF8800")
    qss = theme.theme_qss("dark")
    assert "#FF8800" in qss
    p = theme.effective_palette("dark")
    assert p["accent"] == "#FF8800"
    assert p["accent_a"] != p["accent_b"]          # gradient still has two stops
    theme.set_active_theme("dark")
    assert theme.chart_colors()["accent"] == "#FF8800"


def test_accent_reset_restores_theme_default():
    theme.set_accent("#FF8800")
    theme.set_accent(None)
    assert theme.effective_palette("dark")["accent"] == theme.DARK["accent"]
    assert "#FF8800" not in theme.theme_qss("dark")


def test_accent_soft_blends_with_each_theme_surface():
    theme.set_accent("#FF8800")
    softs = {key: theme.effective_palette(key)["accent_soft"] for key in theme.THEMES}
    # The soft fill derives from each theme's own surface, so it must differ
    # between a dark and a light theme.
    assert softs["dark"] != softs["light"]


# ── Bundled font ──────────────────────────────────────────────────────────────

def test_inter_files_and_license_are_bundled():
    fonts_dir = ROOT / "assets" / "fonts"
    for name in ("Inter-Regular.ttf", "Inter-Medium.ttf",
                 "Inter-SemiBold.ttf", "Inter-Bold.ttf", "LICENSE.txt"):
        assert (fonts_dir / name).exists(), f"missing {name}"


def test_qss_prefers_inter():
    assert '"Inter", "Segoe UI"' in theme.theme_qss("dark")


def test_chartutil_prefers_inter():
    import matplotlib
    import views.chartutil  # noqa: F401
    assert matplotlib.rcParams["font.sans-serif"][0] == "Inter"


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_load_fonts_registers_inter(qapp):
    from views import fonts
    assert fonts.load_fonts(ROOT / "assets")
    assert fonts.family() == "Inter"
    font = fonts.ui_font(11)
    assert font.family() == "Inter"
