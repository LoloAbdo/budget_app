"""
views/widgets.py
Small reusable widgets: SummaryCard, AmountLabel, SectionHeader, etc.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QProgressBar, QPushButton, QTableWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QKeySequence, QShortcut

from views.i18n import tr


def make_empty_state(text: str) -> QLabel:
    """A centered, muted placeholder shown in place of an empty table."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setObjectName("muted")
    lbl.setWordWrap(True)
    return lbl


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
    """A rounded card with a title, large value, and optional subtitle."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        color: str = "#6C63FF",
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
        lbl_title.setFont(QFont("Segoe UI", 11))
        layout.addWidget(lbl_title)

        self._lbl_value = QLabel(value)
        self._lbl_value.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self._lbl_value.setStyleSheet(f"color: {color};")
        layout.addWidget(self._lbl_value)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setObjectName("muted")
            lbl_sub.setFont(QFont("Segoe UI", 10))
            layout.addWidget(lbl_sub)

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
        name_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
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
        pct_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
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
        cat_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
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
