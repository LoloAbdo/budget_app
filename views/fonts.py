"""
views/fonts.py
Bundled UI font (Inter, OFL-licensed — see assets/fonts/LICENSE.txt) and the
user's font-scale preference.

Inter ships with the app so amounts render identically on every machine, and
its tabular-numerals feature (`tnum`) makes digits fixed-width so money
columns align perfectly. `ui_font()` is the one place code-created QFonts
come from: it applies the family, the user's scale (0.9–1.25), and tnum.

If the bundled files are missing or fail to load, everything falls back to
Segoe UI and the app keeps working.
"""

from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase

FALLBACK_FAMILY = "Segoe UI"

# Set by load_fonts(); stays at the fallback until fonts load successfully.
_family = FALLBACK_FAMILY
_scale = 1.0

# The scale options offered in Settings (value, "label").
FONT_SCALES = [(0.9, "90%"), (1.0, "100%"), (1.1, "110%"), (1.25, "125%")]


def load_fonts(assets_dir) -> bool:
    """Register the bundled Inter files with Qt. Returns True on success."""
    global _family
    fonts_dir = Path(assets_dir) / "fonts"
    loaded_any = False
    for ttf in sorted(fonts_dir.glob("Inter-*.ttf")):
        if QFontDatabase.addApplicationFont(str(ttf)) >= 0:
            loaded_any = True
    if loaded_any:
        _family = "Inter"
    return loaded_any


def family() -> str:
    return _family


def set_scale(scale: float) -> None:
    """Set the user's font scale (clamped to the supported range)."""
    global _scale
    _scale = min(max(float(scale or 1.0), 0.9), 1.25)


def get_scale() -> float:
    return _scale


def scaled(px: float) -> int:
    """A pixel/point size adjusted by the user's font scale."""
    return max(1, round(px * _scale))


def ui_font(point_size: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """The app font at a scaled size, with tabular numerals when available."""
    font = QFont(_family, scaled(point_size), weight)
    try:
        # Qt 6.7+: fixed-width digits so amount columns line up.
        font.setFeature(QFont.Tag("tnum"), 1)
    except AttributeError:
        pass  # older Qt — proportional digits, still fine
    return font
