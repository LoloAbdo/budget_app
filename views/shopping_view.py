"""
views/shopping_view.py
Shopping price tracker: watch Amazon product URLs (or seed from a public
wishlist), keep the starting price, and re-check prices on a background thread.
A price below the frozen start price raises a dashboard alert.

Network fetching runs in a QRunnable on the global thread pool so the UI never
blocks. Cached prices show instantly; a blocked/failed fetch keeps the last
price and shows a "stale" status instead of crashing.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDialog, QFormLayout, QMessageBox,
    QTableWidget, QHeaderView,
)
from PyQt6.QtCore import Qt, QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtGui import QColor

from database import DatabaseManager
from services import shopping_service as ss
from views.i18n import tr
from views.sortable import SortableItem, enable_sorting
from views.widgets import add_table_shortcuts, hug_button

GREEN = "#10B981"
RED = "#EF4444"
AMBER = "#F59E0B"
MUTED = "#8A8FA3"

# Skip re-fetching an item checked more recently than this on tab open.
_STALE_AFTER = timedelta(hours=1)
# Politeness delay between product requests (avoid hammering Amazon).
_REQUEST_GAP = 0.8  # seconds


# ── Background workers ───────────────────────────────────────────────────────

class _PricesSignals(QObject):
    done = pyqtSignal(object)   # dict[item_id] -> ItemInfo


class _PricesWorker(QRunnable):
    """Fetch fresh prices for the given items off the UI thread."""

    def __init__(self, items: list[dict]) -> None:
        super().__init__()
        self._items = items
        self.signals = _PricesSignals()

    def run(self) -> None:
        result: dict[int, ss.ItemInfo] = {}
        for i, it in enumerate(self._items):
            try:
                result[it["id"]] = ss.fetch_item(it["url"])
            except Exception:
                pass
            if i < len(self._items) - 1:
                time.sleep(_REQUEST_GAP)
        self.signals.done.emit(result)


class _WishlistSignals(QObject):
    done = pyqtSignal(object)   # list[seed dict]


class _WishlistWorker(QRunnable):
    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url
        self.signals = _WishlistSignals()

    def run(self) -> None:
        try:
            seeds = ss.fetch_wishlist(self._url)
        except Exception:
            seeds = []
        self.signals.done.emit(seeds)


# ── Add dialogs ──────────────────────────────────────────────────────────────

class _AddUrlDialog(QDialog):
    def __init__(self, title: str, label: str, placeholder: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        form.addRow(label, self._edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton(tr("Cancel"))
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr("Add"))
        save.setDefault(True)
        save.clicked.connect(self._accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _accept(self) -> None:
        if not self._edit.text().strip():
            QMessageBox.warning(self, tr("Validation"), tr("A URL is required."))
            return
        self.accept()

    def url(self) -> str:
        return self._edit.text().strip()


# ── Shopping view ────────────────────────────────────────────────────────────

class ShoppingView(QWidget):
    COLS = ["Item", "Start Price", "Current", "Change", "Status", "Checked"]

    prices_changed = pyqtSignal()   # emitted after prices persist (dashboard alert refresh)

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._pool = QThreadPool.globalInstance()
        self._fetching = False
        self._items: list[dict] = []

        self._build_ui()
        self._reload()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel(tr("Shopping"))
        title.setObjectName("heading")
        head.addWidget(title)
        head.addStretch()

        self._refresh_btn = QPushButton(tr("Refresh"))
        self._refresh_btn.setObjectName("secondary")
        self._refresh_btn.clicked.connect(lambda: self._fetch())
        head.addWidget(self._refresh_btn)

        wl_btn = QPushButton(tr("+ Add Wishlist"))
        wl_btn.setObjectName("secondary")
        wl_btn.clicked.connect(self._add_wishlist)
        head.addWidget(wl_btn)

        add_btn = QPushButton(tr("+ Add Product"))
        add_btn.clicked.connect(self._add_product)
        head.addWidget(add_btn)
        layout.addLayout(head)

        hint = QLabel(tr(
            "Tracks Amazon product prices. Prices are scraped best-effort and can "
            "be blocked or delayed by Amazon — a drop below the starting price "
            "alerts you on the Dashboard."
        ))
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

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
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, len(self.COLS)):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        enable_sorting(self._table, 0, Qt.SortOrder.AscendingOrder)
        add_table_shortcuts(self._table, on_delete=self._remove_selected)
        layout.addWidget(self._table)

        self._empty_lbl = QLabel(
            tr("No tracked items yet.\nClick '+ Add Product' to start tracking a price.")
        )
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setObjectName("muted")
        layout.addWidget(self._empty_lbl)

        del_btn = QPushButton(tr("🗑 Remove"))
        del_btn.setObjectName("danger")
        hug_button(del_btn)
        del_btn.clicked.connect(self._remove_selected)
        del_btn.setToolTip(tr("Remove selected (Del)"))
        layout.addWidget(del_btn)

    # ── Data / table ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Public entry (e.g. from data_changed): reload rows from the DB."""
        self._reload()

    def refresh_on_open(self) -> None:
        """Called when the Shopping tab opens: show cached rows, then re-fetch
        only items not checked within the last hour (avoid hammering Amazon)."""
        self._reload()
        stale = [it for it in self._items if self._is_stale(it)]
        if stale:
            self._fetch(stale)

    def _is_stale(self, item: dict) -> bool:
        last = item.get("last_checked")
        if not last:
            return True
        try:
            return datetime.now() - datetime.fromisoformat(last) > _STALE_AFTER
        except ValueError:
            return True

    def _reload(self) -> None:
        rows = self._db.get_watched_items(self._user["id"])
        self._items = rows
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        self._empty_lbl.setVisible(not rows)
        self._table.setVisible(bool(rows))
        for r, it in enumerate(rows):
            self._fill_row(r, it)
        self._table.setSortingEnabled(True)

    def _fill_row(self, r: int, it: dict) -> None:
        cur = it.get("currency") or "CAD"
        start = it.get("start_price")
        current = it.get("current_price")
        change = (current - start) if (start is not None and current is not None) else None
        cells = [
            (it.get("title") or it.get("url") or "—", None),
            (self._fmt_price(start, cur), start),
            (self._fmt_price(current, cur), current),
            (self._fmt_change(change, cur), change),
            (self._status_text(it, change), None),
            (self._fmt_checked(it.get("last_checked")), None),
        ]
        for c, (text, sort_key) in enumerate(cells):
            item = SortableItem(text, sort_key)
            item.setData(Qt.ItemDataRole.UserRole, it["id"])
            if c in (1, 2, 3):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if c == 3 and change is not None:
                item.setForeground(QColor(GREEN if change < 0 else (RED if change > 0 else MUTED)))
            self._table.setItem(r, c, item)

    def _status_text(self, it: dict, change) -> str:
        if it.get("is_blocked"):
            return tr("⚠ Blocked (stale)")
        if it.get("current_price") is None:
            return tr("Not checked yet")
        if change is not None and change < 0:
            return tr("⬇ Price dropped")
        return tr("Tracking")

    # ── Fetch ──────────────────────────────────────────────────────────────────

    def _fetch(self, items: Optional[list[dict]] = None) -> None:
        items = items if items is not None else self._items
        if self._fetching or not items:
            return
        payload = [{"id": it["id"], "url": it["url"]} for it in items]
        self._fetching = True
        self._refresh_btn.setEnabled(False)
        self._status.setText(tr("Checking prices…"))
        worker = _PricesWorker(payload)
        worker.signals.done.connect(self._on_prices)
        self._pool.start(worker)

    def _on_prices(self, result: dict) -> None:
        self._fetching = False
        self._refresh_btn.setEnabled(True)
        now = datetime.now().isoformat(timespec="seconds")
        any_ok = any_blocked = False
        for item_id, info in result.items():
            if info.ok and info.price is not None:
                any_ok = True
                self._db.update_item_price(item_id, info.price, info.currency,
                                           info.title, now)
            elif info.blocked:
                any_blocked = True
                self._db.mark_item_blocked(item_id, now)
        self._reload()
        if any_ok:
            self.prices_changed.emit()   # a fresh price may have crossed the start
            self._status.setText(tr("Prices updated {time}").format(
                time=datetime.now().strftime("%Y-%m-%d %H:%M")))
        elif any_blocked:
            self._status.setText(tr("⚠ Amazon blocked the request — showing last saved prices"))
        else:
            self._status.setText(tr("⚠ Couldn't update — showing last saved prices"))

    # ── Actions ────────────────────────────────────────────────────────────────

    def _add_product(self) -> None:
        dlg = _AddUrlDialog(tr("Add Product"), tr("Product URL"),
                            "https://www.amazon.ca/dp/…", self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        url = dlg.url()
        asin = ss.asin_from_url(url)
        if not asin:
            QMessageBox.warning(
                self, tr("Add Product"),
                tr("That doesn't look like an Amazon product URL (no product id found)."))
            return
        domain = ss.domain_from_url(url)
        canon = ss.canonical_url(asin, domain) or url
        item_id = self._db.add_watched_item(
            self._user["id"], canon, asin=asin, domain=domain,
            currency=ss.currency_for_domain(domain))
        self._reload()
        self._fetch([{"id": item_id, "url": canon}])

    def _add_wishlist(self) -> None:
        dlg = _AddUrlDialog(tr("Add Wishlist"), tr("Public wishlist URL"),
                            "https://www.amazon.ca/hz/wishlist/ls/…", self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._status.setText(tr("Reading wishlist…"))
        worker = _WishlistWorker(dlg.url())
        worker.signals.done.connect(self._on_wishlist)
        self._pool.start(worker)

    def _on_wishlist(self, seeds: list) -> None:
        if not seeds:
            self._status.setText(
                tr("Couldn't read the wishlist (empty, private, or blocked)."))
            return
        added = []
        for s in seeds:
            if not s.get("asin"):
                continue
            item_id = self._db.add_watched_item(
                self._user["id"], s["url"], asin=s["asin"], domain=s["domain"],
                title=s.get("title"),
                currency=ss.currency_for_domain(s["domain"]),
                start_price=s.get("price"))
            added.append({"id": item_id, "url": s["url"]})
        self._reload()
        if added:
            self.prices_changed.emit()  # seeded start prices may already differ
            self._status.setText(tr("Added {n} item(s) from wishlist.").format(n=len(added)))
            self._fetch(added)

    def _remove_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()
        reply = QMessageBox.question(
            self, tr("🗑 Remove"),
            tr("Stop tracking '{name}'?").format(name=name[:60]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.remove_watched_item(item_id)
            self._reload()

    # ── Formatting ─────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_price(value: Optional[float], currency: str) -> str:
        if value is None:
            return "—"
        return f"{currency} {value:,.2f}"

    @staticmethod
    def _fmt_change(value: Optional[float], currency: str) -> str:
        if value is None:
            return "—"
        sign = "−" if value < 0 else ("+" if value > 0 else "")
        return f"{sign}{currency} {abs(value):,.2f}"

    @staticmethod
    def _fmt_checked(iso: Optional[str]) -> str:
        """'2026-07-12T14:44:50' -> '2026-07-12 14:44' (still sorts lexically)."""
        if not iso:
            return "—"
        return iso.replace("T", " ")[:16]
