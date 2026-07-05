"""
views/update_check.py
A small QRunnable that checks GitHub for a newer release off the UI thread.
Shared by the Settings 'About' tab and the quiet startup check in MainWindow.
"""

import os
import urllib.parse

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from services.update_service import (
    check_for_update, download_file, verify_installer, UpdateInfo,
    INSTALLER_ASSET_NAME,
)


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
    """Downloads and verifies the installer off the UI thread.

    After the download, the file's size and SHA-256 are checked against the
    release metadata (see update_service.verify_installer). A failed check
    deletes the file and reports an error instead of emitting done — the
    installer is never launched unverified.
    """

    def __init__(self, url: str, dest: str,
                 expected_size: int = 0, checksums_url: str | None = None) -> None:
        super().__init__()
        self._url = url
        self._dest = dest
        self._expected_size = expected_size
        self._checksums_url = checksums_url
        self.signals = _DownloadSignals()

    def run(self) -> None:
        try:
            download_file(
                self._url, self._dest,
                progress_cb=lambda done, total: self.signals.progress.emit(done, total),
            )
            # The checksums file lists assets by filename — use the name the
            # asset actually has on the release, not our expected constant.
            asset_name = os.path.basename(
                urllib.parse.urlparse(self._url).path
            ) or INSTALLER_ASSET_NAME
            verify_installer(
                self._dest,
                expected_size=self._expected_size,
                checksums_url=self._checksums_url,
                asset_name=asset_name,
            )
            self.signals.done.emit(self._dest)
        except Exception as exc:
            try:
                os.remove(self._dest)
            except OSError:
                pass
            self.signals.error.emit(str(exc))
