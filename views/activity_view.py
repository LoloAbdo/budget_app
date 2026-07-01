"""
views/activity_view.py
Read-only viewer for the append-only activity/audit log.

Every create/update/delete the app performs is recorded in the ``audit_log``
table (see DatabaseManager._log). This panel surfaces that history in-app with
action/entity filters and a free-text search, plus a CSV export that reuses the
same service as Settings ▸ Backup & Restore.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QHeaderView, QComboBox, QLineEdit, QFrame,
    QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from database import DatabaseManager
from services.import_export_service import ImportExportService
from views.i18n import tr
from views.sortable import SortableItem, SORT_ROLE, enable_sorting
from views.widgets import make_empty_state

# Friendly labels + colors for the raw SQL action verbs.
ACTIONS = {
    "INSERT": ("Created", "#10B981"),
    "UPDATE": ("Updated", "#3B82F6"),
    "DELETE": ("Deleted", "#EF4444"),
}


class ActivityView(QWidget):
    """Activity log panel: filterable, read-only history of every change."""

    # English keys; localized at build time via tr()
    COLS = ["When", "Action", "Item", "ID", "Details"]

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._ie = ImportExportService(db)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        head_row = QHBoxLayout()
        title = QLabel(tr("Activity Log"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        refresh_btn = QPushButton(tr("⟳ Refresh"))
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh)
        head_row.addWidget(refresh_btn)

        export_btn = QPushButton(tr("⤓ Export"))
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export)
        export_btn.setToolTip(tr("Export the full activity log to CSV"))
        head_row.addWidget(export_btn)
        layout.addLayout(head_row)

        # ── Filter bar ──────────────────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setObjectName("card")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(tr("🔍 Search…"))
        self._search_edit.textChanged.connect(self._apply)
        filter_layout.addWidget(self._search_edit, 2)

        self._action_filter = QComboBox()
        self._action_filter.addItem(tr("All Actions"), None)
        for verb, (label, _color) in ACTIONS.items():
            self._action_filter.addItem(tr(label), verb)
        self._action_filter.currentIndexChanged.connect(self._apply)
        filter_layout.addWidget(self._action_filter, 1)

        self._entity_filter = QComboBox()
        self._entity_filter.addItem(tr("All Items"), None)
        self._entity_filter.currentIndexChanged.connect(self._apply)
        filter_layout.addWidget(self._entity_filter, 1)

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
        hdr.setMinimumSectionSize(60)
        self._table.setColumnWidth(0, 160)   # When
        self._table.setColumnWidth(1, 90)    # Action
        self._table.setColumnWidth(2, 110)   # Item
        self._table.setColumnWidth(3, 60)    # ID
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Details
        enable_sorting(self._table, 0, Qt.SortOrder.DescendingOrder)
        layout.addWidget(self._table)

        self._empty_lbl = make_empty_state("")
        layout.addWidget(self._empty_lbl)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("muted")
        layout.addWidget(self._count_lbl)

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload the log from the DB and repopulate the entity filter."""
        self._rows = self._db.get_audit_log()

        # Rebuild the entity dropdown from the entities actually present.
        current = self._entity_filter.currentData()
        self._entity_filter.blockSignals(True)
        self._entity_filter.clear()
        self._entity_filter.addItem(tr("All Items"), None)
        for ent in sorted({r["entity"] for r in self._rows}):
            self._entity_filter.addItem(tr(ent.capitalize()), ent)
        idx = self._entity_filter.findData(current)
        self._entity_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self._entity_filter.blockSignals(False)

        self._apply()

    def _apply(self) -> None:
        """Apply the search + action + entity filters and repaint the table."""
        keyword = self._search_edit.text().strip().lower()
        action  = self._action_filter.currentData()
        entity  = self._entity_filter.currentData()

        rows = []
        for r in self._rows:
            if action and r["action"] != action:
                continue
            if entity and r["entity"] != entity:
                continue
            if keyword:
                haystack = f"{r['entity']} {r['details'] or ''}".lower()
                if keyword not in haystack:
                    continue
            rows.append(r)

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            verb_label, verb_color = ACTIONS.get(r["action"], (r["action"], "#9CA3AF"))
            values = [
                r["timestamp"],
                tr(verb_label),
                tr(r["entity"].capitalize()),
                str(r["entity_id"]) if r["entity_id"] is not None else "—",
                r["details"] or "",
            ]
            for c, text in enumerate(values):
                item = SortableItem(text)
                if c == 1:
                    item.setForeground(QColor(verb_color))
                if c == 3 and r["entity_id"] is not None:
                    item.setData(SORT_ROLE, r["entity_id"])  # numeric sort on ID
                self._table.setItem(i, c, item)
        self._table.setSortingEnabled(True)

        self._count_lbl.setText(tr("{n} entries").format(n=len(rows)))
        self._empty_lbl.setText(
            tr("No activity matches your filters.") if self._rows
            else tr("No activity recorded yet.")
        )
        self._empty_lbl.setVisible(not rows)
        self._table.setVisible(bool(rows))

    def _clear_filters(self) -> None:
        self._search_edit.clear()
        self._action_filter.setCurrentIndex(0)
        self._entity_filter.setCurrentIndex(0)

    # ── Export ──────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        if not self._rows:
            QMessageBox.information(self, tr("Export"), tr("There is no activity to export."))
            return
        default = f"activity_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export Activity Log"), default, "CSV Files (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            count = self._ie.export_audit_log_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, tr("Export Failed"), str(exc))
            return
        QMessageBox.information(
            self, tr("Export"),
            tr("Exported {n} entries to:\n{path}").format(n=count, path=path),
        )
