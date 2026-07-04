"""
views/toast.py
Lightweight toast notifications: a small pill that fades in near the bottom
of the window, holds a moment, and fades away. Used for action feedback
("Transfer created", "Exchange rates updated") that shouldn't interrupt like
a message box but is too easy to miss in the status bar.

Qt stylesheets can't animate, so the fade is a QPropertyAnimation driving a
QGraphicsOpacityEffect. Toasts are child widgets of the main window (never
separate OS windows), so they can't steal focus; one toast shows at a time —
a new one replaces the old.
"""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel

from views.fonts import ui_font

_KINDS = {
    "success": ("✓", "#10B981"),
    "info":    ("ℹ", "#6366F1"),
    "warning": ("⚠", "#F59E0B"),
    "error":   ("✕", "#EF4444"),
}

_FADE_IN_MS = 180
_HOLD_MS = 2600
_FADE_OUT_MS = 350


class Toast(QFrame):
    """One transient notification. Use show_toast() instead of this directly."""

    def __init__(self, window, message: str, kind: str = "success") -> None:
        super().__init__(window)
        icon, color = _KINDS.get(kind, _KINDS["success"])

        # Fixed dark pill regardless of theme: readable on every palette.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "background-color: rgba(17, 19, 28, 242);"
            f"border: 1px solid {color};"
            "border-radius: 10px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 16, 9)
        layout.setSpacing(9)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"color: {color}; font-weight: 700; background: transparent; border: none;"
        )
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setFont(ui_font(10))
        msg_lbl.setStyleSheet("color: #F4F5FB; background: transparent; border: none;")
        layout.addWidget(msg_lbl)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._anim = None  # current animation, kept so it isn't GC'd mid-run

    def show_animated(self) -> None:
        parent = self.parentWidget()
        self.adjustSize()
        self.move(
            (parent.width() - self.width()) // 2,
            parent.height() - self.height() - 28,
        )
        self.show()
        self.raise_()
        self._animate(0.0, 1.0, _FADE_IN_MS)
        QTimer.singleShot(_FADE_IN_MS + _HOLD_MS, self._fade_out)

    def _fade_out(self) -> None:
        self._animate(self._effect.opacity(), 0.0, _FADE_OUT_MS,
                      on_done=self._dispose)

    def _animate(self, start: float, end: float, ms: int, on_done=None) -> None:
        anim = QPropertyAnimation(self._effect, b"opacity", self)
        anim.setDuration(ms)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        if on_done:
            anim.finished.connect(on_done)
        anim.start()
        self._anim = anim

    def _dispose(self) -> None:
        self.hide()
        self.deleteLater()


def show_toast(anchor, message: str, kind: str = "success") -> None:
    """Show a toast on the window that contains *anchor* (any widget).

    Safe to call from anywhere in the UI; replaces any toast already showing.
    """
    window = anchor.window() if anchor is not None else None
    if window is None:
        return
    previous = getattr(window, "_active_toast", None)
    if previous is not None:
        try:
            previous._dispose()
        except RuntimeError:
            pass  # already deleted by Qt
    toast = Toast(window, message, kind)
    window._active_toast = toast
    toast.show_animated()
