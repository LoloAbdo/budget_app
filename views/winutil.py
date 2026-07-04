"""
views/winutil.py
Windows-specific chrome tweaks: make the native title bar match the theme.

Qt draws the app; Windows draws the title bar. Without this, dark themes get
a glaring white title bar. DwmSetWindowAttribute(DWMWA_USE_IMMERSIVE_DARK_MODE)
flips it to dark. An app-wide event filter applies the current mode to every
top-level window as it appears (dialogs, message boxes, the main window), so
individual views never need to think about it. All calls are best-effort
no-ops on other platforms or very old Windows builds.
"""

import sys

from PyQt6.QtCore import QEvent, QObject

# Attribute id 20 on current Windows 10/11; 19 on pre-20H1 builds.
_DWM_DARK_ATTRS = (20, 19)

# The mode every new top-level window should get; MainWindow updates this
# whenever the user switches themes.
_dark_mode = True


def apply_title_bar(window, dark: bool) -> None:
    """Set one window's title bar to dark/light. Safe to call repeatedly."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(window.winId())
        value = ctypes.c_int(1 if dark else 0)
        for attr in _DWM_DARK_ATTRS:
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                break
    except Exception:
        pass


def set_dark_mode(dark: bool) -> None:
    """Record the app-wide mode used for windows shown from now on."""
    global _dark_mode
    _dark_mode = dark


def is_dark_mode() -> bool:
    return _dark_mode


class TitleBarFilter(QObject):
    """Applies the current title-bar mode to every top-level window on show."""

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Show and obj.isWidgetType() and obj.isWindow():
            apply_title_bar(obj, _dark_mode)
        return False
