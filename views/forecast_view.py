"""
views/forecast_view.py
Cash-flow forecast: projects the combined account balance forward from the
user's recurring income and expenses, so they can see where their money is
heading over the next few months.

The projection is pure arithmetic on existing data (current balances + recurring
schedule) — no new tables. Transfers between the user's own accounts are skipped
because they don't change net worth. The heavy lifting lives in
RecurringService.forecast(); this view just renders it.
"""

from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QScrollArea, QFrame, QTableWidget, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from database import DatabaseManager
from services.recurring_service import RecurringService
from views.widgets import SummaryCard, make_empty_state
from views.sortable import SortableItem, SORT_ROLE, enable_sorting
from views.i18n import tr
from views.theme import chart_colors

GREEN = "#10B981"
RED = "#EF4444"

# Horizon options shown in the dropdown: (label key, number of months).
HORIZONS = [("3 months", 3), ("6 months", 6), ("12 months", 12)]


class ForecastView(QWidget):
    """Projected-balance panel driven by recurring income/expenses."""

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        self._svc = RecurringService(db)
        self._months = 3
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

        # Header with a horizon selector
        head_row = QHBoxLayout()
        title = QLabel(tr("Forecast"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        head_row.addWidget(QLabel(tr("Horizon:")))
        self._horizon_combo = QComboBox()
        for label, months in HORIZONS:
            self._horizon_combo.addItem(tr(label), months)
        self._horizon_combo.currentIndexChanged.connect(self._on_horizon_change)
        head_row.addWidget(self._horizon_combo)
        self._main_layout.addLayout(head_row)

        # Body — rebuilt on every refresh
        self._body = QVBoxLayout()
        self._body.setSpacing(18)
        self._main_layout.addLayout(self._body)
        self._main_layout.addStretch()

    def _on_horizon_change(self) -> None:
        self._months = self._horizon_combo.currentData()
        self.refresh()

    # ── Refresh ─────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._clear_layout(self._body)
        data = self._svc.forecast(self._user["id"], self._months)

        if not data["events"]:
            self._body.addWidget(make_empty_state(
                tr("No recurring income or expenses to forecast.\n"
                   "Add recurring items to see where your balance is heading.")
            ))
            return

        start = data["start_balance"]
        end   = data["end_balance"]
        change = end - start

        # ── Summary cards ────────────────────────────────────────────────────
        cards = QHBoxLayout()
        cards.setSpacing(14)
        cards.addWidget(SummaryCard(tr("Balance Today"), self._money(start), color="#6C63FF"))
        cards.addWidget(SummaryCard(
            tr("Projected ({n} mo)").format(n=self._months),
            self._money(end), color=self._sign_color(end),
        ))
        cards.addWidget(SummaryCard(
            tr("Net Change"),
            ("+" if change >= 0 else "") + self._money(change),
            color=self._sign_color(change),
        ))
        self._body.addLayout(cards)

        # ── Projected-balance chart ──────────────────────────────────────────
        self._body.addWidget(self._build_chart(data["timeline"]))

        # ── Upcoming-events table ────────────────────────────────────────────
        lbl = QLabel(tr("Upcoming recurring activity"))
        lbl.setObjectName("subheading")
        self._body.addWidget(lbl)
        self._body.addWidget(self._build_events_table(data["events"]))

    # ── Builders ─────────────────────────────────────────────────────────────────

    def _build_chart(self, timeline) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(280)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)

        lbl = QLabel(tr("Projected balance over time"))
        lbl.setObjectName("subheading")
        layout.addWidget(lbl)

        dates = [d for d, _ in timeline]
        values = [v for _, v in timeline]

        c = chart_colors()
        fig = Figure(figsize=(6, 3), facecolor=c["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(c["bg"])
        # Step line: the balance holds flat between recurring events.
        line_color = GREEN if values[-1] >= values[0] else RED
        ax.step(dates, values, where="post", color=line_color, linewidth=2)
        ax.fill_between(dates, values, step="post", color=line_color, alpha=0.12)
        ax.axhline(0, color=c["grid"], linewidth=1)
        ax.tick_params(axis="x", colors=c["muted"], labelsize=8, rotation=30)
        ax.tick_params(axis="y", colors=c["muted"], labelsize=8)
        ax.spines[:].set_color(c["grid"])
        fig.tight_layout(pad=1.2)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(220)
        layout.addWidget(canvas)
        return card

    def _build_events_table(self, events) -> QTableWidget:
        cols = [tr("Date"), tr("Name"), tr("Amount"), tr("Projected Balance")]
        tbl = QTableWidget(len(events), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in (0, 2, 3):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        for r, e in enumerate(events):
            iso = e["date"].isoformat()
            tbl.setItem(r, 0, SortableItem(iso))
            tbl.setItem(r, 1, SortableItem(e["name"]))

            amt = SortableItem(self._signed_money(e["amount"]), e["amount"])
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amt.setForeground(QColor(self._sign_color(e["amount"])))
            tbl.setItem(r, 2, amt)

            bal = SortableItem(self._money(e["balance"]), e["balance"])
            bal.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if e["balance"] < 0:
                bal.setForeground(QColor(RED))   # flag a projected overdraft
            tbl.setItem(r, 3, bal)

        tbl.setMinimumHeight(min(420, 46 + len(events) * 36))
        enable_sorting(tbl, 0, Qt.SortOrder.AscendingOrder)
        return tbl

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _money(self, value: float) -> str:
        return f"{self._currency} {value:,.2f}"

    def _signed_money(self, value: float) -> str:
        return ("+" if value >= 0 else "") + self._money(value)

    @staticmethod
    def _sign_color(value: float) -> str:
        return GREEN if value >= 0 else RED

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
