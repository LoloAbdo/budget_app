"""
tests/test_style_polish.py
Style polish: app icon asset, dark-title-bar theme classification,
table hover styling, and the category color-dot helper.
"""

import os
from pathlib import Path

import pytest

from views import theme

ROOT = Path(__file__).resolve().parent.parent


# ── App icon ──────────────────────────────────────────────────────────────────

def test_icon_asset_exists_and_is_plausible():
    ico = ROOT / "assets" / "icon.ico"
    assert ico.exists(), "assets/icon.ico missing — run scripts/make_icon.py"
    assert ico.stat().st_size > 5_000   # a real multi-size .ico, not a stub


# ── Dark title bar classification ─────────────────────────────────────────────

def test_is_dark_theme_classification():
    assert theme.is_dark_theme("dark")
    assert theme.is_dark_theme("midnight")
    assert theme.is_dark_theme("ocean")
    assert theme.is_dark_theme("forest")
    assert theme.is_dark_theme("sunset")
    assert not theme.is_dark_theme("light")
    assert not theme.is_dark_theme("sand")
    assert theme.is_dark_theme("no-such-theme")   # falls back to dark


# ── Table hover state ─────────────────────────────────────────────────────────

def test_every_theme_styles_table_hover():
    for key in theme.THEMES:
        assert "QTableWidget::item:hover" in theme.theme_qss(key)


def test_hover_rule_precedes_selected_rule():
    """Selected must win over hover, so it must come later in the stylesheet."""
    qss = theme.theme_qss("dark")
    assert qss.index("::item:hover") < qss.index("::item:selected")


# ── Category dot icons ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    """QPixmap needs a QGuiApplication; reuse one for the module."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_category_dot_builds_and_caches(qapp):
    from views.widgets import category_dot, _DOT_CACHE
    icon1 = category_dot("#FF5722")
    icon2 = category_dot("#FF5722")
    assert not icon1.isNull()
    assert icon1 is icon2            # cached — same QIcon object
    assert "#FF5722" in _DOT_CACHE
    assert not category_dot("#4CAF50").isNull()
