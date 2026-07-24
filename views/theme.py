"""
views/theme.py
Centralised colour tokens and QSS stylesheets for all UI themes.

Visual language: layered surfaces for depth, a two-stop gradient accent,
real hover/pressed states, focus rings, and pill-style tabs.

Adding a theme = adding a palette dict with the same keys as DARK and
registering it in THEMES below; the QSS is generated from the palette.
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


MIDNIGHT: dict[str, str] = {   # pure-black OLED variant of Dark
    "bg":             "#000000",
    "surface":        "#0C0C11",
    "surface2":       "#16161E",
    "surface3":       "#20202B",
    "border":         "#26262F",
    "accent":         "#7C5CFF",
    "accent_a":       "#8B5CF6",
    "accent_b":       "#6366F1",
    "accent_hover_a": "#9B72FF",
    "accent_hover_b": "#7C7DF7",
    "accent_soft":    "#1B1830",
    "text":           "#F2F2F8",
    "text_muted":     "#84879A",
    "success":        "#10B981",
    "success_hover":  "#34D399",
    "warning":        "#F59E0B",
    "danger":         "#EF4444",
    "danger_hover":   "#F26563",
    "income":         "#10B981",
    "expense":        "#EF4444",
    "chart_bg":       "#0C0C11",
    "chart_fg":       "#F2F2F8",
    "chart_muted":    "#84879A",
    "chart_grid":     "#26262F",
}

OCEAN: dict[str, str] = {      # deep navy with a cyan→azure accent
    "bg":             "#071019",
    "surface":        "#0D1B29",
    "surface2":       "#132639",
    "surface3":       "#1B3349",
    "border":         "#213A52",
    "accent":         "#0EA5E9",
    "accent_a":       "#22D3EE",
    "accent_b":       "#0EA5E9",
    "accent_hover_a": "#4BDFF5",
    "accent_hover_b": "#2FB7F2",
    "accent_soft":    "#0E2A3C",
    "text":           "#E6F1F8",
    "text_muted":     "#7E97A8",
    "success":        "#10B981",
    "success_hover":  "#34D399",
    "warning":        "#F59E0B",
    "danger":         "#EF4444",
    "danger_hover":   "#F26563",
    "income":         "#10B981",
    "expense":        "#EF4444",
    "chart_bg":       "#0D1B29",
    "chart_fg":       "#E6F1F8",
    "chart_muted":    "#7E97A8",
    "chart_grid":     "#213A52",
}

FOREST: dict[str, str] = {     # dark green with a fresh leaf accent
    "bg":             "#0A120D",
    "surface":        "#111D16",
    "surface2":       "#18281F",
    "surface3":       "#213529",
    "border":         "#284031",
    "accent":         "#22C55E",
    "accent_a":       "#4ADE80",
    "accent_b":       "#16A34A",
    "accent_hover_a": "#6BE89A",
    "accent_hover_b": "#1FBF5B",
    "accent_soft":    "#15301F",
    "text":           "#E9F4EC",
    "text_muted":     "#88A190",
    "success":        "#34D399",
    "success_hover":  "#6EE7B7",
    "warning":        "#F59E0B",
    "danger":         "#EF4444",
    "danger_hover":   "#F26563",
    "income":         "#34D399",
    "expense":        "#F87171",
    "chart_bg":       "#111D16",
    "chart_fg":       "#E9F4EC",
    "chart_muted":    "#88A190",
    "chart_grid":     "#284031",
}

SUNSET: dict[str, str] = {     # warm plum dusk with a rose→amber accent
    "bg":             "#160D14",
    "surface":        "#20141E",
    "surface2":       "#2B1C28",
    "surface3":       "#372532",
    "border":         "#3E2B39",
    "accent":         "#F97316",
    "accent_a":       "#FB7185",
    "accent_b":       "#F97316",
    "accent_hover_a": "#FC8D9D",
    "accent_hover_b": "#FB8A3C",
    "accent_soft":    "#33202B",
    "text":           "#F7EDF1",
    "text_muted":     "#A78E9C",
    "success":        "#10B981",
    "success_hover":  "#34D399",
    "warning":        "#FBBF24",
    "danger":         "#EF4444",
    "danger_hover":   "#F26563",
    "income":         "#10B981",
    "expense":        "#EF4444",
    "chart_bg":       "#20141E",
    "chart_fg":       "#F7EDF1",
    "chart_muted":    "#A78E9C",
    "chart_grid":     "#3E2B39",
}

SAND: dict[str, str] = {       # warm paper-like light theme with a bronze accent
    "bg":             "#F7F3EC",
    "surface":        "#FFFFFF",
    "surface2":       "#F0E9DD",
    "surface3":       "#E5DCCB",
    "border":         "#DDD2BE",
    "accent":         "#B45309",
    "accent_a":       "#D97706",
    "accent_b":       "#B45309",
    "accent_hover_a": "#B96505",
    "accent_hover_b": "#92400E",
    "accent_soft":    "#F6E8D2",
    "text":           "#2A2118",
    "text_muted":     "#7A6E5C",
    "success":        "#059669",
    "success_hover":  "#047857",
    "warning":        "#B45309",
    "danger":         "#DC2626",
    "danger_hover":   "#B91C1C",
    "income":         "#059669",
    "expense":        "#DC2626",
    "chart_bg":       "#FFFFFF",
    "chart_fg":       "#2A2118",
    "chart_muted":    "#7A6E5C",
    "chart_grid":     "#DDD2BE",
}


NORD: dict[str, str] = {       # the Nord palette: calm blue-grey + frost accent
    "bg":             "#232831",
    "surface":        "#2E3440",
    "surface2":       "#353C4A",
    "surface3":       "#3B4252",
    "border":         "#434C5E",
    "accent":         "#5E81AC",
    "accent_a":       "#88C0D0",
    "accent_b":       "#5E81AC",
    "accent_hover_a": "#A3D3E0",
    "accent_hover_b": "#7295BD",
    "accent_soft":    "#33404E",
    "text":           "#ECEFF4",
    "text_muted":     "#9AA5B8",
    "success":        "#A3BE8C",
    "success_hover":  "#B8CDA6",
    "warning":        "#EBCB8B",
    "danger":         "#BF616A",
    "danger_hover":   "#D08770",
    "income":         "#A3BE8C",
    "expense":        "#BF616A",
    "chart_bg":       "#2E3440",
    "chart_fg":       "#ECEFF4",
    "chart_muted":    "#9AA5B8",
    "chart_grid":     "#434C5E",
}

DRACULA: dict[str, str] = {    # the Dracula palette: purple & pink on deep slate
    "bg":             "#1E2029",
    "surface":        "#282A36",
    "surface2":       "#313342",
    "surface3":       "#3B3D4F",
    "border":         "#44475A",
    "accent":         "#BD93F9",
    "accent_a":       "#FF79C6",
    "accent_b":       "#BD93F9",
    "accent_hover_a": "#FF95D2",
    "accent_hover_b": "#CDA9FA",
    "accent_soft":    "#332E4A",
    "text":           "#F8F8F2",
    "text_muted":     "#8B93B5",
    "success":        "#50FA7B",
    "success_hover":  "#69FF94",
    "warning":        "#FFB86C",
    "danger":         "#FF5555",
    "danger_hover":   "#FF6E6E",
    "income":         "#50FA7B",
    "expense":        "#FF5555",
    "chart_bg":       "#282A36",
    "chart_fg":       "#F8F8F2",
    "chart_muted":    "#8B93B5",
    "chart_grid":     "#44475A",
}

HIGH_CONTRAST: dict[str, str] = {   # accessibility: max contrast, strong borders
    "bg":             "#000000",
    "surface":        "#0A0A0A",
    "surface2":       "#161616",
    "surface3":       "#222222",
    "border":         "#6E6E6E",
    "accent":         "#0066FF",
    "accent_a":       "#1A73E8",
    "accent_b":       "#0044CC",
    "accent_hover_a": "#4D94FF",
    "accent_hover_b": "#1A66E0",
    "accent_soft":    "#002B66",
    "text":           "#FFFFFF",
    "text_muted":     "#C8C8C8",
    "success":        "#00E676",
    "success_hover":  "#4DFF9E",
    "warning":        "#FFB300",
    "danger":         "#FF5252",
    "danger_hover":   "#FF7B7B",
    "income":         "#00E676",
    "expense":        "#FF5252",
    "chart_bg":       "#0A0A0A",
    "chart_fg":       "#FFFFFF",
    "chart_muted":    "#C8C8C8",
    "chart_grid":     "#6E6E6E",
}

SAKURA: dict[str, str] = {     # soft cherry-blossom light theme with a rose accent
    "bg":             "#FBF3F5",
    "surface":        "#FFFFFF",
    "surface2":       "#F7E8ED",
    "surface3":       "#F0DAE2",
    "border":         "#E9CDD8",
    "accent":         "#D6336C",
    "accent_a":       "#EC4899",
    "accent_b":       "#DB2777",
    "accent_hover_a": "#D12C63",
    "accent_hover_b": "#B02458",
    "accent_soft":    "#FBE1EB",
    "text":           "#38202B",
    "text_muted":     "#8A6B78",
    "success":        "#059669",
    "success_hover":  "#047857",
    "warning":        "#D97706",
    "danger":         "#DC2626",
    "danger_hover":   "#B91C1C",
    "income":         "#059669",
    "expense":        "#DC2626",
    "chart_bg":       "#FFFFFF",
    "chart_fg":       "#38202B",
    "chart_muted":    "#8A6B78",
    "chart_grid":     "#E9CDD8",
}


def _grad(c1: str, c2: str) -> str:
    """Horizontal linear gradient string for QSS backgrounds."""
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c1}, stop:1 {c2})"


# ── Color math (for deriving accent variants from one chosen color) ───────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, c)) for c in rgb))


def _mix(c1: str, c2: str, t: float) -> str:
    """Blend two hex colors: t=0 -> c1, t=1 -> c2."""
    a, b = _hex_to_rgb(c1), _hex_to_rgb(c2)
    return _rgb_to_hex(tuple(round(x + (y - x) * t) for x, y in zip(a, b)))


def _lighten(c: str, t: float) -> str:
    return _mix(c, "#FFFFFF", t)


def _darken(c: str, t: float) -> str:
    return _mix(c, "#000000", t)


def _qss(p: dict[str, str], scale: float = 1.0) -> str:
    """Build a QSS stylesheet from a palette dict *p* at a given font scale."""
    accent_grad       = _grad(p["accent_a"], p["accent_b"])
    accent_grad_hover = _grad(p["accent_hover_a"], p["accent_hover_b"])

    def fs(px: int) -> int:
        """Font size scaled by the user's preference."""
        return max(1, round(px * scale))

    return f"""
/* ── Global ── */
QWidget {{
    background-color: {p['bg']};
    color: {p['text']};
    font-family: "Inter", "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: {fs(13)}px;
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
    font-size: {fs(13)}px;
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

/* Drag-reorderable nav list — styled to match the nav buttons above. */
QListWidget#navList {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget#navList::item {{
    color: {p['text_muted']};
    border-radius: 10px;
    padding: 11px 16px;
    margin-bottom: 4px;
    font-size: {fs(13)}px;
}}
QListWidget#navList::item:hover {{
    background-color: {p['surface2']};
    color: {p['text']};
}}
QListWidget#navList::item:selected {{
    background: {accent_grad};
    color: #FFFFFF;
}}

/* ── Primary buttons ── */
QPushButton {{
    background-color: {p['accent']};
    background: {accent_grad};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 9px 20px;
    font-size: {fs(13)}px;
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
QTableWidget::item:hover {{
    background-color: {p['surface3']};
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
    font-size: {fs(11)}px;
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
    font-size: {fs(24)}px;
    font-weight: 800;
    color: {p['text']};
}}
QLabel#subheading {{
    font-size: {fs(16)}px;
    font-weight: 700;
    color: {p['text']};
}}
QLabel#muted {{
    color: {p['text_muted']};
    font-size: {fs(12)}px;
}}
QLabel#amount_income {{
    color: {p['income']};
    font-weight: 700;
    font-size: {fs(15)}px;
}}
QLabel#amount_expense {{
    color: {p['expense']};
    font-weight: 700;
    font-size: {fs(15)}px;
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


# ── Theme registry ────────────────────────────────────────────────────────────
# key (stored in users.theme) → (English display label, palette).
# Labels are tr()'d by the Settings combo, so keep them in the i18n table.

THEMES: dict[str, tuple[str, dict[str, str]]] = {
    "dark":         ("Dark",          DARK),
    "light":        ("Light",         LIGHT),
    "midnight":     ("Midnight",      MIDNIGHT),
    "ocean":        ("Ocean",         OCEAN),
    "forest":       ("Forest",        FOREST),
    "sunset":       ("Sunset",        SUNSET),
    "sand":         ("Sand",          SAND),
    "nord":         ("Nord",          NORD),
    "dracula":      ("Dracula",       DRACULA),
    "hicontrast":   ("High Contrast", HIGH_CONTRAST),
    "sakura":       ("Sakura",        SAKURA),
}

_PALETTES: dict[str, dict[str, str]] = {k: p for k, (_, p) in THEMES.items()}
_QSS_CACHE: dict[tuple, str] = {}

# Virtual theme key: follows the OS light/dark preference. Stored in
# users.theme like a real theme, but resolved to dark/light at apply time.
AUTO_THEME = "auto"


def system_prefers_dark() -> bool:
    """True when Windows (or the platform) is set to dark mode.

    Uses Qt's styleHints color scheme (Qt ≥ 6.5). An unknown/unavailable
    scheme falls back to dark — the app's historic default.
    """
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QGuiApplication
        app = QGuiApplication.instance()
        if app is not None:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return False
            if scheme == Qt.ColorScheme.Dark:
                return True
    except Exception:
        pass
    return True


def resolve_theme(name: str) -> str:
    """Map the virtual 'auto' theme to a real palette key; pass others through."""
    if name == AUTO_THEME:
        return "dark" if system_prefers_dark() else "light"
    return name

# User personalization applied on top of the chosen theme.
_custom_accent: str | None = None   # hex like "#FF8800", or None = theme default
_font_scale: float = 1.0


def set_accent(color: str | None) -> None:
    """Override every theme's accent with one chosen color (None = default)."""
    global _custom_accent
    _custom_accent = color.upper() if color else None


def get_accent() -> str | None:
    return _custom_accent


def set_font_scale(scale: float) -> None:
    global _font_scale
    _font_scale = min(max(float(scale or 1.0), 0.9), 1.25)


def effective_palette(name: str) -> dict[str, str]:
    """The theme palette with the custom accent (if any) blended in.

    All accent variants derive from the one chosen color: a lighter/darker
    pair for the gradient, brighter hovers, and a soft fill mixed into the
    theme's surface so selections stay subtle on any background.
    """
    name = resolve_theme(name)
    key = name if name in _PALETTES else "dark"
    p = _PALETTES[key]
    if not _custom_accent:
        return p
    c = _custom_accent
    return {
        **p,
        "accent":         c,
        "accent_a":       _lighten(c, 0.15),
        "accent_b":       _darken(c, 0.12),
        "accent_hover_a": _lighten(c, 0.30),
        "accent_hover_b": _lighten(c, 0.05),
        "accent_soft":    _mix(p["surface"], c, 0.22),
    }


def theme_qss(name: str) -> str:
    """Stylesheet for a theme at the current font scale and accent
    (unknown theme names → dark; 'auto' → the OS light/dark preference)."""
    name = resolve_theme(name)
    key = name if name in _PALETTES else "dark"
    cache_key = (key, _font_scale, _custom_accent)
    if cache_key not in _QSS_CACHE:
        _QSS_CACHE[cache_key] = _qss(effective_palette(key), _font_scale)
    return _QSS_CACHE[cache_key]


def available_themes() -> list[tuple[str, str]]:
    """(key, English label) pairs for building theme pickers."""
    return [(AUTO_THEME, "Auto (match Windows)")] + [
        (key, label) for key, (label, _) in THEMES.items()
    ]


def is_dark_theme(name: str) -> bool:
    """True if the theme's background is dark (drives the OS title-bar mode)."""
    bg = _PALETTES.get(resolve_theme(name), DARK)["bg"].lstrip("#")
    r, g, b = (int(bg[i:i + 2], 16) for i in (0, 2, 4))
    # Perceived luminance (ITU-R BT.601); < 128 of 255 reads as dark.
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


# Kept for callers that predate the registry (e.g. the login screen).
DARK_QSS: Final[str]  = theme_qss("dark")
LIGHT_QSS: Final[str] = theme_qss("light")


# ── Chart theming ───────────────────────────────────────────────────────────────
# Matplotlib charts can't read QSS, so views ask theme.chart_colors() for the
# palette that matches the active mode.

_active_theme = "dark"


def set_active_theme(name: str) -> None:
    """Record the active theme so charts render with matching colours."""
    global _active_theme
    name = resolve_theme(name)
    _active_theme = name if name in _PALETTES else "dark"


def chart_colors() -> dict[str, str]:
    """Return chart colours (bg/fg/muted/grid/income/expense/accent) for the active theme."""
    p = effective_palette(_active_theme)
    return {
        "bg":      p["chart_bg"],
        "fg":      p["chart_fg"],
        "muted":   p["chart_muted"],
        "grid":    p["chart_grid"],
        "income":  p["income"],
        "expense": p["expense"],
        "accent":  p["accent"],
    }
