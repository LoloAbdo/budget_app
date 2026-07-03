"""
views/fx_refresh.py
A small QRunnable that refreshes cached exchange rates off the UI thread.
Shared by the Settings 'Currency' tab and the quiet startup refresh in
MainWindow.
"""

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from database import DatabaseManager
from services.fx_service import FxService


class _Signals(QObject):
    done = pyqtSignal(dict)   # {"USD→CAD": 1.37, ...}; None values = fetch failed


class FxRefreshWorker(QRunnable):
    def __init__(self, db: DatabaseManager, user_id: int) -> None:
        super().__init__()
        self._db = db
        self._user_id = user_id
        self.signals = _Signals()

    def run(self) -> None:
        try:
            results = FxService(self._db).refresh(self._user_id)
        except Exception:
            results = {}
        self.signals.done.emit(results)
