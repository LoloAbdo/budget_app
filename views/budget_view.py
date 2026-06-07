"""
views/budget_view.py
Monthly budget management: create/edit budgets, visualise progress.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDialog, QFormLayout, QDoubleSpinBox, QMessageBox,
    QScrollArea, QFrame, QGridLayout, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from database import DatabaseManager
from views.widgets import BudgetBar
from views.i18n import tr


MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]


class BudgetDialog(QDialog):
    """Add or edit a single budget line."""

    def __init__(
        self,
        db: DatabaseManager,
        user_id: int,
        month: int,
        year: int,
        existing: Optional[dict] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._user_id = user_id
        self._month = month
        self._year = year
        self._existing = existing
        self.setWindowTitle(tr("Edit Budget") if existing else tr("Add Budget"))
        self.setMinimumWidth(380)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._cat_combo = QComboBox()
        for c in self._db.get_categories("Expense"):
            self._cat_combo.addItem(c["name"], c["id"])
        if self._existing:
            for i in range(self._cat_combo.count()):
                if self._cat_combo.itemData(i) == self._existing["category_id"]:
                    self._cat_combo.setCurrentIndex(i)
                    break
        form.addRow(tr("Category"), self._cat_combo)

        self._amount_spin = QDoubleSpinBox()
        self._amount_spin.setRange(0, 1_000_000)
        self._amount_spin.setDecimals(2)
        self._amount_spin.setPrefix("$ ")
        if self._existing:
            self._amount_spin.setValue(self._existing["budget_amount"])
        form.addRow(tr("Budget Amount"), self._amount_spin)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(tr("Save"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self) -> None:
        if self._amount_spin.value() == 0:
            QMessageBox.warning(self, tr("Validation"), tr("Budget amount must be greater than zero."))
            return
        try:
            cat_id = self._cat_combo.currentData()
            amount = self._amount_spin.value()
            self._db.upsert_budget(self._user_id, cat_id, self._month, self._year, amount)
        except Exception as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not save budget:\n{err}").format(err=exc))
            return
        self.accept()


class BudgetView(QWidget):
    """Budget management panel."""

    budget_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
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
        title = QLabel(tr("Budgets"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        # Month / year selectors
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

        add_btn = QPushButton(tr("+ Add Budget"))
        add_btn.clicked.connect(self._add_budget)
        head_row.addWidget(add_btn)
        layout.addLayout(head_row)

        # Summary row
        self._summary_lbl = QLabel()
        self._summary_lbl.setObjectName("muted")
        layout.addWidget(self._summary_lbl)

        # Scroll area for budget bars
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

    def _on_period_change(self) -> None:
        self._month = self._month_combo.currentIndex() + 1
        self._year  = self._year_spin.value()
        self.refresh()

    def refresh(self) -> None:
        # Clear
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        budgets = self._db.get_budgets(self._user["id"], self._month, self._year)

        if not budgets:
            no_lbl = QLabel(tr("No budgets set for this month.\nClick '+ Add Budget' to get started."))
            no_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_lbl.setObjectName("muted")
            self._content_layout.addWidget(no_lbl)
            self._summary_lbl.setText("")
            return

        total_budget  = sum(b["budget_amount"] for b in budgets)
        total_spent   = sum(b["actual_spending"] for b in budgets)
        total_remain  = total_budget - total_spent

        self._summary_lbl.setText(
            tr("Total Budgeted: {budgeted}  •  Spent: {spent}  •  Remaining: {remaining}").format(
                budgeted=f"{self._currency} {total_budget:,.0f}",
                spent=f"{self._currency} {total_spent:,.0f}",
                remaining=f"{self._currency} {total_remain:,.0f}",
            )
        )

        for b in budgets:
            bar_widget = BudgetBar(
                b,
                self._currency,
                on_edit=lambda _, bud=b: self._edit_budget(bud),
                on_delete=lambda _, bud=b: self._delete_budget(bud),
            )
            self._content_layout.addWidget(bar_widget)

        self._content_layout.addStretch()

    def _add_budget(self) -> None:
        dlg = BudgetDialog(self._db, self._user["id"], self._month, self._year, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.budget_changed.emit()

    def _edit_budget(self, bud: dict) -> None:
        dlg = BudgetDialog(self._db, self._user["id"], self._month, self._year, existing=bud, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.budget_changed.emit()

    def _delete_budget(self, bud: dict) -> None:
        reply = QMessageBox.question(
            self,
            tr("Delete Budget"),
            tr("Delete the budget for '{name}'?").format(name=bud["category_name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._db.delete_budget(bud["id"])
            except Exception as exc:
                QMessageBox.critical(self, tr("Error"), tr("Could not delete budget:\n{err}").format(err=exc))
                return
            self.refresh()
            self.budget_changed.emit()