"""
views/theme.py
Centralised colour tokens and QSS stylesheets for light / dark modes.

Visual language: layered surfaces for depth, a violet→indigo gradient accent,
real hover/pressed states, focus rings, and pill-style tabs.
"""

from typing import Final

# ── Palette tokens ─────────────────────────────────────────────────────────────

DARK: dict[str, str] = {
    "bg":             "#0B0D14",
    "surface":        "#151823",
    "surface2":       "#1E2230",
    "surface3":       "#272C3D",
    "border":         "#2A2F42",
    "accent":         "#7C5CFF",
    "accent_a":       "#8B5CF6",   # gradient start (violet)
    "accent_b":       "#6366F1",   # gradient end   (indigo)
    "accent_hover_a": "#9B72FF",
    "accent_hover_b": "#7C7DF7",
    "accent_soft":    "#221F3D",   # tinted fill for selected pills
    "text":           "#ECEDF5",
    "text_muted":     "#8A8FA3",
    "success":        "#10B981",
    "success_hover":  "#34D399",
    "warning":        "#F59E0B",
    "danger":         "#EF4444",
    "danger_hover":   "#F26563",
    "income":         "#10B981",
    "expense":        "#EF4444",
    # chart-specific
    "chart_bg":       "#151823",
    "chart_fg":       "#ECEDF5",
    "chart_muted":    "#8A8FA3",
    "chart_grid":     "#2A2F42",
}

LIGHT: dict[str, str] = {
    "bg":             "#F4F5FB",
    "surface":        "#FFFFFF",
    "surface2":       "#EEF0F8",
    "surface3":       "#E2E6F3",
    "border":         "#D9DDEC",
    "accent":         "#6D5AE6",
    "accent_a":       "#7C5CFF",
    "accent_b":       "#5B5BF0",
    "accent_hover_a": "#6A4DE0",
    "accent_hover_b": "#4F4FE0",
    "accent_soft":    "#ECEAFD",
    "text":           "#1A1D2E",
    "text_muted":     "#5C5F73",
    "success":        "#059669",
    "success_hover":  "#047857",
    "warning":        "#D97706",
    "danger":         "#DC2626",
    "danger_hover":   "#B91C1C",
    "income":         "#059669",
    "expense":        "#DC2626",
    # chart-specific
    "chart_bg":       "#FFFFFF",
    "chart_fg":       "#1A1D2E",
    "chart_muted":    "#5C5F73",
    "chart_grid":     "#D9DDEC",
}


def _grad(c1: str, c2: str) -> str:
    """Horizontal linear gradient string for QSS backgrounds."""
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c1}, stop:1 {c2})"


def _qss(p: dict[str, str]) -> str:
    """Build a QSS stylesheet from a palette dict *p*."""
    accent_grad       = _grad(p["accent_a"], p["accent_b"])
    accent_grad_hover = _grad(p["accent_hover_a"], p["accent_hover_b"])
    return f"""
/* ── Global ── */
QWidget {{
    background-color: {p['bg']};
    color: {p['text']};
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {p['bg']};
}}

/* ── Cards ── */
QFrame#card {{
    background-color: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 14px;
}}

/* ── Sidebar ── */
QFrame#sidebar {{
    background-color: {p['surface']};
    border-right: 1px solid {p['border']};
}}

QPushButton#navBtn {{
    background-color: transparent;
    color: {p['text_muted']};
    border: none;
    border-radius: 10px;
    padding: 11px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#navBtn:hover {{
    background-color: {p['surface2']};
    color: {p['text']};
}}
QPushButton#navBtn:checked {{
    background: {accent_grad};
    color: #FFFFFF;
    font-weight: 700;
}}

/* ── Primary buttons ── */
QPushButton {{
    background-color: {p['accent']};
    background: {accent_grad};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {accent_grad_hover};
}}
QPushButton:pressed {{
    background-color: {p['accent_b']};
    background: {p['accent_b']};
}}
QPushButton:disabled {{
    background-color: {p['surface3']};
    background: {p['surface3']};
    color: {p['text_muted']};
}}

/* ── Secondary buttons ── */
QPushButton#secondary {{
    background-color: {p['surface2']};
    background: {p['surface2']};
    color: {p['text']};
    border: 1px solid {p['border']};
}}
QPushButton#secondary:hover {{
    background-color: {p['surface3']};
    background: {p['surface3']};
    border-color: {p['accent']};
}}
QPushButton#secondary:pressed {{
    background-color: {p['surface2']};
    background: {p['surface2']};
}}

/* ── Danger buttons ── */
QPushButton#danger {{
    background-color: {p['danger']};
    background: {p['danger']};
    color: #FFFFFF;
}}
QPushButton#danger:hover {{
    background-color: {p['danger_hover']};
    background: {p['danger_hover']};
}}

/* ── Success buttons ── */
QPushButton#success {{
    background-color: {p['success']};
    background: {p['success']};
    color: #FFFFFF;
}}
QPushButton#success:hover {{
    background-color: {p['success_hover']};
    background: {p['success_hover']};
}}

/* ── Expense / Income toggle ── */
QPushButton#toggleLeft, QPushButton#toggleRight {{
    background-color: {p['surface2']};
    background: {p['surface2']};
    color: {p['text']};
    border: 1px solid {p['border']};
    padding: 6px 18px;
    min-width: 80px;
    font-weight: 600;
}}
QPushButton#toggleLeft {{
    border-right: none;
    border-top-left-radius: 9px;
    border-bottom-left-radius: 9px;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QPushButton#toggleRight {{
    border-left: none;
    border-top-right-radius: 9px;
    border-bottom-right-radius: 9px;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
}}
QPushButton#toggleLeft:checked {{
    background-color: {p['danger']};
    background: {p['danger']};
    color: #FFFFFF;
    border-color: {p['danger']};
}}
QPushButton#toggleRight:checked {{
    background-color: {p['success']};
    background: {p['success']};
    color: #FFFFFF;
    border-color: {p['success']};
}}

/* ── Inputs ── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {{
    background-color: {p['surface2']};
    color: {p['text']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 9px 12px;
    selection-background-color: {p['accent']};
    selection-color: #FFFFFF;
}}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QDateEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {p['surface3']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {p['accent']};
    background-color: {p['surface3']};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 8px;
    selection-background-color: {p['accent']};
    selection-color: #FFFFFF;
    color: {p['text']};
    padding: 4px;
    outline: none;
}}

/* ── Checkboxes ── */
QCheckBox {{
    spacing: 8px;
    color: {p['text']};
    background: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {p['border']};
    background-color: {p['surface2']};
}}
QCheckBox::indicator:hover {{
    border-color: {p['accent']};
}}
QCheckBox::indicator:checked {{
    background: {accent_grad};
    border-color: {p['accent_b']};
}}

/* ── Tables ── */
QTableWidget {{
    background-color: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 12px;
    gridline-color: transparent;
    alternate-background-color: {p['surface2']};
    outline: none;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {p['accent_soft']};
    color: {p['text']};
}}
QHeaderView::section {{
    background-color: {p['surface']};
    color: {p['text_muted']};
    border: none;
    border-bottom: 2px solid {p['border']};
    padding: 10px 12px;
    font-weight: 700;
    font-size: 11px;
}}
QTableCornerButton::section {{
    background-color: {p['surface']};
    border: none;
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    width: 10px;
    background: transparent;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {p['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{
    height: 10px;
    background: transparent;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {p['border']};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {p['accent']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ── Labels ── */
QLabel {{ background: transparent; }}
QLabel#heading {{
    font-size: 24px;
    font-weight: 800;
    color: {p['text']};
}}
QLabel#subheading {{
    font-size: 16px;
    font-weight: 700;
    color: {p['text']};
}}
QLabel#muted {{
    color: {p['text_muted']};
    font-size: 12px;
}}
QLabel#amount_income {{
    color: {p['income']};
    font-weight: 700;
    font-size: 15px;
}}
QLabel#amount_expense {{
    color: {p['expense']};
    font-weight: 700;
    font-size: 15px;
}}

/* ── Tabs (pill style) ── */
QTabWidget::pane {{
    border: 1px solid {p['border']};
    border-radius: 12px;
    background-color: {p['surface']};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {p['text_muted']};
    padding: 9px 18px;
    margin-right: 4px;
    border-radius: 8px;
    font-weight: 600;
}}
QTabBar::tab:hover {{
    background-color: {p['surface2']};
    color: {p['text']};
}}
QTabBar::tab:selected {{
    background-color: {p['accent_soft']};
    color: {p['accent']};
}}

/* ── Progress bar ── */
QProgressBar {{
    background-color: {p['surface2']};
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {accent_grad};
    border-radius: 6px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {p['border']};
}}

/* ── Message box ── */
QMessageBox {{
    background-color: {p['surface']};
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {p['surface3']};
    color: {p['text']};
    border: 1px solid {p['border']};
    padding: 6px 10px;
    border-radius: 8px;
}}
"""


DARK_QSS: Final[str]  = _qss(DARK)
LIGHT_QSS: Final[str] = _qss(LIGHT)


# ── Chart theming ───────────────────────────────────────────────────────────────
# Matplotlib charts can't read QSS, so views ask theme.chart_colors() for the
# palette that matches the active mode.

_PALETTES: dict[str, dict[str, str]] = {"dark": DARK, "light": LIGHT}
_active_theme = "dark"


def set_active_theme(name: str) -> None:
    """Record the active theme so charts render with matching colours."""
    global _active_theme
    _active_theme = name if name in _PALETTES else "dark"


def chart_colors() -> dict[str, str]:
    """Return chart colours (bg/fg/muted/grid/income/expense/accent) for the active theme."""
    p = _PALETTES[_active_theme]
    return {
        "bg":      p["chart_bg"],
        "fg":      p["chart_fg"],
        "muted":   p["chart_muted"],
        "grid":    p["chart_grid"],
        "income":  p["income"],
        "expense": p["expense"],
        "accent":  p["accent"],
    }
