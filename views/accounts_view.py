"""
views/accounts_view.py
Account management panel.
"""

from typing import Optional
from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QMessageBox,
    QFrame, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from database import DatabaseManager
from services.fx_service import CURRENCIES
from views.i18n import tr
from views.sortable import SortableItem, enable_sorting
from views.toast import show_toast
from views.widgets import add_table_shortcuts, make_empty_state, ColumnWidths

ACCOUNT_TYPES = ["Checking", "Savings", "Credit Card", "Cash"]
ACCOUNT_NAME_MAX = 50   # enforced in dialog; no hard DB limit


class AccountDialog(QDialog):
    def __init__(self, db: DatabaseManager, user_id: int, account: Optional[dict] = None,
                 currency: str = "", parent=None):
        super().__init__(parent)
        self._db = db
        self._user_id = user_id
        self._account = account
        self._currency = currency
        self._orig_balance = account["current_balance"] if account else 0.0
        self.setWindowTitle(tr("Edit Account") if account else tr("Add Account"))
        self.setMinimumWidth(360)
        self._build_ui()
        if account:
            self._populate(account)
        self._update_interest_ui()
        self._update_currency_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("e.g. Main Checking"))
        self._name_edit.setMaxLength(ACCOUNT_NAME_MAX)
        form.addRow(tr("Account Name"), self._name_edit)

        self._type_combo = QComboBox()
        # Display localized label, store the English value used in the DB
        for t in ACCOUNT_TYPES:
            self._type_combo.addItem(tr(t), t)
        form.addRow(tr("Account Type"), self._type_combo)

        # Account currency — defaults to the user's home currency. Amounts in
        # this account are kept in this currency; app-wide totals convert.
        self._currency_combo = QComboBox()
        currencies = list(CURRENCIES)
        if self._currency and self._currency not in currencies:
            currencies.insert(0, self._currency)
        self._currency_combo.addItems(currencies)
        if self._currency in currencies:
            self._currency_combo.setCurrentText(self._currency)
        self._currency_combo.currentTextChanged.connect(self._update_currency_ui)
        form.addRow(tr("Currency"), self._currency_combo)

        self._currency_hint = QLabel("")
        self._currency_hint.setObjectName("muted")
        self._currency_hint.setWordWrap(True)
        form.addRow("", self._currency_hint)

        self._balance_spin = QDoubleSpinBox()
        self._balance_spin.setRange(-1_000_000, 1_000_000)
        self._balance_spin.setDecimals(2)
        self._balance_spin.setPrefix("$ ")
        form.addRow(tr("Current Balance"), self._balance_spin)

        # Character counter shown below the name field
        self._char_lbl = QLabel(f"0 / {ACCOUNT_NAME_MAX}")
        self._char_lbl.setObjectName("muted")
        self._name_edit.textChanged.connect(self._update_char_count)
        form.addRow("", self._char_lbl)

        # ── Interest / gain auto-detect (Savings accounts, editing only) ─────────
        self._interest_chk = QCheckBox(tr("Record balance change as interest/gain"))
        self._interest_chk.setChecked(True)
        self._interest_chk.toggled.connect(self._update_interest_ui)
        form.addRow("", self._interest_chk)

        self._interest_hint = QLabel("")
        self._interest_hint.setObjectName("muted")
        self._interest_hint.setWordWrap(True)
        form.addRow("", self._interest_hint)

        # React to changes that affect the interest hint
        self._type_combo.currentIndexChanged.connect(self._update_interest_ui)
        self._balance_spin.valueChanged.connect(self._update_interest_ui)

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

    def _update_char_count(self, text: str) -> None:
        n = len(text)
        self._char_lbl.setText(f"{n} / {ACCOUNT_NAME_MAX}")

    def _update_currency_ui(self, *_args) -> None:
        """Prefix the balance with the chosen currency; warn on relabels."""
        cur = self._currency_combo.currentText()
        self._balance_spin.setPrefix(f"{cur} ")
        if self._account and cur != (self._account.get("currency") or self._currency):
            self._currency_hint.setText(
                tr("The balance and existing transactions are relabeled to {cur} — amounts are not converted.").format(cur=cur)
            )
        else:
            self._currency_hint.setText("")

    def _interest_applicable(self) -> bool:
        """Interest auto-detect applies only when editing a Savings account."""
        return self._account is not None and self._type_combo.currentData() == "Savings"

    def _update_interest_ui(self, *_args) -> None:
        """Show/hide the interest checkbox + live delta hint based on context."""
        applicable = self._interest_applicable()
        self._interest_chk.setVisible(applicable)
        self._interest_hint.setVisible(applicable)
        if not applicable:
            return

        delta = self._balance_spin.value() - self._orig_balance
        cur = self._currency_combo.currentText() + " "
        if abs(delta) < 0.005 or not self._interest_chk.isChecked():
            self._interest_hint.setText("")
        else:
            kind = tr("gain") if delta > 0 else tr("loss")
            self._interest_hint.setText(
                tr("Change of {amount} will be recorded as a {kind}.").format(
                    amount=f"{cur}{abs(delta):,.2f}", kind=kind
                )
            )

    def _populate(self, a: dict) -> None:
        self._name_edit.setText(a["account_name"])
        idx = ACCOUNT_TYPES.index(a["account_type"]) if a["account_type"] in ACCOUNT_TYPES else 0
        self._type_combo.setCurrentIndex(idx)
        self._balance_spin.setValue(a["current_balance"])
        acct_cur = a.get("currency")
        if acct_cur:
            if self._currency_combo.findText(acct_cur) < 0:
                self._currency_combo.insertItem(0, acct_cur)
            self._currency_combo.setCurrentText(acct_cur)

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("Validation"), tr("Account name required."))
            return
        acct_type = self._type_combo.currentData()
        balance   = self._balance_spin.value()
        currency  = self._currency_combo.currentText()
        delta     = balance - self._orig_balance
        record_interest = (
            self._interest_applicable()
            and self._interest_chk.isChecked()
            and abs(delta) >= 0.005
        )
        try:
            if not self._account:
                self._db.create_account(self._user_id, name, acct_type, balance, currency)
            elif record_interest:
                # Keep the original balance, then post the difference as a signed
                # interest/gain entry — which moves the balance to the new value.
                self._db.update_account(self._account["id"], name, acct_type, self._orig_balance, currency)
                self._db.record_interest(self._account["id"], delta, date.today().isoformat())
            else:
                # Plain edit / correction: set the balance directly.
                self._db.update_account(self._account["id"], name, acct_type, balance, currency)
        except Exception as exc:
            QMessageBox.critical(
                self, tr("Database Error"),
                tr("Could not save account:\n{err}").format(err=exc)
            )
            return
        self.accept()


class AccountsView(QWidget):
    accounts_changed = pyqtSignal()

    # English keys; localized at build time via tr()
    COLS = ["Name", "Type", "Currency", "Balance"]

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
        title = QLabel(tr("Accounts"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        add_btn = QPushButton(tr("+ Add Account"))
        add_btn.clicked.connect(self._add_account)
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

        self._type_filter = QComboBox()
        self._type_filter.addItem(tr("All Types"), None)
        for t in ACCOUNT_TYPES:
            self._type_filter.addItem(tr(t), t)
        self._type_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self._type_filter, 1)

        clear_btn = QPushButton(tr("Clear"))
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_btn)

        layout.addWidget(filter_frame)

        self._total_lbl = QLabel()
        self._total_lbl.setObjectName("muted")
        layout.addWidget(self._total_lbl)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels([tr(c) for c in self.COLS])
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        hdr = self._table.horizontalHeader()
        # Set modes ONCE here — never override them inside refresh()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)   # Name always fills spare space
        hdr.setMinimumSectionSize(60)
        self._table.setColumnWidth(1, 130)   # Type  — initial width; user can resize
        self._table.setColumnWidth(2, 90)    # Currency
        self._table.setColumnWidth(3, 150)   # Balance
        self._cols = ColumnWidths(self._table, "accounts", self._user["id"])

        self._table.doubleClicked.connect(self._edit_selected)
        enable_sorting(self._table, 0, Qt.SortOrder.AscendingOrder)
        add_table_shortcuts(self._table, on_delete=self._delete_selected, on_edit=self._edit_selected)
        layout.addWidget(self._table)

        self._empty_lbl = make_empty_state(
            "", icon="🏦",
            action_text=tr("+ Add Account"), on_action=self._add_account,
        )
        layout.addWidget(self._empty_lbl)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton(tr("✏ Edit"))
        edit_btn.setObjectName("secondary")
        edit_btn.clicked.connect(self._edit_selected)
        edit_btn.setToolTip(tr("Edit selected (Enter)"))
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton(tr("🗑 Delete"))
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_selected)
        del_btn.setToolTip(tr("Delete selected (Del)"))
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self) -> None:
        all_accounts = self._db.get_accounts(self._user["id"])
        accounts = self._apply_filters(all_accounts)
        self._accounts = accounts

        # Block signals while rebuilding rows to avoid mid-population repaints
        self._table.blockSignals(True)
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(accounts))

        # Total reflects the visible rows; label notes when a filter is active.
        # Foreign-currency balances convert at the cached rate; the ≈ marks the
        # total as an estimate whenever more than one currency is involved.
        filtered = len(accounts) != len(all_accounts)
        total = sum(
            self._db.convert_amount(
                a["current_balance"], a.get("currency") or self._currency, self._currency
            )
            for a in accounts
        )
        mixed = len({a.get("currency") or self._currency for a in accounts}) > 1
        total_str = f"{'≈ ' if mixed else ''}{self._currency} {total:,.2f}"
        label_key = "Total (filtered): {total}" if filtered else "Total across all accounts: {total}"
        self._total_lbl.setText(tr(label_key).format(total=total_str))

        for r, a in enumerate(accounts):
            bal_color = "#10B981" if a["current_balance"] >= 0 else "#EF4444"
            acct_cur = a.get("currency") or self._currency
            items = [
                (a["account_name"], None, None),
                (tr(a["account_type"]), None, None),
                (acct_cur, None, None),
                (f"{acct_cur} {a['current_balance']:,.2f}", bal_color, a["current_balance"]),
            ]
            for c, (text, color, sort_key) in enumerate(items):
                item = SortableItem(text, sort_key)
                item.setData(Qt.ItemDataRole.UserRole, a["id"])
                if color:
                    item.setForeground(QColor(color))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(r, c, item)

        self._table.blockSignals(False)
        self._table.setSortingEnabled(True)

        # Honor the user's saved widths; otherwise fit the non-stretch columns
        # to content (muted so the auto-fit isn't recorded as a preference).
        if self._cols.has_saved():
            self._cols.restore()
        else:
            with self._cols.muted():
                self._table.resizeColumnToContents(1)   # Type
                self._table.resizeColumnToContents(2)   # Currency
                self._table.resizeColumnToContents(3)   # Balance

        # Empty state: no accounts at all vs. filters hiding them all.
        self._empty_lbl.setText(
            tr("No accounts match your filters.") if all_accounts
            else tr("No accounts yet. Click '+ Add Account' to start.")
        )
        # The CTA only makes sense when there's truly nothing (not filtered out).
        self._empty_lbl.set_action_visible(not all_accounts)
        self._empty_lbl.setVisible(not accounts)
        self._table.setVisible(bool(accounts))

    def _apply_filters(self, accounts: list[dict]) -> list[dict]:
        """Client-side name search + account-type filter."""
        keyword   = self._search_edit.text().strip().lower()
        type_data = self._type_filter.currentData()
        result = []
        for a in accounts:
            if keyword and keyword not in a["account_name"].lower():
                continue
            if type_data and a["account_type"] != type_data:
                continue
            result.append(a)
        return result

    def _clear_filters(self) -> None:
        self._search_edit.clear()
        self._type_filter.setCurrentIndex(0)

    def _add_account(self) -> None:
        dlg = AccountDialog(self._db, self._user["id"], currency=self._currency, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.accounts_changed.emit()
            show_toast(self, tr("Account created"))

    def _edit_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        acct_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        acct = self._db.get_account(acct_id)
        if acct:
            dlg = AccountDialog(self._db, self._user["id"], account=acct, currency=self._currency, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
                # Restore selection so a second edit/delete works without re-clicking
                self._table.selectRow(row)
                self.accounts_changed.emit()
                show_toast(self, tr("Account updated"))

    def _delete_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        acct_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name    = self._table.item(row, 0).text()
        reply   = QMessageBox.question(
            self, tr("Delete Account"),
            tr("Delete account '{name}' and all its transactions?").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_account(acct_id)
            self.refresh()
            # Select the nearest remaining row
            new_row = min(row, self._table.rowCount() - 1)
            if new_row >= 0:
                self._table.selectRow(new_row)
            self.accounts_changed.emit()
            show_toast(self, tr("Account deleted"))
