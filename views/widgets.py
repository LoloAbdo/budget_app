"""
views/widgets.py
Small reusable widgets: SummaryCard, AmountLabel, SectionHeader, etc.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QProgressBar, QPushButton, QTableWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut

from views.fonts import scaled, ui_font
from views.i18n import tr

# Cache of colored-circle icons keyed by hex color (a dozen at most per run).
_DOT_CACHE: dict[str, QIcon] = {}


def category_dot(color: str) -> QIcon:
    """A small colored circle icon that tags a category with its color in tables."""
    icon = _DOT_CACHE.get(color)
    if icon is None:
        pix = QPixmap(12, 12)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
        icon = QIcon(pix)
        _DOT_CACHE[color] = icon
    return icon


GREEN = "#10B981"
RED = "#EF4444"


def delta_text(current: float, previous, invert: bool = False):
    """(text, color) for a percent change vs the previous period, or None.

    None when there's no meaningful comparison (no/zero previous value) or the
    change is flat. ``invert`` flips the good/bad coloring for metrics where
    an increase is bad (expenses).
    """
    if previous is None or abs(previous) < 0.005:
        return None
    pct = (current - previous) / abs(previous) * 100
    if abs(pct) < 0.05:
        return None
    up = pct > 0
    good = (not up) if invert else up
    return f"{'▲' if up else '▼'} {abs(pct):,.0f}%", (GREEN if good else RED)


def delta_points(current: float, previous):
    """Like delta_text but for values already in percent (savings rate):
    the change is shown in points ('▲ 3.2 pts') rather than percent-of."""
    if previous is None:
        return None
    diff = current - previous
    if abs(diff) < 0.05:
        return None
    return f"{'▲' if diff > 0 else '▼'} {abs(diff):,.1f} pts", (GREEN if diff > 0 else RED)


class EmptyState(QFrame):
    """Centered placeholder for empty tables/panels: icon, message, and an
    optional call-to-action button so a blank screen tells you what to do."""

    def __init__(self, text: str, icon: str = "📭",
                 action_text: str = "", on_action=None, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 28, 20, 28)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFont(QFont("Segoe UI Emoji", scaled(28)))
        layout.addWidget(icon_lbl)

        self._text_lbl = QLabel(text)
        self._text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_lbl.setObjectName("muted")
        self._text_lbl.setWordWrap(True)
        layout.addWidget(self._text_lbl)

        self._action_btn = None
        if action_text and on_action:
            row = QHBoxLayout()
            row.addStretch()
            self._action_btn = QPushButton(action_text)
            self._action_btn.clicked.connect(on_action)
            row.addWidget(self._action_btn)
            row.addStretch()
            layout.addLayout(row)

    def setText(self, text: str) -> None:
        self._text_lbl.setText(text)

    def set_action_visible(self, visible: bool) -> None:
        """Hide the CTA when it doesn't apply (e.g. filters hid the rows)."""
        if self._action_btn is not None:
            self._action_btn.setVisible(visible)


def make_empty_state(text: str, icon: str = "📭",
                     action_text: str = "", on_action=None) -> EmptyState:
    """Build an EmptyState (kept as a function for the existing call sites)."""
    return EmptyState(text, icon, action_text, on_action)


def add_table_shortcuts(table: QTableWidget, on_delete=None, on_edit=None) -> None:
    """Wire keyboard shortcuts to a data table for quicker, mouse-free editing.

    - ``Delete``        → ``on_delete`` (remove the selected row)
    - ``Enter``/``Return`` → ``on_edit`` (edit the selected row, like a double-click)

    Shortcuts use ``WidgetShortcut`` context so they fire only while the table has
    focus. The connected slots already no-op when nothing is selected.
    """
    def _bind(key, slot) -> None:
        sc = QShortcut(QKeySequence(key), table)
        sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        sc.activated.connect(slot)

    if on_delete:
        _bind(QKeySequence.StandardKey.Delete, on_delete)
    if on_edit:
        _bind(Qt.Key.Key_Return, on_edit)
        _bind(Qt.Key.Key_Enter, on_edit)   # numeric-keypad Enter


class SummaryCard(QFrame):
    """A rounded card with a title, large value, optional subtitle, and an
    optional delta line — a (text, color) pair like ('▲ 12%', green) from
    delta_text()/delta_points(), rendered with a muted 'vs last month'."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        color: str = "#6C63FF",
        delta=None,
        delta_label: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("muted")
        lbl_title.setFont(ui_font(11))
        layout.addWidget(lbl_title)

        self._lbl_value = QLabel(value)
        self._lbl_value.setFont(ui_font(22, QFont.Weight.Bold))
        self._lbl_value.setStyleSheet(f"color: {color};")
        layout.addWidget(self._lbl_value)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setObjectName("muted")
            lbl_sub.setFont(ui_font(10))
            layout.addWidget(lbl_sub)

        if delta:
            d_text, d_color = delta
            row = QHBoxLayout()
            row.setSpacing(6)
            d_lbl = QLabel(d_text)
            d_lbl.setStyleSheet(f"color: {d_color}; font-size: 11px; font-weight: 700;")
            row.addWidget(d_lbl)
            if delta_label:
                ctx = QLabel(delta_label)
                ctx.setObjectName("muted")
                ctx.setFont(ui_font(9))
                row.addWidget(ctx)
            row.addStretch()
            layout.addLayout(row)

    def update_value(self, value: str, color: str | None = None) -> None:
        self._lbl_value.setText(value)
        if color:
            self._lbl_value.setStyleSheet(f"color: {color};")


class GoalProgressCard(QFrame):
    """Card for a financial goal with a progress bar."""

    def __init__(self, goal: dict, currency: str = "CAD", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        name_lbl = QLabel(goal["goal_name"])
        name_lbl.setFont(ui_font(13, QFont.Weight.Bold))
        layout.addWidget(name_lbl)

        pct = min(100, int(goal["current_amount"] / max(goal["target_amount"], 1) * 100))

        bar = QProgressBar()
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setFixedHeight(10)
        if pct >= 100:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #10B981; }")
        elif pct >= 60:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #F59E0B; }")
        layout.addWidget(bar)

        row = QHBoxLayout()
        saved_lbl = QLabel(f"{currency} {goal['current_amount']:,.0f} / {currency} {goal['target_amount']:,.0f}")
        saved_lbl.setObjectName("muted")
        row.addWidget(saved_lbl)
        row.addStretch()
        pct_lbl = QLabel(f"{pct}%")
        pct_lbl.setFont(ui_font(11, QFont.Weight.Bold))
        row.addWidget(pct_lbl)
        layout.addLayout(row)

        date_lbl = QLabel(tr("Target: {date}").format(date=goal['target_date']))
        date_lbl.setObjectName("muted")
        layout.addWidget(date_lbl)


class BudgetBar(QFrame):
    """Inline budget row: category name, bar, amounts, edit/delete buttons."""

    def __init__(
        self,
        budget: dict,
        currency: str = "CAD",
        on_edit=None,
        on_delete=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # ── Top row: category name | amounts | action buttons ────────────────
        top = QHBoxLayout()
        cat_lbl = QLabel(budget["category_name"])
        cat_lbl.setFont(ui_font(12, QFont.Weight.Bold))
        top.addWidget(cat_lbl)
        top.addStretch()

        spent    = budget.get("actual_spending", 0.0)
        budgeted = budget["budget_amount"]
        remaining = budgeted - spent
        pct = min(100, int(spent / max(budgeted, 1) * 100))

        amounts = QLabel(f"{currency} {spent:,.0f} / {currency} {budgeted:,.0f}")
        amounts.setObjectName("muted")
        top.addWidget(amounts)

        if on_edit:
            edit_btn = QPushButton("🖊")
            edit_btn.setObjectName("secondary")
            edit_btn.setFixedSize(28, 28)
            edit_btn.setToolTip(tr("Edit budget"))
            edit_btn.clicked.connect(on_edit)
            top.addWidget(edit_btn)

        if on_delete:
            del_btn = QPushButton("🗑")
            del_btn.setObjectName("danger")
            del_btn.setFixedSize(28, 28)
            del_btn.setToolTip(tr("Delete budget"))
            del_btn.clicked.connect(on_delete)
            top.addWidget(del_btn)

        layout.addLayout(top)

        # ── Progress bar ──────────────────────────────────────────────────────
        bar = QProgressBar()
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        if pct >= 100:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #EF4444; }")
        elif pct >= 80:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #F59E0B; }")
        else:
            bar.setStyleSheet("QProgressBar::chunk { background-color: #10B981; }")
        layout.addWidget(bar)

        # ── Status line ───────────────────────────────────────────────────────
        status_color = "#EF4444" if remaining < 0 else ("#F59E0B" if pct >= 80 else "#10B981")
        status_lbl = QLabel(
            f"{tr('Over budget') if remaining < 0 else tr('Remaining')}: "
            f"{currency} {abs(remaining):,.0f}"
        )
        status_lbl.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        layout.addWidget(status_lbl)
