"""
views/markets_view.py
Markets watchlist: track live stock & crypto prices (converted to the user's
currency), refreshed on a background thread every 5–15 minutes.

Network fetching runs in a QRunnable on the global thread pool, so the UI never
blocks. Cached last-prices are shown instantly; a fetch failure keeps the cached
values and shows a "couldn't update" notice instead of crashing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QDialog, QFormLayout, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, pyqtSignal

from database import DatabaseManager
from services import market_service as ms
from views.i18n import tr
from views.sortable import SortableItem, SORT_ROLE, enable_sorting
from views.widgets import add_table_shortcuts, hug_button

GREEN = "#10B981"
RED = "#EF4444"
MUTED = "#8A8FA3"


# ── Background worker ────────────────────────────────────────────────────────

class _QuotesSignals(QObject):
    done = pyqtSignal(object)   # dict[(symbol, asset_type)] -> Quote


class _QuotesWorker(QRunnable):
    """Fetches quotes off the UI thread and emits the result."""

    def __init__(self, items: list[dict], currency: str) -> None:
        super().__init__()
        self._items = items
        self._currency = currency
        self.signals = _QuotesSignals()

    def run(self) -> None:
        try:
            result = ms.fetch_quotes(self._items, self._currency)
        except Exception:
            result = {}
        self.signals.done.emit(result)


# ── Add-symbol dialog ────────────────────────────────────────────────────────

class AddWatchDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Add Symbol"))
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self._type_combo = QComboBox()
        self._type_combo.addItem(tr("Stock"), "Stock")
        self._type_combo.addItem(tr("Crypto"), "Crypto")
        form.addRow(tr("Type"), self._type_combo)

        self._symbol_edit = QLineEdit()
        self._symbol_edit.setPlaceholderText("AAPL, TSLA, BTC, ETH…")
        form.addRow(tr("Symbol"), self._symbol_edit)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("Optional"))
        form.addRow(tr("Name (optional)"), self._name_edit)

        layout.addLayout(form)

        hint = QLabel(tr("Stocks use tickers (AAPL). Crypto uses tickers too (BTC).\n"
                         "For non-US stocks add a suffix, e.g. SHOP.TO"))
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        cancel = QPushButton(tr("Cancel"))
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr("Save"))
        save.setDefault(True)
        save.clicked.connect(self._accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _accept(self) -> None:
        if not self._symbol_edit.text().strip():
            QMessageBox.warning(self, tr("Validation"), tr("Symbol is required."))
            return
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return (
            self._symbol_edit.text().strip().upper(),
            self._type_combo.currentData(),
            self._name_edit.text().strip(),
        )


# ── Markets view ─────────────────────────────────────────────────────────────

class MarketsView(QWidget):
    COLS = ["Symbol", "Name", "Type", "Price", "Change %", "Updated"]

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        self._pool = QThreadPool.globalInstance()
        self._fetching = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._fetch)

        self._build_ui()
        self._reload()           # show cached values immediately (no network)
        self._apply_interval()   # default is Manual → timer stays off, no auto-fetch

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel(tr("Markets"))
        title.setObjectName("heading")
        head.addWidget(title)
        head.addStretch()

        head.addWidget(QLabel(tr("Auto-refresh:")))
        self._interval_combo = QComboBox()
        self._interval_combo.addItem(tr("Off (manual)"), 0)   # default — no background calls
        for m in (5, 10, 15):
            self._interval_combo.addItem(tr("{n} min").format(n=m), m)
        self._interval_combo.setCurrentIndex(0)
        self._interval_combo.currentIndexChanged.connect(self._apply_interval)
        head.addWidget(self._interval_combo)

        self._refresh_btn = QPushButton(tr("Refresh"))
        self._refresh_btn.setObjectName("secondary")
        self._refresh_btn.clicked.connect(self._fetch)
        head.addWidget(self._refresh_btn)

        add_btn = QPushButton(tr("+ Add Symbol"))
        add_btn.clicked.connect(self._add_symbol)
        head.addWidget(add_btn)
        layout.addLayout(head)

        self._status = QLabel("")
        self._status.setObjectName("muted")
        layout.addWidget(self._status)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLS))
        self._table.setHorizontalHeaderLabels([tr(c) for c in self.COLS])
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in range(2, len(self.COLS)):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        enable_sorting(self._table, 0, Qt.SortOrder.AscendingOrder)
        add_table_shortcuts(self._table, on_delete=self._remove_selected)
        layout.addWidget(self._table)

        self._empty_lbl = QLabel(tr("No symbols yet.\nClick '+ Add Symbol' to start tracking."))
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setObjectName("muted")
        layout.addWidget(self._empty_lbl)

        del_btn = QPushButton(tr("🗑 Remove"))
        del_btn.setObjectName("danger")
        hug_button(del_btn)
        del_btn.clicked.connect(self._remove_selected)
        del_btn.setToolTip(tr("Remove selected (Del)"))
        layout.addWidget(del_btn)

    # ── Data / table ─────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Public entry: reload rows from DB and trigger a live fetch."""
        self._reload()
        self._fetch()

    def _reload(self) -> None:
        """(Re)build table rows from the DB watchlist, showing cached prices."""
        rows = self._db.get_watchlist(self._user["id"])
        self._watch = rows
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        self._empty_lbl.setVisible(not rows)
        self._table.setVisible(bool(rows))

        for r, w in enumerate(rows):
            name = w.get("display_name") or "—"
            cells = [
                (w["symbol"], None),
                (name, None),
                (tr(w["asset_type"]), None),
                (self._fmt_price(w.get("last_price")), w.get("last_price")),
                (self._fmt_change(w.get("last_change_pct")), w.get("last_change_pct")),
                ((w.get("last_updated") or "—"), None),
            ]
            for c, (text, sort_key) in enumerate(cells):
                item = SortableItem(text, sort_key)
                item.setData(Qt.ItemDataRole.UserRole, w["id"])
                if c in (3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 4:
                    item.setForeground(self._change_color(w.get("last_change_pct")))
                self._table.setItem(r, c, item)

        self._table.setSortingEnabled(True)

    def _fetch(self) -> None:
        """Start a background quote fetch for the current watchlist."""
        if self._fetching or not getattr(self, "_watch", None):
            return
        items = [
            {"symbol": w["symbol"], "asset_type": w["asset_type"], "provider_id": w.get("provider_id")}
            for w in self._watch
        ]
        self._fetching = True
        self._status.setText(tr("Updating…"))
        worker = _QuotesWorker(items, self._currency)
        worker.signals.done.connect(self._on_quotes)
        self._pool.start(worker)

    def _on_quotes(self, result: dict) -> None:
        self._fetching = False
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        any_ok = False

        # Pause sorting so rows don't reshuffle mid-update; the visual order may
        # differ from _reload's if the user clicked a header, so locate each row
        # by its watch id rather than a cached index.
        self._table.setSortingEnabled(False)
        for w in self._watch:
            key = (w["symbol"].upper(), w["asset_type"])
            quote = result.get(key)
            row = self._row_for_watch(w["id"])
            if quote is None or not quote.ok or row is None:
                continue
            any_ok = True
            self._db.update_watch_cache(w["id"], quote.price, quote.change_pct, quote.currency, now)
            self._set_cell(row, 3, self._fmt_price(quote.price), align_right=True,
                           sort_key=quote.price)
            self._set_cell(row, 4, self._fmt_change(quote.change_pct),
                           align_right=True, color=self._change_color(quote.change_pct),
                           sort_key=quote.change_pct)
            self._set_cell(row, 5, now)
        self._table.setSortingEnabled(True)

        if any_ok:
            self._status.setText(tr("Updated {time}").format(time=now))
        else:
            self._status.setText(tr("⚠ Couldn't update — showing last saved values"))

    def _row_for_watch(self, watch_id) -> Optional[int]:
        """Current visual row whose symbol cell carries this watch id, or None."""
        for r in range(self._table.rowCount()):
            it = self._table.item(r, 0)
            if it is not None and it.data(Qt.ItemDataRole.UserRole) == watch_id:
                return r
        return None

    def _set_cell(self, row: int, col: int, text: str, align_right=False, color=None,
                  sort_key=None) -> None:
        item = self._table.item(row, col)
        if item is None:
            return
        item.setText(text)
        if sort_key is not None:
            item.setData(SORT_ROLE, sort_key)
        if align_right:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if color is not None:
            item.setForeground(color)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _add_symbol(self) -> None:
        dlg = AddWatchDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        symbol, asset_type, name = dlg.values()
        # Guard: a well-known crypto ticker (BTC, ETH…) added as a Stock is almost
        # always a mistake — there are unrelated low-priced stocks under the same
        # tickers, which is how "BTC" can show ~$37 instead of the real coin price.
        if asset_type == "Stock" and ms.known_crypto_id(symbol):
            reply = QMessageBox.question(
                self, tr("Add Symbol"),
                tr("'{symbol}' looks like a cryptocurrency. Add it as Crypto instead?").format(symbol=symbol),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                asset_type = "Crypto"

        # Resolve a provider id without touching the network (keeps UI snappy)
        if asset_type == "Crypto":
            provider_id = ms.known_crypto_id(symbol)   # may be None → resolved at fetch
        else:
            provider_id = ms.default_stock_provider_id(symbol)
        self._db.add_watch(self._user["id"], symbol, asset_type, provider_id, name or None)
        self._reload()
        self._fetch()

    def _remove_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        watch_id = item.data(Qt.ItemDataRole.UserRole)
        symbol = item.text()
        reply = QMessageBox.question(
            self, tr("🗑 Remove"),
            tr("Remove '{symbol}' from your watchlist?").format(symbol=symbol),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.remove_watch(watch_id)
            self._reload()

    # ── Interval ─────────────────────────────────────────────────────────────

    def _apply_interval(self) -> None:
        minutes = self._interval_combo.currentData() or 0
        if minutes:
            self._timer.start(minutes * 60 * 1000)
            self._fetch()        # refresh now when enabling auto-refresh
        else:
            self._timer.stop()   # manual mode — only the Refresh button fetches

    # ── Formatting helpers ───────────────────────────────────────────────────

    def _fmt_price(self, value: Optional[float]) -> str:
        if value is None:
            return "—"
        return f"{self._currency} {value:,.2f}"

    @staticmethod
    def _fmt_change(value: Optional[float]) -> str:
        if value is None:
            return "—"
        return f"{value:+.2f}%"

    @staticmethod
    def _change_color(value: Optional[float]):
        from PyQt6.QtGui import QColor
        if value is None:
            return QColor(MUTED)
        return QColor(GREEN if value >= 0 else RED)
