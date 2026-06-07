"""
services/backup_service.py
Creates and restores SQLite database backups.
"""

import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class BackupService:
    """Manages daily/weekly/manual backups of the SQLite database file."""

    def __init__(self, db_path: str, backup_dir: str) -> None:
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, label: str = "manual") -> str:
        """Copy the database file to the backup directory. Returns the new path."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.backup_dir / f"budget_backup_{label}_{ts}.db"
        shutil.copy2(self.db_path, dest)
        self._prune_old_backups()
        return str(dest)

    def list_backups(self) -> list[dict]:
        """Return a list of backup dicts {path, name, size_kb, created}."""
        backups = []
        for f in sorted(self.backup_dir.glob("*.db"), reverse=True):
            stat = f.stat()
            backups.append({
                "path": str(f),
                "name": f.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
        return backups

    def restore_backup(self, backup_path: str) -> bool:
        """Overwrite the live database with the chosen backup. Returns success."""
        try:
            shutil.copy2(backup_path, self.db_path)
            return True
        except Exception:
            return False

    def _prune_old_backups(self, keep: int = 30) -> None:
        """Keep only the most recent *keep* backup files."""
        files = sorted(self.backup_dir.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
        for old in files[keep:]:
            try:
                old.unlink()
            except Exception:
                pass
