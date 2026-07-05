"""
views/search_dialog.py
Global transaction search (Ctrl+F): one box that matches description, notes,
or an exact amount across every account and the full date range.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QTableWidget, QHeaderView,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from database import DatabaseManager
from views.i18n import tr
from views.sortable import SortableItem, SORT_ROLE, enable_sorting
from views.widgets import category_dot

_DEBOUNCE_MS = 250
_MAX_RESULTS = 200


class SearchDialog(QDialog):
    """Modeless global search. Double-click a result (or press Enter) to jump
    to the Transactions panel filtered to the current query."""

    # Emitted with the query text when the user picks a result / hits Enter.
    jump_requested = pyqtSignal(str)

    COLS = ["Date", "Description", "Category", "Account", "Amount"]

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self.setWindowTitle(tr("Search transactions"))
        self.resize(680, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText(
            tr("🔍 Search description, notes, or amount — e.g. NETFLIX or 15.99")
        )
        self._query_edit.textChanged.connect(self._schedule_search)
        self._query_edit.returnPressed.connect(self._jump)
        layout.addWidget(self._query_edit)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels([tr(c) for c in self.COLS])
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setMinimumSectionSize(60)
        self._table.doubleClicked.connect(self._jump)
        enable_sorting(self._table, 0, Qt.SortOrder.DescendingOrder)
        layout.addWidget(self._table)

        self._status = QLabel(tr("Type to search across all accounts and dates."))
        self._status.setObjectName("muted")
        layout.addWidget(self._status)

        # Debounce so we don't hit the DB on every keystroke.
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_DEBOUNCE_MS)
        self._timer.timeout.connect(self._run_search)

        self._query_edit.setFocus()

    # ── Search ────────────────────────────────────────────────────────────────

    def _schedule_search(self, _text: str) -> None:
        self._timer.start()

    def _run_search(self) -> None:
        query = self._query_edit.text().strip()
        rows = self._db.search_transactions(self._user["id"], query, limit=_MAX_RESULTS)

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for r_idx, txn in enumerate(rows):
            is_transfer = txn.get("transfer_id") is not None
            items = [
                txn["date"],
                txn["description"],
                tr("[Transfer]") if is_transfer else (txn.get("category_name") or "—"),
                txn.get("account_name") or "—",
                f"{txn.get('account_currency') or ''} {txn['amount']:,.2f}".strip(),
            ]
            for c_idx, text in enumerate(items):
                item = SortableItem(text)
                item.setData(Qt.ItemDataRole.UserRole, txn["id"])
                if c_idx == 2 and not is_transfer and txn.get("category_color"):
                    item.setIcon(category_dot(txn["category_color"]))
                if c_idx == 4:
                    item.setData(SORT_ROLE, txn["amount"])
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                    if is_transfer:
                        item.setForeground(QColor("#8B5CF6"))
                    elif txn.get("category_type") == "Income":
                        item.setForeground(QColor("#10B981"))
                    else:
                        item.setForeground(QColor("#EF4444"))
                self._table.setItem(r_idx, c_idx, item)
        self._table.setSortingEnabled(True)

        if not query:
            self._status.setText(tr("Type to search across all accounts and dates."))
        elif len(rows) >= _MAX_RESULTS:
            self._status.setText(
                tr("Showing the first {n} matches — narrow your search.").format(n=_MAX_RESULTS)
            )
        else:
            self._status.setText(tr("{n} match(es).").format(n=len(rows)))

    # ── Jump to Transactions panel ────────────────────────────────────────────

    def _jump(self) -> None:
        query = self._query_edit.text().strip()
        if not query:
            return
        self.jump_requested.emit(query)
        self.accept()
