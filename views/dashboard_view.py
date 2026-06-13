"""
views/dashboard_view.py
Main dashboard: summary cards + matplotlib charts + recent transactions.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QGridLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from database import DatabaseManager
from views.widgets import SummaryCard
from views.i18n import tr, month_abbr
from views.theme import chart_colors


class DashboardView(QWidget):
    """The home dashboard panel."""

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        self._build_ui()
        self.refresh()

    # ── Build skeleton ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(24, 20, 24, 20)
        self._main_layout.setSpacing(20)
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload all data and re-render the dashboard."""
        # Clear existing content (recursively — cards & charts live in nested layouts)
        self._clear_layout(self._main_layout)

        now = datetime.now()
        month, year = now.month, now.year

        summary  = self._db.get_monthly_summary(self._user["id"], month, year)
        balance  = self._db.get_total_balance(self._user["id"])
        spending = self._db.get_spending_by_category(self._user["id"], month, year)
        monthly  = self._db.get_monthly_totals(self._user["id"], year)
        networth = self._db.get_net_worth_history(self._user["id"], 12)
        recent   = self._db.get_transactions(self._user["id"], limit=10)

        # ── Page header ───────────────────────────────────────────────────────
        first_name = self._user["name"].split()[0]
        heading = QLabel(
            tr("{greeting}, {name}!").format(
                greeting=tr(self._time_greeting()), name=first_name
            )
        )
        heading.setObjectName("heading")
        self._main_layout.addWidget(heading)

        sub = QLabel(
            tr("{date}  •  {month} Overview").format(
                date=now.strftime("%A, %B %d %Y"),
                month=tr(now.strftime("%B")),
            )
        )
        sub.setObjectName("muted")
        self._main_layout.addWidget(sub)

        # ── Summary cards ──────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        savings_color = "#10B981" if summary["savings"] >= 0 else "#EF4444"

        cards_data = [
            (tr("Total Balance"),    f"{self._currency} {balance:,.2f}",          "#6C63FF"),
            (tr("Monthly Income"),   f"{self._currency} {summary['income']:,.2f}", "#10B981"),
            (tr("Monthly Expenses"), f"{self._currency} {summary['expenses']:,.2f}","#EF4444"),
            (tr("Net Savings"),      f"{self._currency} {summary['savings']:,.2f}", savings_color),
            (tr("Savings Rate"),     f"{summary['savings_rate']:.1f}%",            "#F59E0B"),
        ]
        for title, val, color in cards_data:
            card = SummaryCard(title, val, color=color)
            cards_row.addWidget(card)

        self._main_layout.addLayout(cards_row)

        # ── Charts row ─────────────────────────────────────────────────────────
        charts_row = QHBoxLayout()
        charts_row.setSpacing(14)

        if spending:
            charts_row.addWidget(self._build_pie_chart(spending), 1)
        charts_row.addWidget(self._build_bar_chart(monthly), 2)

        self._main_layout.addLayout(charts_row)

        # ── Net worth trend ─────────────────────────────────────────────────────
        if networth:
            self._main_layout.addWidget(self._build_net_worth_chart(networth))

        # ── Recent transactions ────────────────────────────────────────────────
        section_lbl = QLabel(tr("Recent Transactions"))
        section_lbl.setObjectName("subheading")
        self._main_layout.addWidget(section_lbl)

        self._main_layout.addWidget(self._build_txn_table(recent))

    # ── Chart builders ─────────────────────────────────────────────────────────

    def _chart_bg(self) -> str:
        """Return the chart background for the active theme."""
        return chart_colors()["bg"]

    def _build_pie_chart(self, spending: list[dict]) -> QFrame:
        """Spending-by-category donut chart."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(280)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)

        lbl = QLabel(tr("Spending by Category"))
        lbl.setObjectName("subheading")
        layout.addWidget(lbl)

        c = chart_colors()
        fig = Figure(figsize=(4, 3), facecolor=c["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(c["bg"])
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

        labels = [r["name"] for r in spending[:7]]
        vals   = [r["total"] for r in spending[:7]]
        colors = [r.get("color", "#607D8B") for r in spending[:7]]

        wedges, _ = ax.pie(
            vals, labels=None, colors=colors,
            startangle=90, wedgeprops={"width": 0.6, "edgecolor": c["bg"]},
        )
        ax.legend(
            wedges, labels,
            loc="lower center", ncol=2, framealpha=0,
            labelcolor=c["fg"], fontsize=8,
            bbox_to_anchor=(0.5, -0.12),
        )

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(230)
        layout.addWidget(canvas)
        return card

    def _build_bar_chart(self, monthly: list[dict]) -> QFrame:
        """Monthly income vs expenses bar chart for the current year."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(280)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)

        lbl = QLabel(tr("Income vs Expenses — Monthly"))
        lbl.setObjectName("subheading")
        layout.addWidget(lbl)

        c = chart_colors()
        fig = Figure(figsize=(6, 3), facecolor=c["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(c["bg"])

        month_nums = list(range(1, 13))
        inc_vals   = [0.0] * 12
        exp_vals   = [0.0] * 12
        for r in monthly:
            idx = int(r["month"]) - 1
            inc_vals[idx] = r["income"]
            exp_vals[idx] = r["expenses"]

        x = range(12)
        w = 0.35

        ax.bar([i - w/2 for i in x], inc_vals, width=w, color=c["income"],  label=tr("Income"),   alpha=0.9)
        ax.bar([i + w/2 for i in x], exp_vals, width=w, color=c["expense"], label=tr("Expenses"), alpha=0.9)

        ax.set_xticks(list(x))
        ax.set_xticklabels(month_abbr(), fontsize=8, color=c["muted"])
        ax.tick_params(axis="y", colors=c["muted"], labelsize=8)
        ax.spines[:].set_color(c["grid"])
        ax.yaxis.set_tick_params(labelcolor=c["muted"])
        ax.legend(framealpha=0, labelcolor=c["fg"], fontsize=9)
        fig.tight_layout(pad=1.2)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(230)
        layout.addWidget(canvas)
        return card

    def _build_net_worth_chart(self, history: list[dict]) -> QFrame:
        """Net-worth-over-time line chart for the last 12 months."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(280)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)

        lbl = QLabel(tr("Net Worth — Last 12 Months"))
        lbl.setObjectName("subheading")
        layout.addWidget(lbl)

        c = chart_colors()
        fig = Figure(figsize=(8, 3), facecolor=c["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(c["bg"])

        # Labels: localized 3-letter month abbreviations.
        abbr = month_abbr()
        labels = [abbr[int(p["month"][5:]) - 1] for p in history]
        vals   = [p["balance"] for p in history]
        x = range(len(vals))

        ax.plot(list(x), vals, color=c["accent"], linewidth=2, marker="o", markersize=4)
        ax.fill_between(list(x), vals, min(vals + [0]), color=c["accent"], alpha=0.12)
        ax.axhline(0, color=c["grid"], linewidth=0.8)

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8, color=c["muted"])
        ax.tick_params(axis="y", colors=c["muted"], labelsize=8)
        ax.spines[:].set_color(c["grid"])
        ax.yaxis.set_tick_params(labelcolor=c["muted"])
        fig.tight_layout(pad=1.2)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(230)
        layout.addWidget(canvas)
        return card

    # ── Transaction table ──────────────────────────────────────────────────────

    def _build_txn_table(self, transactions: list[dict]) -> QTableWidget:
        cols = [tr("Date"), tr("Description"), tr("Category"), tr("Account"), tr("Amount")]
        tbl = QTableWidget(len(transactions), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(False)
        hdr.setMinimumSectionSize(60)
        tbl.setColumnWidth(0, 100)   # Date
        tbl.setColumnWidth(1, 220)   # Description
        tbl.setColumnWidth(2, 130)   # Category
        tbl.setColumnWidth(3, 100)   # Amount

        for row_idx, txn in enumerate(transactions):
            items = [
                txn["date"],
                txn["description"],
                txn.get("category_name") or "—",
                txn.get("account_name") or "—",
                f"{self._currency} {txn['amount']:,.2f}",
            ]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col_idx == 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    color = "#10B981" if txn.get("category_type") == "Income" else "#EF4444"
                    item.setForeground(QColor(color))
                tbl.setItem(row_idx, col_idx, item)

        tbl.resizeColumnsToContents()
        tbl.setMinimumHeight(min(400, 46 + len(transactions) * 40))
        return tbl

    # ── Utilities ──────────────────────────────────────────────────────────────

    def _clear_layout(self, layout) -> None:
        """Recursively remove every widget/sub-layout so nothing ghosts on top."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)      # remove from view immediately
                w.deleteLater()        # free on the next event loop pass
            else:
                child = item.layout()
                if child is not None:
                    self._clear_layout(child)
                    child.deleteLater()

    @staticmethod
    def _time_greeting() -> str:
        """Return an English greeting key; tr() localizes it at the call site."""
        h = datetime.now().hour
        if h < 12:
            return "Good morning"
        elif h < 17:
            return "Good afternoon"
        return "Good evening"
