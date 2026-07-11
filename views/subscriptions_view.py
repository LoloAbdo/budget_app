"""
views/subscriptions_view.py
Auto-detected subscriptions panel.

Scans transaction history for charges that recur on a regular cadence with a
consistent amount (see ``DatabaseManager.get_detected_subscriptions``) and
lists them with an estimated monthly / yearly cost, so the user can spot
forgotten or creeping recurring spend. Read-only — it detects, it doesn't
create recurring rules.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from database import DatabaseManager
from views.widgets import category_dot, make_empty_state, SummaryCard, ColumnWidths
from views.i18n import tr
from views.sortable import SortableItem, SORT_ROLE, enable_sorting


# Localized cadence label + how many times per year it bills (for annual totals).
_CADENCE = {
    "weekly":    ("Weekly",    52),
    "biweekly":  ("Bi-weekly", 26),
    "monthly":   ("Monthly",   12),
    "quarterly": ("Quarterly", 4),
    "yearly":    ("Yearly",    1),
}


class SubscriptionsView(QWidget):
    """Panel listing subscriptions detected from transaction history."""

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        self._build_ui()
        self.refresh()

    # ── Build skeleton ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(24, 20, 24, 20)
        self._main_layout.setSpacing(16)
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Refresh ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._clear_layout(self._main_layout)

        subs = self._db.get_detected_subscriptions(self._user["id"])

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel(tr("Subscriptions"))
        title.setObjectName("heading")
        header.addWidget(title)
        header.addStretch()
        refresh_btn = QPushButton(tr("↻ Refresh"))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        self._main_layout.addLayout(header)

        sub = QLabel(tr(
            "Recurring charges detected automatically from your transaction history."
        ))
        sub.setObjectName("muted")
        self._main_layout.addWidget(sub)

        if not subs:
            self._main_layout.addWidget(make_empty_state(
                tr("No subscriptions detected yet.\n"
                   "A few months of transaction history are needed to spot recurring charges."),
                icon="🧾",
            ))
            self._main_layout.addStretch()
            return

        # ── Summary cards: count, monthly, yearly ─────────────────────────────
        monthly_total = sum(s["monthly_cost"] for s in subs)
        yearly_total = monthly_total * 12
        cards = QHBoxLayout()
        cards.setSpacing(14)
        cards.addWidget(SummaryCard(
            tr("Subscriptions"), str(len(subs)), color="#6C63FF"))
        cards.addWidget(SummaryCard(
            tr("Est. Monthly Cost"), f"{self._currency} {monthly_total:,.2f}", color="#EF4444"))
        cards.addWidget(SummaryCard(
            tr("Est. Yearly Cost"), f"{self._currency} {yearly_total:,.2f}", color="#F59E0B"))
        self._main_layout.addLayout(cards)

        # ── Table ─────────────────────────────────────────────────────────────
        self._main_layout.addWidget(self._build_table(subs))
        self._main_layout.addStretch()

    def _build_table(self, subs: list[dict]) -> QTableWidget:
        cols = [tr("Subscription"), tr("Amount"), tr("Frequency"), tr("Category"),
                tr("Last charged"), tr("Next (est.)"), tr("Per month")]
        tbl = QTableWidget(len(subs), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(True)
        hdr.setMinimumSectionSize(70)

        for row, s in enumerate(subs):
            cur = s["currency"]
            freq_label = tr(_CADENCE.get(s["cadence"], (s["cadence"].title(), 12))[0])
            cells = [
                (s["name"], None),
                (f"{cur} {s['amount']:,.2f}", s["amount"]),
                (freq_label, None),
                (s.get("category_name") or "—", None),
                (s["last_date"], None),
                (s["next_date"], None),
                (f"{cur} {s['monthly_cost']:,.2f}", s["monthly_cost"]),
            ]
            for col, (text, sort_val) in enumerate(cells):
                item = SortableItem(text)
                if col == 3 and s.get("category_color"):
                    item.setIcon(category_dot(s["category_color"]))
                if col in (1, 6):
                    item.setData(SORT_ROLE, sort_val)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 6:
                    item.setForeground(QColor("#EF4444"))
                tbl.setItem(row, col, item)

        col_widths = ColumnWidths(tbl, "subscriptions", self._user["id"])
        if col_widths.has_saved():
            col_widths.restore()
        else:
            with col_widths.muted():
                tbl.resizeColumnsToContents()
        tbl.setMinimumHeight(min(520, 46 + len(subs) * 40))
        enable_sorting(tbl, 6, Qt.SortOrder.DescendingOrder)
        return tbl

    # ── Utilities ──────────────────────────────────────────────────────────────

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                child = item.layout()
                if child is not None:
                    self._clear_layout(child)
                    child.deleteLater()
