"""
views/recurring_view.py
Recurring transactions management panel.
Supports both regular recurring transactions and recurring transfers.
"""

from datetime import date
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox,
    QMessageBox, QStackedWidget, QFrame,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

from database import DatabaseManager
from views.i18n import tr
from views.sortable import SortableItem, SORT_ROLE, enable_sorting
from views.widgets import add_table_shortcuts

FREQUENCIES = ["Weekly", "Bi-weekly", "Monthly", "Quarterly", "Yearly"]


class RecurringDialog(QDialog):
    """Add or edit a recurring transaction or recurring transfer."""

    def __init__(self, db: DatabaseManager, user_id: int, rec: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._user_id = user_id
        self._rec = rec
        self.setWindowTitle(tr("Edit Recurring") if rec else tr("Add Recurring"))
        self.setMinimumWidth(420)
        self._build_ui()
        if rec:
            self._populate(rec)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        # Name
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("e.g. Weekly savings transfer"))
        form.addRow(tr("Name"), self._name_edit)

        # ── Type toggle: Transaction / Transfer ───────────────────────────────
        type_row = QHBoxLayout()
        type_row.setSpacing(0)
        self._txn_btn = QPushButton(tr("Transaction"))
        self._txn_btn.setCheckable(True)
        self._txn_btn.setChecked(True)
        self._txn_btn.setObjectName("toggleLeft")
        self._transfer_btn = QPushButton(tr("Transfer"))
        self._transfer_btn.setCheckable(True)
        self._transfer_btn.setObjectName("toggleRight")
        self._txn_btn.clicked.connect(lambda: self._set_mode("transaction"))
        self._transfer_btn.clicked.connect(lambda: self._set_mode("transfer"))
        type_row.addWidget(self._txn_btn)
        type_row.addWidget(self._transfer_btn)
        type_row.addStretch()
        form.addRow(tr("Type"), type_row)

        # Amount (always positive — sign handled by mode)
        self._amount_spin = QDoubleSpinBox()
        self._amount_spin.setRange(0.01, 1_000_000)
        self._amount_spin.setDecimals(2)
        self._amount_spin.setPrefix("$ ")
        form.addRow(tr("Amount"), self._amount_spin)

        # Frequency — display localized label, store the English value
        self._freq_combo = QComboBox()
        for f in FREQUENCIES:
            self._freq_combo.addItem(tr(f), f)
        form.addRow(tr("Frequency"), self._freq_combo)

        # Next due date
        self._next_date = QDateEdit(QDate.currentDate())
        self._next_date.setCalendarPopup(True)
        self._next_date.setDisplayFormat("yyyy-MM-dd")
        form.addRow(tr("Next Due Date"), self._next_date)

        # From / source account (used by both modes)
        self._acct_combo = QComboBox()
        accounts = self._db.get_accounts(self._user_id)
        for a in accounts:
            self._acct_combo.addItem(a["account_name"], a["id"])
        form.addRow(tr("From Account"), self._acct_combo)

        # ── Stacked: Transaction fields / Transfer fields ─────────────────────
        self._detail_stack = QStackedWidget()

        # Page 0 — Transaction: expense/income toggle + category
        txn_widget = QWidget()
        txn_layout = QFormLayout(txn_widget)
        txn_layout.setContentsMargins(0, 0, 0, 0)
        txn_layout.setSpacing(10)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(0)
        self._expense_btn = QPushButton(tr("Expense"))
        self._expense_btn.setCheckable(True)
        self._expense_btn.setChecked(True)
        self._expense_btn.setObjectName("toggleLeft")
        self._income_btn = QPushButton(tr("Income"))
        self._income_btn.setCheckable(True)
        self._income_btn.setObjectName("toggleRight")
        self._expense_btn.clicked.connect(lambda: self._set_direction("Expense"))
        self._income_btn.clicked.connect(lambda: self._set_direction("Income"))
        dir_row.addWidget(self._expense_btn)
        dir_row.addWidget(self._income_btn)
        dir_row.addStretch()
        txn_layout.addRow(tr("Direction"), dir_row)

        self._cat_combo = QComboBox()
        self._cat_combo.addItem(tr("— None —"), None)
        for c in self._db.get_categories():
            self._cat_combo.addItem(c["name"], c["id"])
        txn_layout.addRow(tr("Category"), self._cat_combo)

        self._detail_stack.addWidget(txn_widget)

        # Page 1 — Transfer: destination account
        xfer_widget = QWidget()
        xfer_layout = QFormLayout(xfer_widget)
        xfer_layout.setContentsMargins(0, 0, 0, 0)
        xfer_layout.setSpacing(10)

        self._to_acct_combo = QComboBox()
        for a in accounts:
            self._to_acct_combo.addItem(a["account_name"], a["id"])
        if self._to_acct_combo.count() > 1:
            self._to_acct_combo.setCurrentIndex(1)
        xfer_layout.addRow(tr("To Account"), self._to_acct_combo)

        self._detail_stack.addWidget(xfer_widget)
        form.addRow("", self._detail_stack)

        layout.addLayout(form)

        # Buttons
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

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        is_transfer = mode == "transfer"
        self._txn_btn.setChecked(not is_transfer)
        self._transfer_btn.setChecked(is_transfer)
        self._detail_stack.setCurrentIndex(1 if is_transfer else 0)

    def _set_direction(self, direction: str) -> None:
        self._expense_btn.setChecked(direction == "Expense")
        self._income_btn.setChecked(direction == "Income")

    def _is_transfer(self) -> bool:
        return self._transfer_btn.isChecked()

    def _populate(self, r: dict) -> None:
        self._name_edit.setText(r["name"])
        self._amount_spin.setValue(abs(r["amount"]))
        freq_idx = self._freq_combo.findData(r["frequency"])
        if freq_idx >= 0:
            self._freq_combo.setCurrentIndex(freq_idx)
        self._next_date.setDate(QDate.fromString(r["next_due_date"], "yyyy-MM-dd"))

        # Select from account
        for i in range(self._acct_combo.count()):
            if self._acct_combo.itemData(i) == r.get("account_id"):
                self._acct_combo.setCurrentIndex(i)
                break

        if r.get("to_account_id"):
            # Recurring transfer
            self._set_mode("transfer")
            for i in range(self._to_acct_combo.count()):
                if self._to_acct_combo.itemData(i) == r["to_account_id"]:
                    self._to_acct_combo.setCurrentIndex(i)
                    break
        else:
            # Regular transaction
            self._set_mode("transaction")
            self._set_direction("Expense" if r["amount"] < 0 else "Income")
            for i in range(self._cat_combo.count()):
                if self._cat_combo.itemData(i) == r.get("category_id"):
                    self._cat_combo.setCurrentIndex(i)
                    break

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("Validation"), tr("Name is required."))
            return
        if self._amount_spin.value() == 0:
            QMessageBox.warning(self, tr("Validation"), tr("Amount must be greater than zero."))
            return

        freq     = self._freq_combo.currentData()
        next_due = self._next_date.date().toString("yyyy-MM-dd")
        acct_id  = self._acct_combo.currentData()

        if self._is_transfer():
            to_acct_id = self._to_acct_combo.currentData()
            if not acct_id or not to_acct_id:
                QMessageBox.warning(self, tr("Validation"), tr("Both accounts are required for a transfer."))
                return
            if acct_id == to_acct_id:
                QMessageBox.warning(self, tr("Validation"), tr("Source and destination must be different accounts."))
                return
            amount     = self._amount_spin.value()   # always positive for transfers
            cat_id     = None
        else:
            to_acct_id = None
            raw        = self._amount_spin.value()
            amount     = -raw if self._expense_btn.isChecked() else raw
            cat_id     = self._cat_combo.currentData()

        try:
            if self._rec:
                self._db.update_recurring(
                    self._rec["id"], name, amount, freq, next_due,
                    cat_id, acct_id, to_acct_id
                )
            else:
                self._db.create_recurring(
                    self._user_id, name, amount, freq, next_due,
                    cat_id, acct_id, to_acct_id
                )
        except Exception as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not save recurring:\n{err}").format(err=exc))
            return
        self.accept()


class RecurringView(QWidget):
    # English keys; localized at build time via tr()
    COLS = ["Name", "Amount", "Frequency", "Next Due", "Type", "From Account", "To / Category"]

    def __init__(self, db: DatabaseManager, user: dict, parent=None):
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

        head_row = QHBoxLayout()
        title = QLabel(tr("Recurring Transactions"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        add_btn = QPushButton(tr("+ Add Recurring"))
        add_btn.clicked.connect(self._add_recurring)
        head_row.addWidget(add_btn)
        layout.addLayout(head_row)

        # ── Filter bar ──────────────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setObjectName("card")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(tr("🔍 Search…"))
        self._search_edit.textChanged.connect(self.refresh)
        filter_layout.addWidget(self._search_edit, 2)

        self._freq_filter = QComboBox()
        self._freq_filter.addItem(tr("All Frequencies"), None)
        for f in FREQUENCIES:
            self._freq_filter.addItem(tr(f), f)
        self._freq_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self._freq_filter, 1)

        self._type_filter = QComboBox()
        self._type_filter.addItem(tr("All Types"), None)
        for t in ("Income", "Expense", "Transfer"):
            self._type_filter.addItem(tr(t), t)
        self._type_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self._type_filter, 1)

        clear_btn = QPushButton(tr("Clear"))
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_btn)

        layout.addWidget(filter_frame)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels([tr(c) for c in self.COLS])
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setMinimumSectionSize(60)
        self._table.setColumnWidth(1, 110)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 90)
        self._table.setColumnWidth(5, 140)
        self._table.setColumnWidth(6, 140)
        self._table.doubleClicked.connect(self._edit_selected)
        enable_sorting(self._table, 0, Qt.SortOrder.AscendingOrder)
        add_table_shortcuts(self._table, on_delete=self._delete_selected, on_edit=self._edit_selected)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton(tr("✏ Edit"))
        edit_btn.setObjectName("secondary")
        edit_btn.clicked.connect(self._edit_selected)
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton(tr("🗑 Delete"))
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    @staticmethod
    def _rec_type(rec: dict) -> str:
        """Return the English type key for a recurring row: Transfer/Income/Expense."""
        if rec.get("to_account_id"):
            return "Transfer"
        return "Income" if rec["amount"] > 0 else "Expense"

    def _apply_filters(self, recurrings: list[dict]) -> list[dict]:
        """Client-side name search + frequency + type filters."""
        keyword   = self._search_edit.text().strip().lower()
        freq_data = self._freq_filter.currentData()
        type_data = self._type_filter.currentData()
        result = []
        for rec in recurrings:
            if keyword and keyword not in rec["name"].lower():
                continue
            if freq_data and rec["frequency"] != freq_data:
                continue
            if type_data and self._rec_type(rec) != type_data:
                continue
            result.append(rec)
        return result

    def _clear_filters(self) -> None:
        self._search_edit.clear()
        self._freq_filter.setCurrentIndex(0)
        self._type_filter.setCurrentIndex(0)

    def refresh(self) -> None:
        recurrings = self._apply_filters(self._db.get_recurring(self._user["id"]))
        self._table.blockSignals(True)
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(recurrings))
        today = date.today().isoformat()

        for r, rec in enumerate(recurrings):
            due         = rec["next_due_date"]
            is_transfer = bool(rec.get("to_account_id"))
            rec_type    = tr(self._rec_type(rec))
            last_col    = rec.get("to_account_name") or "—" if is_transfer else (rec.get("category_name") or "—")

            items = [
                rec["name"],
                f"{self._currency} {abs(rec['amount']):,.2f}",
                tr(rec["frequency"]),
                due,
                rec_type,
                rec.get("account_name") or "—",
                last_col,
            ]
            for c, text in enumerate(items):
                item = SortableItem(text)
                item.setData(Qt.ItemDataRole.UserRole, rec["id"])
                if c == 1:
                    item.setData(SORT_ROLE, abs(rec["amount"]))   # sort Amount numerically
                # Overdue: red on date column
                if c == 3 and due <= today:
                    item.setForeground(QColor("#EF4444"))
                # Transfers: purple tint on type column
                elif c == 4 and is_transfer:
                    item.setForeground(QColor("#8B5CF6"))
                self._table.setItem(r, c, item)

        self._table.blockSignals(False)
        self._table.setSortingEnabled(True)
        self._table.resizeColumnToContents(1)
        self._table.resizeColumnToContents(2)
        self._table.resizeColumnToContents(3)
        self._table.resizeColumnToContents(4)

    def _add_recurring(self) -> None:
        dlg = RecurringDialog(self._db, self._user["id"], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        rec_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        recs   = self._db.get_recurring(self._user["id"])
        rec    = next((r for r in recs if r["id"] == rec_id), None)
        if rec:
            dlg = RecurringDialog(self._db, self._user["id"], rec=rec, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
                self._table.selectRow(row)

    def _delete_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        rec_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name   = self._table.item(row, 0).text()
        reply  = QMessageBox.question(
            self, tr("Delete Recurring"),
            tr("Delete recurring '{name}'?\nThis will not delete transactions already posted.").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_recurring(rec_id)
            self.refresh()
            new_row = min(row, self._table.rowCount() - 1)
            if new_row >= 0:
                self._table.selectRow(new_row)
