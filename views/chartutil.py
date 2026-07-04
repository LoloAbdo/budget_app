"""
views/chartutil.py
Shared matplotlib styling so charts look native to the app.

Importing this module points matplotlib at the UI font (Segoe UI, with
fallbacks), and `money_axis()` formats an axis's ticks as compact amounts
(1500 -> "1.5k") so charts stop showing raw "3000"-style numbers.
"""

from pathlib import Path

import matplotlib
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

# Register the bundled Inter files so charts use the exact same face as the
# Qt UI, regardless of what's installed on the machine.
_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
for _ttf in sorted(_FONTS_DIR.glob("Inter-*.ttf")):
    try:
        font_manager.fontManager.addfont(str(_ttf))
    except Exception:
        pass  # a bad/missing file just falls through to the next family

# Matplotlib falls through the list until one exists, so this stays safe on
# machines without Inter or Segoe UI (e.g. the Linux CI runner).
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", "Arial", "DejaVu Sans",
]


def compact_money(value: float) -> str:
    """Format an amount for axis ticks: 950 -> '950', 1500 -> '1.5k',
    30000 -> '30k', 2_500_000 -> '2.5M'. Sign is preserved."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{sign}{s}M"
    if v >= 1_000:
        s = f"{v / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{sign}{s}k"
    return f"{sign}{v:g}"


def money_axis(ax, axis: str = "y") -> None:
    """Apply the compact-money formatter to an axis's ticks (y by default)."""
    target = ax.xaxis if axis == "x" else ax.yaxis
    target.set_major_formatter(FuncFormatter(lambda v, _pos: compact_money(v)))
