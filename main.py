#!/usr/bin/env python3
"""
main.py
Budget Manager — application entry point.

Usage:
    python main.py                  # Normal launch
    python main.py --seed           # Seed demo data, then launch
    python main.py --reset          # Delete database and start fresh
"""

import sys
import os
import argparse
from pathlib import Path

# ── Make package root importable regardless of CWD ────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from database.schema   import DatabaseManager
from services.auth_service  import AuthService
from services.backup_service import BackupService
from views.login_view  import LoginView
from views.main_window import MainWindow
from views.theme       import DARK_QSS
from views.i18n        import set_language


# ── Paths ──────────────────────────────────────────────────────────────────────
def _user_data_root() -> Path:
    """
    Folder where the app keeps its database and backups.

    * Packaged (.exe): a stable per-user location (``%APPDATA%\\BudgetManager``
      on Windows, ``~/.local/share/BudgetManager`` elsewhere). A one-file build
      unpacks to a temp dir that Windows deletes on exit, so data must NOT live
      next to the executable.
    * Source run: the project folder, so existing development data keeps working.
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
        return Path(base) / "BudgetManager"
    return ROOT


APP_ROOT   = _user_data_root()
DATA_DIR   = APP_ROOT / "data"
DB_PATH    = str(DATA_DIR / "budget.db")
BACKUP_DIR = str(APP_ROOT / "backups")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Budget Manager")
    p.add_argument("--seed",  action="store_true", help="Seed sample data before launching")
    p.add_argument("--reset", action="store_true", help="Delete the database and start fresh")
    p.add_argument("--theme", choices=["dark", "light"], default=None,
                   help="UI theme (overrides the saved preference for this run)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # ── Optional resets ────────────────────────────────────────────────────────
    if args.reset and Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
        print("Database deleted.")

    # ── Ensure data + backup directories exist ─────────────────────────────────
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

    # ── Optional seeding ──────────────────────────────────────────────────────
    if args.seed:
        print("Seeding sample data…")
        from scripts.seed_sample_data import main as seed
        seed()

    # ── Qt application ─────────────────────────────────────────────────────────
    # High-DPI policy MUST be set before QApplication is created
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Budget Manager")
    app.setOrganizationName("BudgetApp")
    app.setStyleSheet(DARK_QSS)

    # ── Services ───────────────────────────────────────────────────────────────
    db     = DatabaseManager(DB_PATH)
    auth   = AuthService(db)
    backup = BackupService(DB_PATH, BACKUP_DIR)

    # ── Login dialog ───────────────────────────────────────────────────────────
    login_dlg = LoginView(auth)

    user_holder: list = []

    def on_login_success(user: dict) -> None:
        user_holder.append(user)

    login_dlg.login_success.connect(on_login_success)

    result = login_dlg.exec()
    if result != login_dlg.DialogCode.Accepted or not user_holder:
        return 0

    user = user_holder[0]

    # ── Apply the user's saved language before building the UI ─────────────────
    set_language(user.get("language", "en"))

    # ── Main window ────────────────────────────────────────────────────────────
    # Saved per-user theme wins; an explicit --theme flag overrides it for this run.
    theme = args.theme or user.get("theme") or "dark"
    window = MainWindow(db, user, backup, current_theme=theme)
    app._main_window = window  # keep reference alive
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
