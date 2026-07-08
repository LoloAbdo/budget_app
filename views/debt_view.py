"""
views/debt_view.py
Debt payoff planner: list debts, choose a strategy (snowball / avalanche),
add an extra monthly payment and see when you'll be debt-free.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QMessageBox, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from database import DatabaseManager
from services import debt_service
from views.fonts import ui_font
from views.i18n import tr


class DebtDialog(QDialog):
    """Add / edit a single debt."""

    def __init__(
        self,
        db: DatabaseManager,
        user_id: int,
        currency: str = "CAD",
        debt: Optional[dict] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._user_id = user_id
        self._currency = currency
        self._debt = debt
        self.setWindowTitle(tr("Edit Debt") if debt else tr("Add Debt"))
        self.setMinimumWidth(400)
        self._build_ui()
        if debt:
            self._populate(debt)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("e.g. Visa card"))
        form.addRow(tr("Name"), self._name_edit)

        self._balance_spin = QDoubleSpinBox()
        self._balance_spin.setRange(0, 10_000_000)
        self._balance_spin.setDecimals(2)
        self._balance_spin.setPrefix(f"{self._currency} ")
        form.addRow(tr("Balance Owed"), self._balance_spin)

        self._apr_spin = QDoubleSpinBox()
        self._apr_spin.setRange(0, 100)
        self._apr_spin.setDecimals(2)
        self._apr_spin.setSuffix(" %")
        form.addRow(tr("Interest Rate (APR)"), self._apr_spin)

        self._min_spin = QDoubleSpinBox()
        self._min_spin.setRange(0, 1_000_000)
        self._min_spin.setDecimals(2)
        self._min_spin.setPrefix(f"{self._currency} ")
        form.addRow(tr("Minimum Monthly Payment"), self._min_spin)

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

    def _populate(self, debt: dict) -> None:
        self._name_edit.setText(debt["name"])
        self._balance_spin.setValue(debt["balance"])
        self._apr_spin.setValue(debt["apr"])
        self._min_spin.setValue(debt["min_payment"])

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("Validation"), tr("Debt name is required."))
            return
        if self._balance_spin.value() <= 0:
            QMessageBox.warning(self, tr("Validation"), tr("Balance must be greater than zero."))
            return
        try:
            bal = self._balance_spin.value()
            apr = self._apr_spin.value()
            minp = self._min_spin.value()
            if self._debt:
                self._db.update_debt(self._debt["id"], name, bal, apr, minp)
            else:
                self._db.create_debt(self._user_id, name, bal, apr, minp)
        except Exception as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not save debt:\n{err}").format(err=exc))
            return
        self.accept()


class DebtView(QWidget):
    """Debt payoff planner panel."""

    debt_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        head_row = QHBoxLayout()
        title = QLabel(tr("Debt Payoff Planner"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()
        add_btn = QPushButton(tr("+ Add Debt"))
        add_btn.clicked.connect(self._add_debt)
        head_row.addWidget(add_btn)
        layout.addLayout(head_row)

        # Controls: strategy + extra payment
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel(tr("Strategy")))
        self._strategy_combo = QComboBox()
        # userData holds the English strategy key the service expects.
        self._strategy_combo.addItem(tr("Avalanche (highest interest first)"), "avalanche")
        self._strategy_combo.addItem(tr("Snowball (smallest balance first)"), "snowball")
        self._strategy_combo.currentIndexChanged.connect(self.refresh)
        ctrl_row.addWidget(self._strategy_combo)

        ctrl_row.addSpacing(16)
        ctrl_row.addWidget(QLabel(tr("Extra monthly payment")))
        self._extra_spin = QDoubleSpinBox()
        self._extra_spin.setRange(0, 1_000_000)
        self._extra_spin.setDecimals(2)
        self._extra_spin.setPrefix(f"{self._currency} ")
        self._extra_spin.valueChanged.connect(self.refresh)
        ctrl_row.addWidget(self._extra_spin)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Result summary
        self._summary = QLabel()
        self._summary.setObjectName("card")
        self._summary.setWordWrap(True)
        self._summary.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._summary)

        # Debt list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

    def _money(self, value: float) -> str:
        return f"{self._currency} {value:,.0f}"

    def refresh(self) -> None:
        # Clear the debt list.
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        debts = self._db.get_debts(self._user["id"])
        if not debts:
            self._summary.setText(
                tr("No debts tracked. Click '+ Add Debt' to build a payoff plan.")
            )
            empty = QLabel(tr("You're debt-free here — nothing to plan. 🎉"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("muted")
            self._content_layout.addWidget(empty)
            return

        strategy = self._strategy_combo.currentData() or "avalanche"
        extra = self._extra_spin.value()
        result = debt_service.plan(debts, extra, strategy)
        baseline = debt_service.plan(debts, 0.0, strategy)

        self._render_summary(result, baseline)

        # Order the cards the way the plan pays them off, so the list doubles as
        # a payoff schedule. Debts the plan never clears fall to the bottom.
        payoff_month = {p["id"]: p["month"] for p in result["payoff_order"]}
        debts_sorted = sorted(debts, key=lambda d: payoff_month.get(d["id"], 10**9))
        for d in debts_sorted:
            self._content_layout.addWidget(
                self._debt_card(d, payoff_month.get(d["id"]))
            )
        self._content_layout.addStretch()

    def _render_summary(self, result: dict, baseline: dict) -> None:
        total = result["start_balance"]
        if not result["feasible"]:
            self._summary.setText(
                tr("Total owed: {total}").format(total=self._money(total)) + "<br>"
                + "<b>" + tr(
                    "Your monthly payment is too small to clear these debts — "
                    "the balance never reaches zero. Increase the minimums or add "
                    "an extra payment."
                ) + "</b>"
            )
            return

        years, months = divmod(result["months"], 12)
        if years and months:
            span = tr("{y} yr {m} mo").format(y=years, m=months)
        elif years:
            span = tr("{y} yr").format(y=years)
        else:
            span = tr("{m} mo").format(m=months)

        date_str = result["debt_free_date"].strftime("%b %Y") if result["debt_free_date"] else "—"

        lines = [
            tr("Total owed: {total}  •  Monthly payment: {pay}").format(
                total=self._money(total), pay=self._money(result["monthly_payment"])),
            "<b>" + tr("Debt-free in {span} — around {date}").format(span=span, date=date_str) + "</b>",
            tr("Total interest paid: {interest}").format(interest=self._money(result["total_interest"])),
        ]

        # Savings vs paying only the minimums (baseline = no extra payment).
        if baseline["feasible"]:
            saved_i = round(baseline["total_interest"] - result["total_interest"], 2)
            saved_m = baseline["months"] - result["months"]
            if saved_i > 0.5 or saved_m > 0:
                lines.append(
                    "<span style='color:#10B981'>" + tr(
                        "vs minimums only: save {interest} and {months} months"
                    ).format(interest=self._money(saved_i), months=saved_m) + "</span>"
                )
        self._summary.setText("<br>".join(lines))

    def _debt_card(self, debt: dict, month: Optional[int]) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(4)

        top = QHBoxLayout()
        name = QLabel(debt["name"])
        name.setFont(ui_font(12, QFont.Weight.Bold))
        top.addWidget(name)
        top.addStretch()
        top.addWidget(QLabel(self._money(debt["balance"])))

        edit_btn = QPushButton(tr("Edit"))
        edit_btn.setObjectName("secondary")
        edit_btn.clicked.connect(lambda _, d=debt: self._edit_debt(d))
        top.addWidget(edit_btn)
        del_btn = QPushButton(tr("Delete"))
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(lambda _, d=debt: self._delete_debt(d))
        top.addWidget(del_btn)
        v.addLayout(top)

        detail = tr("{apr}% APR  •  min {min}/mo").format(
            apr=f"{debt['apr']:.2f}", min=self._money(debt["min_payment"]))
        if month:
            detail += "  •  " + tr("paid off in month {n}").format(n=month)
        info = QLabel(detail)
        info.setObjectName("muted")
        info.setStyleSheet("font-size: 11px;")
        v.addWidget(info)
        return card

    def _add_debt(self) -> None:
        dlg = DebtDialog(self._db, self._user["id"], self._currency, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.debt_changed.emit()

    def _edit_debt(self, debt: dict) -> None:
        dlg = DebtDialog(self._db, self._user["id"], self._currency, debt=debt, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.debt_changed.emit()

    def _delete_debt(self, debt: dict) -> None:
        reply = QMessageBox.question(
            self, tr("Delete Debt"),
            tr("Delete debt '{name}'?").format(name=debt["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_debt(debt["id"])
            self.refresh()
            self.debt_changed.emit()
