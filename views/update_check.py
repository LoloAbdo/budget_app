"""
views/update_check.py
A small QRunnable that checks GitHub for a newer release off the UI thread.
Shared by the Settings 'About' tab and the quiet startup check in MainWindow.
"""

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from services.update_service import check_for_update, download_file, UpdateInfo


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


class _DownloadSignals(QObject):
    progress = pyqtSignal(int, int)   # bytes_done, total (total=0 if unknown)
    done     = pyqtSignal(str)        # path to the downloaded installer
    error    = pyqtSignal(str)


class UpdateDownloadWorker(QRunnable):
    """Downloads the installer off the UI thread, reporting progress."""

    def __init__(self, url: str, dest: str) -> None:
        super().__init__()
        self._url = url
        self._dest = dest
        self.signals = _DownloadSignals()

    def run(self) -> None:
        try:
            download_file(
                self._url, self._dest,
                progress_cb=lambda done, total: self.signals.progress.emit(done, total),
            )
            self.signals.done.emit(self._dest)
        except Exception as exc:
            self.signals.error.emit(str(exc))
