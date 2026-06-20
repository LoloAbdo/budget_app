"""Helpers for click-to-sort QTableWidget columns.

Qt's QTableWidget already supports header-click sorting (first click ascending,
second descending) once ``setSortingEnabled(True)`` is set. The catch is that the
default ``QTableWidgetItem`` compares by its *displayed text*, so currency
columns like ``"$1,234.56"`` and percentages sort lexically (wrong) instead of
numerically. ``SortableItem`` fixes that by sorting on a hidden numeric key when
one is provided, falling back to text otherwise.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

# A private role for the comparable sort key. Views already stash DB row ids in
# UserRole, so we use the next role to avoid clobbering them.
SORT_ROLE = Qt.ItemDataRole.UserRole + 1


class SortableItem(QTableWidgetItem):
    """Table item that sorts by an optional numeric key, else by text."""

    def __init__(self, text: str = "", sort_key=None):
        super().__init__(text)
        if sort_key is not None:
            self.setData(SORT_ROLE, sort_key)

    def __lt__(self, other: QTableWidgetItem) -> bool:  # noqa: D401
        a = self.data(SORT_ROLE)
        b = other.data(SORT_ROLE) if isinstance(other, QTableWidgetItem) else None
        if a is not None and b is not None:
            try:
                return a < b
            except TypeError:
                pass
        return super().__lt__(other)


def enable_sorting(table: QTableWidget, column: int = 0,
                   order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
    """Turn on click-to-sort and pick the initial sort column/order."""
    table.setSortingEnabled(True)
    table.horizontalHeader().setSortIndicatorShown(True)
    table.horizontalHeader().setSortIndicator(column, order)
