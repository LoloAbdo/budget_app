"""
views/transactions_view.py
Full CRUD for transactions: table list, filter toolbar, add/edit dialog.
"""

from datetime import date
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QTextEdit,
    QFormLayout, QMessageBox, QFrame, QSizePolicy, QFileDialog,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from database import DatabaseManager
from services.import_export_service import ImportExportService
from views.i18n import tr
from views.sortable import SortableItem, SORT_ROLE, enable_sorting
from views.widgets import add_table_shortcuts, make_empty_state


# ── Transaction dialog ─────────────────────────────────────────────────────────

class TransactionDialog(QDialog):
    """Add / Edit transaction modal."""

    def __init__(
        self,
        db: DatabaseManager,
        user_id: int,
        transaction: Optional[dict] = None,
        prefill: Optional[dict] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._user_id = user_id
        self._txn = transaction
        # Build a category-id → type lookup used to auto-switch the toggle
        self._cat_types: dict[int, str] = {
            c["id"]: c["type"] for c in self._db.get_categories()
        }
        self.setWindowTitle(tr("Edit Transaction") if transaction else tr("Add Transaction"))
        self.setMinimumWidth(420)
        self._build_ui()
        # ``transaction`` = edit an existing row; ``prefill`` = pre-populate the
        # fields but still save as a brand-new row (used by Duplicate).
        if transaction:
            self._populate(transaction)
        elif prefill:
            self._populate(prefill)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._date_edit = QDateEdit(QDate.currentDate())
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow(tr("Date"), self._date_edit)

        self._desc_edit = QLineEdit()
        self._desc_edit.setPlaceholderText(tr("e.g. Grocery run"))
        form.addRow(tr("Description"), self._desc_edit)

        # ── Type toggle: Expense (default) / Income ──────────────────────────
        type_row = QHBoxLayout()
        type_row.setSpacing(0)
        self._expense_btn = QPushButton(tr("Expense"))
        self._expense_btn.setCheckable(True)
        self._expense_btn.setChecked(True)
        self._income_btn  = QPushButton(tr("Income"))
        self._income_btn.setCheckable(True)
        self._expense_btn.setObjectName("toggleLeft")
        self._income_btn.setObjectName("toggleRight")
        self._expense_btn.clicked.connect(lambda: self._set_type("Expense"))
        self._income_btn.clicked.connect(lambda: self._set_type("Income"))
        type_row.addWidget(self._expense_btn)
        type_row.addWidget(self._income_btn)
        type_row.addStretch()
        form.addRow(tr("Type"), type_row)

        # Amount — always positive; sign derived from type toggle
        self._amount_edit = QDoubleSpinBox()
        self._amount_edit.setRange(0, 1_000_000)
        self._amount_edit.setDecimals(2)
        self._amount_edit.setPrefix("$ ")
        form.addRow(tr("Amount"), self._amount_edit)

        self._account_combo = QComboBox()
        accounts = self._db.get_accounts(self._user_id)
        for a in accounts:
            self._account_combo.addItem(a["account_name"], a["id"])
        form.addRow(tr("Account"), self._account_combo)

        self._category_combo = QComboBox()
        self._category_combo.addItem(tr("— None —"), None)
        for c in self._db.get_categories():
            self._category_combo.addItem(c["name"], c["id"])
        # Auto-switch toggle when category changes
        self._category_combo.currentIndexChanged.connect(self._on_category_changed)
        form.addRow(tr("Category"), self._category_combo)

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText(tr("Optional notes…"))
        self._notes_edit.setMaximumHeight(80)
        form.addRow(tr("Notes"), self._notes_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
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

    def _set_type(self, txn_type: str) -> None:
        """Switch the Expense/Income toggle without triggering recursion."""
        self._expense_btn.setChecked(txn_type == "Expense")
        self._income_btn.setChecked(txn_type == "Income")

    def _on_category_changed(self, _index: int) -> None:
        """Auto-switch the type toggle to match the selected category."""
        cat_id = self._category_combo.currentData()
        if cat_id is not None and cat_id in self._cat_types:
            self._set_type(self._cat_types[cat_id])

    def _signed_amount(self) -> float:
        """Return the amount with correct sign: negative for Expense."""
        raw = self._amount_edit.value()
        return -raw if self._expense_btn.isChecked() else raw

    def _populate(self, txn: dict) -> None:
        self._date_edit.setDate(QDate.fromString(txn["date"], "yyyy-MM-dd"))
        self._desc_edit.setText(txn["description"])
        # Derive type from stored sign; show absolute value in the spin
        stored = txn["amount"]
        if stored < 0:
            self._set_type("Expense")
            self._amount_edit.setValue(abs(stored))
        else:
            self._set_type("Income")
            self._amount_edit.setValue(stored)
        self._notes_edit.setPlainText(txn.get("notes") or "")

        for i in range(self._account_combo.count()):
            if self._account_combo.itemData(i) == txn["account_id"]:
                self._account_combo.setCurrentIndex(i)
                break
        # Set category without triggering auto-switch (sign already set above)
        self._category_combo.blockSignals(True)
        for i in range(self._category_combo.count()):
            if self._category_combo.itemData(i) == txn.get("category_id"):
                self._category_combo.setCurrentIndex(i)
                break
        self._category_combo.blockSignals(False)

    def _save(self) -> None:
        desc = self._desc_edit.text().strip()
        if not desc:
            QMessageBox.warning(self, tr("Validation"), tr("Description is required."))
            return
        if self._amount_edit.value() == 0:
            QMessageBox.warning(self, tr("Validation"), tr("Amount must be greater than zero."))
            return

        amount  = self._signed_amount()   # negative for expense, positive for income
        date_s  = self._date_edit.date().toString("yyyy-MM-dd")
        acct_id = self._account_combo.currentData()
        cat_id  = self._category_combo.currentData()
        notes   = self._notes_edit.toPlainText().strip()

        if not acct_id:
            QMessageBox.warning(self, tr("Validation"), tr("Please select an account."))
            return
        try:
            if self._txn:
                self._db.update_transaction(
                    self._txn["id"], acct_id, cat_id, date_s, desc, amount, notes
                )
            else:
                self._db.create_transaction(acct_id, cat_id, date_s, desc, amount, notes)
        except Exception as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not save transaction:\n{err}").format(err=exc))
            return
        self.accept()



# ── Transfer dialog ────────────────────────────────────────────────────────────

class TransferDialog(QDialog):
    """Move money between two accounts."""

    def __init__(self, db: DatabaseManager, user_id: int, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user_id = user_id
        self.setWindowTitle(tr("Transfer Between Accounts"))
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        accounts = self._db.get_accounts(self._user_id)

        self._from_combo = QComboBox()
        for a in accounts:
            self._from_combo.addItem(
                f"{a['account_name']}  ({a['current_balance']:,.2f})", a["id"]
            )
        form.addRow(tr("From Account"), self._from_combo)

        self._to_combo = QComboBox()
        for a in accounts:
            self._to_combo.addItem(
                f"{a['account_name']}  ({a['current_balance']:,.2f})", a["id"]
            )
        # Default destination to second account if available
        if self._to_combo.count() > 1:
            self._to_combo.setCurrentIndex(1)
        form.addRow(tr("To Account"), self._to_combo)

        self._amount_spin = QDoubleSpinBox()
        self._amount_spin.setRange(0.01, 1_000_000)
        self._amount_spin.setDecimals(2)
        self._amount_spin.setPrefix("$ ")
        form.addRow(tr("Amount"), self._amount_spin)

        self._date_edit = QDateEdit(QDate.currentDate())
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow(tr("Date"), self._date_edit)

        self._desc_edit = QLineEdit(tr("Transfer"))
        form.addRow(tr("Description"), self._desc_edit)

        self._notes_edit = QLineEdit()
        self._notes_edit.setPlaceholderText(tr("Optional notes…"))
        form.addRow(tr("Notes"), self._notes_edit)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(tr("Transfer"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self) -> None:
        from_id = self._from_combo.currentData()
        to_id   = self._to_combo.currentData()
        if from_id == to_id:
            QMessageBox.warning(self, tr("Validation"), tr("Source and destination must be different accounts."))
            return
        amount = self._amount_spin.value()
        if amount <= 0:
            QMessageBox.warning(self, tr("Validation"), tr("Amount must be greater than zero."))
            return
        desc  = self._desc_edit.text().strip() or tr("Transfer")
        date  = self._date_edit.date().toString("yyyy-MM-dd")
        notes = self._notes_edit.text().strip()
        try:
            self._db.create_transfer(from_id, to_id, amount, date, desc, notes)
        except Exception as exc:
            QMessageBox.critical(self, tr("Error"), tr("Could not create transfer:\n{err}").format(err=exc))
            return
        self.accept()


# ── Transactions view ──────────────────────────────────────────────────────────

class TransactionsView(QWidget):
    """Full transaction management panel."""

    transaction_changed = pyqtSignal()  # triggers dashboard refresh

    # English keys; localized at build time via tr()
    COLS = ["Date", "Description", "Category", "Account", "Amount", "Notes"]

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
        title = QLabel(tr("Transactions"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        transfer_btn = QPushButton(tr("⇄ Transfer"))
        transfer_btn.setObjectName("secondary")
        transfer_btn.clicked.connect(self._add_transfer)
        head_row.addWidget(transfer_btn)

        add_btn = QPushButton(tr("+ Add Transaction"))
        add_btn.clicked.connect(self._add_transaction)
        head_row.addWidget(add_btn)
        layout.addLayout(head_row)

        # ── Filter bar ────────────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setObjectName("card")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(tr("🔍 Search…"))
        self._search_edit.textChanged.connect(self.refresh)
        filter_layout.addWidget(self._search_edit, 2)

        self._cat_filter = QComboBox()
        self._cat_filter.addItem(tr("All Categories"), None)
        for c in self._db.get_categories():
            self._cat_filter.addItem(c["name"], c["id"])
        self._cat_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self._cat_filter, 1)

        self._acct_filter = QComboBox()
        self._acct_filter.addItem(tr("All Accounts"), None)
        for a in self._db.get_accounts(self._user["id"]):
            self._acct_filter.addItem(a["account_name"], a["id"])
        self._acct_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self._acct_filter, 1)

        self._start_date = QDateEdit(QDate.currentDate().addDays(-30))
        self._start_date.setCalendarPopup(True)
        self._start_date.setDisplayFormat("yyyy-MM-dd")
        self._start_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self._start_date)

        self._end_date = QDateEdit(QDate.currentDate())
        self._end_date.setCalendarPopup(True)
        self._end_date.setDisplayFormat("yyyy-MM-dd")
        self._end_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self._end_date)

        clear_btn = QPushButton(tr("Clear"))
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_btn)

        layout.addWidget(filter_frame)

        # ── Table ─────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels([tr(c) for c in self.COLS])
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(False)
        hdr.setMinimumSectionSize(60)
        self._table.setColumnWidth(0, 100)   # Date
        self._table.setColumnWidth(1, 220)   # Description
        self._table.setColumnWidth(2, 130)   # Category
        self._table.setColumnWidth(3, 150)   # Account
        self._table.setColumnWidth(4, 100)   # Amount
        self._table.setColumnWidth(5, 150)   # Notes
        self._table.doubleClicked.connect(self._edit_selected)
        # Newest-first by default; every column is click-sortable.
        enable_sorting(self._table, 0, Qt.SortOrder.DescendingOrder)
        add_table_shortcuts(self._table, on_delete=self._delete_selected, on_edit=self._edit_selected)
        layout.addWidget(self._table)

        self._empty_lbl = make_empty_state("")
        layout.addWidget(self._empty_lbl)

        # Action row
        btn_row = QHBoxLayout()
        edit_btn = QPushButton(tr("✏ Edit"))
        edit_btn.setObjectName("secondary")
        edit_btn.clicked.connect(self._edit_selected)
        edit_btn.setToolTip(tr("Edit selected (Enter)"))
        btn_row.addWidget(edit_btn)

        dup_btn = QPushButton(tr("⧉ Duplicate"))
        dup_btn.setObjectName("secondary")
        dup_btn.clicked.connect(self._duplicate_selected)
        dup_btn.setToolTip(tr("Create a copy of the selected transaction"))
        btn_row.addWidget(dup_btn)

        del_btn = QPushButton(tr("🗑 Delete"))
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_selected)
        del_btn.setToolTip(tr("Delete selected (Del)"))
        btn_row.addWidget(del_btn)

        export_btn = QPushButton(tr("⤓ Export"))
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export)
        export_btn.setToolTip(tr("Export the current filtered list to CSV or Excel"))
        btn_row.addWidget(export_btn)

        btn_row.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("muted")
        btn_row.addWidget(self._count_lbl)

        layout.addLayout(btn_row)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _current_filters(self) -> dict:
        """The active filter toolbar state, as kwargs for get_transactions()."""
        return {
            "keyword":     self._search_edit.text().strip() or None,
            "category_id": self._cat_filter.currentData(),
            "account_id":  self._acct_filter.currentData(),
            "start_date":  self._start_date.date().toString("yyyy-MM-dd"),
            "end_date":    self._end_date.date().toString("yyyy-MM-dd"),
        }

    def refresh(self) -> None:
        filters = self._current_filters()
        rows = self._db.get_transactions(self._user["id"], **filters)
        self._rows = rows
        # Disable sorting while we rebuild rows, then re-enable so the table
        # re-sorts once by the user's current column choice.
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))

        for r_idx, txn in enumerate(rows):
            is_transfer = txn.get("transfer_id") is not None
            items = [
                txn["date"],
                txn["description"],
                tr("[Transfer]") if is_transfer else (txn.get("category_name") or "—"),
                txn.get("account_name") or "—",
                f"{self._currency} {txn['amount']:,.2f}",
                txn.get("notes") or "",
            ]
            for c_idx, text in enumerate(items):
                item = SortableItem(text)
                item.setData(Qt.ItemDataRole.UserRole, txn["id"])
                if c_idx == 4:
                    item.setData(SORT_ROLE, txn["amount"])   # sort by number, not "$1,234.56"
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    if txn.get("transfer_id") is not None:
                        item.setForeground(QColor("#8B5CF6"))  # purple for transfers
                    elif txn.get("category_type") == "Income":
                        item.setForeground(QColor("#10B981"))
                    else:
                        item.setForeground(QColor("#EF4444"))
                # Mark transfer rows with a purple tint on description
                if c_idx == 1 and txn.get("transfer_id") is not None:
                    item.setForeground(QColor("#8B5CF6"))
                self._table.setItem(r_idx, c_idx, item)

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSortingEnabled(True)
        self._count_lbl.setText(tr("{n} transactions").format(n=len(rows)))

        # Empty state: distinguish "nothing yet" from "filters hid everything".
        filtered = bool(filters["keyword"] or filters["category_id"] or filters["account_id"])
        self._empty_lbl.setText(
            tr("No transactions match your filters.") if filtered
            else tr("No transactions yet. Click '+ Add Transaction' to start.")
        )
        self._empty_lbl.setVisible(not rows)
        self._table.setVisible(bool(rows))

    def _clear_filters(self) -> None:
        self._search_edit.clear()
        self._cat_filter.setCurrentIndex(0)
        self._acct_filter.setCurrentIndex(0)
        self._start_date.setDate(QDate.currentDate().addDays(-30))
        self._end_date.setDate(QDate.currentDate())

    # ── Actions ───────────────────────────────────────────────────────────────

    def _export(self) -> None:
        """Export the currently filtered transactions to CSV or Excel."""
        if not self._rows:
            QMessageBox.information(
                self, tr("Export"), tr("There are no transactions to export.")
            )
            return

        default_name = f"transactions_{QDate.currentDate().toString('yyyy-MM-dd')}.csv"
        path, selected = QFileDialog.getSaveFileName(
            self, tr("Export Transactions"), default_name,
            "CSV Files (*.csv);;Excel Files (*.xlsx)",
        )
        if not path:
            return

        # Pick the format from the chosen filter, falling back to the extension.
        is_excel = "xlsx" in selected.lower() or path.lower().endswith(".xlsx")
        ie = ImportExportService(self._db)
        try:
            if is_excel:
                if not path.lower().endswith(".xlsx"):
                    path += ".xlsx"
                count = ie.export_excel(self._user["id"], path, **self._current_filters())
            else:
                if not path.lower().endswith(".csv"):
                    path += ".csv"
                count = ie.export_csv(self._user["id"], path, **self._current_filters())
        except Exception as exc:   # surface IO/permission errors instead of crashing
            QMessageBox.critical(self, tr("Export Failed"), str(exc))
            return

        QMessageBox.information(
            self, tr("Export"),
            tr("Exported {n} transactions to:\n{path}").format(n=count, path=path),
        )

    def _add_transfer(self) -> None:
        dlg = TransferDialog(self._db, self._user["id"], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.transaction_changed.emit()

    def _add_transaction(self) -> None:
        dlg = TransactionDialog(self._db, self._user["id"], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.transaction_changed.emit()

    def _edit_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        txn_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        txn = self._db.get_transaction(txn_id)
        if txn:
            if txn.get("transfer_id") is not None:
                QMessageBox.information(
                    self, tr("Transfer"),
                    tr("Transfers cannot be edited.\nDelete this transfer and create a new one if needed.")
                )
                return
            dlg = TransactionDialog(self._db, self._user["id"], transaction=txn, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
                self._table.selectRow(row)
                self.transaction_changed.emit()

    def _duplicate_selected(self) -> None:
        """Open the Add dialog pre-filled from the selected transaction."""
        row = self._table.currentRow()
        if row < 0:
            return
        txn_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        txn = self._db.get_transaction(txn_id)
        if not txn:
            return
        if txn.get("transfer_id") is not None:
            QMessageBox.information(
                self, tr("Transfer"),
                tr("Transfers cannot be duplicated.\nUse ⇄ Transfer to create a new one."),
            )
            return
        dlg = TransactionDialog(self._db, self._user["id"], prefill=txn, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.transaction_changed.emit()

    def _delete_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        txn_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        desc   = self._table.item(row, 1).text()
        # Check if it's a transfer so we can warn about both legs
        txn_check = self._db.get_transaction(txn_id)
        is_transfer = txn_check and txn_check.get("transfer_id") is not None
        msg = (
            tr("Delete transfer '{desc}'?\nBoth legs of the transfer will be removed.").format(desc=desc)
            if is_transfer else
            tr("Delete '{desc}'?\nThis cannot be undone.").format(desc=desc)
        )
        reply  = QMessageBox.question(
            self, tr("Delete Transfer") if is_transfer else tr("Delete Transaction"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            txn = self._db.get_transaction(txn_id)
            try:
                if txn and txn.get("transfer_id") is not None:
                    self._db.delete_transfer(txn_id)
                else:
                    self._db.delete_transaction(txn_id)
            except Exception as exc:
                QMessageBox.critical(self, tr("Error"), tr("Could not delete:\n{err}").format(err=exc))
                return
            self.refresh()
            new_row = min(row, self._table.rowCount() - 1)
            if new_row >= 0:
                self._table.selectRow(new_row)
            self.transaction_changed.emit()