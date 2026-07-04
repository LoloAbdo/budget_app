"""
views/reports_view.py
Reports panel: monthly summary, category analysis, cash flow.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QFrame, QScrollArea, QFileDialog,
    QMessageBox, QTabWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from database import DatabaseManager
from reports.pdf_report import PDFReportGenerator
from services.import_export_service import ImportExportService
from views.chartutil import money_axis
from views.i18n import tr, month_abbr
from views.theme import chart_colors

MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]


class ReportsView(QWidget):
    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        self._pdf_gen = PDFReportGenerator(db)
        self._ie = ImportExportService(db)
        now = datetime.now()
        self._month = now.month
        self._year  = now.year
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        head_row = QHBoxLayout()
        title = QLabel(tr("Reports"))
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

        pdf_btn = QPushButton(tr("📄 Export PDF"))
        pdf_btn.clicked.connect(self._export_pdf)
        head_row.addWidget(pdf_btn)

        csv_btn = QPushButton(tr("📊 Export CSV"))
        csv_btn.setObjectName("secondary")
        csv_btn.clicked.connect(self._export_csv)
        head_row.addWidget(csv_btn)

        xlsx_btn = QPushButton(tr("📗 Export Excel"))
        xlsx_btn.setObjectName("secondary")
        xlsx_btn.clicked.connect(self._export_xlsx)
        head_row.addWidget(xlsx_btn)

        layout.addLayout(head_row)

        # Tabs
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

    def _on_period_change(self) -> None:
        self._month = self._month_combo.currentIndex() + 1
        self._year  = self._year_spin.value()
        self.refresh()

    def refresh(self) -> None:
        self._tabs.clear()

        summary  = self._db.get_monthly_summary(self._user["id"], self._month, self._year)
        spending = self._db.get_spending_by_category(self._user["id"], self._month, self._year)
        monthly  = self._db.get_monthly_totals(self._user["id"], self._year)

        self._tabs.addTab(self._build_summary_tab(summary), tr("Monthly Summary"))
        self._tabs.addTab(self._build_category_tab(spending), tr("Category Analysis"))
        self._tabs.addTab(self._build_cashflow_tab(monthly), tr("Cash Flow"))

    # ── Tab builders ──────────────────────────────────────────────────────────

    def _build_summary_tab(self, summary: dict) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        month_name = tr(MONTHS[self._month - 1])
        title = QLabel(tr("{month} {year} Summary").format(month=month_name, year=self._year))
        title.setObjectName("subheading")
        layout.addWidget(title)

        for label, value, color in [
            (tr("Total Income"),   f"{self._currency} {summary['income']:,.2f}",   "#10B981"),
            (tr("Total Expenses"), f"{self._currency} {summary['expenses']:,.2f}", "#EF4444"),
            (tr("Net Savings"),    f"{self._currency} {summary['savings']:,.2f}",
             "#10B981" if summary["savings"] >= 0 else "#EF4444"),
            (tr("Savings Rate"),   f"{summary['savings_rate']:.1f}%",              "#F59E0B"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setMinimumWidth(160)
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 16px;")
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch()
            layout.addLayout(row)

        layout.addStretch()
        return w

    def _build_category_tab(self, spending: list[dict]) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)

        if not spending:
            layout.addWidget(QLabel(tr("No expense data for this period.")))
            return w

        c = chart_colors()
        fig = Figure(figsize=(8, 4), facecolor=c["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(c["bg"])

        cats   = [r["name"] for r in spending[:10]]
        totals = [r["total"] for r in spending[:10]]
        colors = [r.get("color", "#607D8B") for r in spending[:10]]

        bars = ax.barh(cats[::-1], totals[::-1], color=colors[::-1], alpha=0.9)
        ax.tick_params(colors=c["muted"], labelsize=9)
        ax.spines[:].set_color(c["grid"])
        ax.set_xlabel(tr("Amount"), color=c["muted"], fontsize=9)
        money_axis(ax, axis="x")

        for bar, val in zip(bars, totals[::-1]):
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                    f"{self._currency} {val:,.0f}", va="center", color=c["fg"], fontsize=8)

        fig.tight_layout(pad=1.5)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        return w

    def _build_cashflow_tab(self, monthly: list[dict]) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)

        c = chart_colors()
        fig = Figure(figsize=(8, 4), facecolor=c["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(c["bg"])

        inc_vals = [0.0] * 12
        exp_vals = [0.0] * 12
        for r in monthly:
            idx = int(r["month"]) - 1
            inc_vals[idx] = r["income"]
            exp_vals[idx] = r["expenses"]

        net = [i - e for i, e in zip(inc_vals, exp_vals)]
        x = list(range(12))

        ax.plot(x, inc_vals, color=c["income"],  linewidth=2, marker="o", markersize=5, label=tr("Income"))
        ax.plot(x, exp_vals, color=c["expense"], linewidth=2, marker="o", markersize=5, label=tr("Expenses"))
        ax.fill_between(x, inc_vals, exp_vals,
                        where=[i >= e for i, e in zip(inc_vals, exp_vals)],
                        alpha=0.15, color=c["income"])
        ax.fill_between(x, inc_vals, exp_vals,
                        where=[i < e for i, e in zip(inc_vals, exp_vals)],
                        alpha=0.15, color=c["expense"])

        ax.set_xticks(x)
        ax.set_xticklabels(month_abbr(), fontsize=9, color=c["muted"])
        ax.tick_params(axis="y", colors=c["muted"], labelsize=9)
        ax.spines[:].set_color(c["grid"])
        money_axis(ax)
        ax.legend(framealpha=0, labelcolor=c["fg"], fontsize=9)
        fig.tight_layout(pad=1.5)

        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        return w

    # ── Exports ────────────────────────────────────────────────────────────────

    def _export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save PDF Report"), f"report_{self._year}_{self._month:02d}.pdf",
            "PDF Files (*.pdf)",
        )
        if path:
            try:
                self._pdf_gen.generate_monthly_report(
                    self._user["id"], self._month, self._year, path
                )
                QMessageBox.information(self, tr("Exported"), tr("PDF saved to:\n{path}").format(path=path))
            except Exception as e:
                QMessageBox.critical(self, tr("Export Failed"), str(e))

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save CSV"), "transactions.csv", "CSV Files (*.csv)"
        )
        if path:
            count = self._ie.export_csv(self._user["id"], path)
            QMessageBox.information(
                self, tr("Exported"),
                tr("{n} transactions saved to:\n{path}").format(n=count, path=path),
            )

    def _export_xlsx(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save Excel"), "transactions.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            count = self._ie.export_excel(self._user["id"], path)
            QMessageBox.information(
                self, tr("Exported"),
                tr("{n} transactions saved to:\n{path}").format(n=count, path=path),
            )
