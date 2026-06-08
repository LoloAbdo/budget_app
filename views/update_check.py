"""
views/update_check.py
A small QRunnable that checks GitHub for a newer release off the UI thread.
Shared by the Settings 'About' tab and the quiet startup check in MainWindow.
"""

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from services.update_service import check_for_update, UpdateInfo


class _Signals(QObject):
    done = pyqtSignal(object)   # emits an UpdateInfo


class UpdateCheckWorker(QRunnable):
    def __init__(self, current_version: str) -> None:
        super().__init__()
        self._current = current_version
        self.signals = _Signals()

    def run(self) -> None:
        try:
            info = check_for_update(self._current)
        except Exception as exc:  # defensive — check_for_update already swallows
            info = UpdateInfo(error=str(exc))
        self.signals.done.emit(info)
