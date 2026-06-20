"""
views/savings_view.py
Savings report: groups all Savings accounts and tracks the interest / gains
earned on them over time.

Interest is derived automatically: whenever a Savings account's balance is
edited, the unexplained difference (i.e. the part not coming from recorded
transfers/transactions) is posted as a signed entry under the system
'Interest' category. This view aggregates those entries per account and period.
"""

from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from database import DatabaseManager
from views.widgets import SummaryCard
from views.i18n import tr, month_abbr
from views.theme import chart_colors
from views.sortable import SortableItem, enable_sorting

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
GREEN = "#10B981"
RED = "#EF4444"


class SavingsView(QWidget):
    """Savings & interest report panel."""

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        now = datetime.now()
        self._month = now.month
        self._year = now.year
        self._build_ui()
        self.refresh()

    # ── Build skeleton ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(24, 20, 24, 20)
        self._main_layout.setSpacing(18)
        scroll.setWidget(container)

        # Header row with period selectors
        head_row = QHBoxLayout()
        title = QLabel(tr("Savings"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        self._month_combo = QComboBox()
        for m in MONTHS:
            self._month_combo.addItem(tr(m))
        self._month_combo.setCurrentIndex(self._month - 1)
        self._month_combo.currentIndexChanged.connect(self._on_period_change)
        head_row.addWidget(self._month_combo)

        self._year_spin = QSpinBox()
        self._year_spin.setRange(2000, 2100)
        self._year_spin.setValue(self._year)
        self._year_spin.valueChanged.connect(self._on_period_change)
        head_row.addWidget(self._year_spin)

        self._main_layout.addLayout(head_row)

        # Body placeholder — rebuilt on refresh
        self._body = QVBoxLayout()
        self._body.setSpacing(18)
        self._main_layout.addLayout(self._body)
        self._main_layout.addStretch()

    def _on_period_change(self) -> None:
        self._month = self._month_combo.currentIndex() + 1
        self._year = self._year_spin.value()
        self.refresh()

    # ── Refresh ─────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        # Clear body (recursive — cards live in a nested layout)
        self._clear_layout(self._body)

        summary = self._db.get_interest_summary(self._user["id"], self._month, self._year)

        if not summary:
            empty = QLabel(tr("No savings accounts.\nAdd a Savings account to start tracking interest."))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("muted")
            self._body.addWidget(empty)
            return

        total_balance = sum(s["current_balance"] for s in summary)
        total_month   = sum(s["interest_month"] for s in summary)
        total_year    = sum(s["interest_year"] for s in summary)
        total_all     = sum(s["interest_total"] for s in summary)

        # ── Summary cards ────────────────────────────────────────────────────
        cards = QHBoxLayout()
        cards.setSpacing(14)
        cards.addWidget(SummaryCard(tr("Total Savings"), self._money(total_balance), color="#6C63FF"))
        cards.addWidget(SummaryCard(tr("Interest This Month"), self._money(total_month), color=self._sign_color(total_month)))
        cards.addWidget(SummaryCard(tr("Interest This Year"), self._money(total_year), color=self._sign_color(total_year)))
        cards.addWidget(SummaryCard(tr("Interest All-Time"), self._money(total_all), color=self._sign_color(total_all)))
        self._body.addLayout(cards)

        # ── Per-account table ────────────────────────────────────────────────
        self._body.addWidget(self._build_accounts_table(summary))

        # ── Interest-over-time chart ─────────────────────────────────────────
        self._body.addWidget(self._build_chart())

        # ── Recent interest activity ─────────────────────────────────────────
        hist_lbl = QLabel(tr("Recent interest activity"))
        hist_lbl.setObjectName("subheading")
        self._body.addWidget(hist_lbl)
        self._body.addWidget(self._build_history_table())

    # ── Builders ────────────────────────────────────────────────────────────────

    def _build_accounts_table(self, summary: list[dict]) -> QTableWidget:
        cols = [tr("Account"), tr("Balance"), tr("This Month"), tr("This Year"), tr("All-Time")]
        tbl = QTableWidget(len(summary), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, len(cols)):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        for r, s in enumerate(summary):
            values = [
                (s["account_name"], None, None),
                (self._money(s["current_balance"]), None, s["current_balance"]),
                (self._money(s["interest_month"]), self._sign_color(s["interest_month"]), s["interest_month"]),
                (self._money(s["interest_year"]),  self._sign_color(s["interest_year"]),  s["interest_year"]),
                (self._money(s["interest_total"]), self._sign_color(s["interest_total"]), s["interest_total"]),
            ]
            for c, (text, color, sort_key) in enumerate(values):
                item = SortableItem(text, sort_key)
                if c >= 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if color and abs(self._raw(s, c)) >= 0.005:
                    item.setForeground(QColor(color))
                tbl.setItem(r, c, item)

        tbl.setMinimumHeight(min(360, 46 + len(summary) * 40))
        enable_sorting(tbl, 0, Qt.SortOrder.AscendingOrder)
        return tbl

    @staticmethod
    def _raw(s: dict, col: int) -> float:
        return {2: s["interest_month"], 3: s["interest_year"], 4: s["interest_total"]}.get(col, 0.0)

    def _build_chart(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(280)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)

        lbl = QLabel(tr("Interest earned over time"))
        lbl.setObjectName("subheading")
        layout.addWidget(lbl)

        monthly = self._db.get_interest_monthly(self._user["id"], self._year)
        vals = [0.0] * 12
        for r in monthly:
            vals[int(r["month"]) - 1] = r["interest"] or 0.0

        c = chart_colors()
        fig = Figure(figsize=(6, 3), facecolor=c["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(c["bg"])
        colors = [c["income"] if v >= 0 else c["expense"] for v in vals]
        ax.bar(range(12), vals, color=colors, alpha=0.9)
        ax.axhline(0, color=c["grid"], linewidth=1)
        ax.set_xticks(range(12))
        ax.set_xticklabels(month_abbr(), fontsize=8, color=c["muted"])
        ax.tick_params(axis="y", colors=c["muted"], labelsize=8)
        ax.spines[:].set_color(c["grid"])
        fig.tight_layout(pad=1.2)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(220)
        layout.addWidget(canvas)
        return card

    def _build_history_table(self) -> QTableWidget:
        entries = self._db.get_interest_entries(self._user["id"], limit=50)
        cols = [tr("Date"), tr("Account"), tr("Amount")]
        tbl = QTableWidget(len(entries), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        for r, e in enumerate(entries):
            tbl.setItem(r, 0, SortableItem(e["date"]))
            tbl.setItem(r, 1, SortableItem(e["account_name"]))
            amt = SortableItem(self._money(e["amount"]), e["amount"])
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amt.setForeground(QColor(self._sign_color(e["amount"])))
            tbl.setItem(r, 2, amt)

        tbl.setMinimumHeight(min(360, 46 + max(len(entries), 1) * 36))
        enable_sorting(tbl, 0, Qt.SortOrder.DescendingOrder)
        return tbl

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _money(self, value: float) -> str:
        return f"{self._currency} {value:,.2f}"

    @staticmethod
    def _sign_color(value: float) -> str:
        return GREEN if value >= 0 else RED

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)      # remove from view immediately (no ghosting)
                w.deleteLater()
            else:
                child = item.layout()
                if child is not None:
                    self._clear_layout(child)
                    child.deleteLater()
