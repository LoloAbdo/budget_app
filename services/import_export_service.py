"""
services/import_export_service.py
Handles CSV and Excel import/export of transactions.
"""

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from database import DatabaseManager


class ImportExportService:
    """Reads/writes transaction data in CSV and Excel formats."""

    TRANSACTION_HEADERS = ["date", "description", "amount", "currency", "category", "account", "notes"]
    AUDIT_HEADERS = ["timestamp", "action", "entity", "entity_id", "user_id", "details"]

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ── Export ────────────────────────────────────────────────────────────────

    def export_csv(self, user_id: int, dest_path: str, **filters) -> int:
        """Export transactions to CSV; returns row count."""
        rows = self._db.get_transactions(user_id, **filters)
        with open(dest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.TRANSACTION_HEADERS, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow({
                    "date": r["date"],
                    "description": r["description"],
                    "amount": r["amount"],
                    "currency": r.get("account_currency", ""),
                    "category": r.get("category_name", ""),
                    "account": r.get("account_name", ""),
                    "notes": r.get("notes", ""),
                })
        return len(rows)

    def export_excel(self, user_id: int, dest_path: str, **filters) -> int:
        """Export transactions to Excel; returns row count."""
        rows = self._db.get_transactions(user_id, **filters)
        data = [{
            "Date": r["date"],
            "Description": r["description"],
            "Amount": r["amount"],
            "Currency": r.get("account_currency", ""),
            "Category": r.get("category_name", ""),
            "Account": r.get("account_name", ""),
            "Notes": r.get("notes", ""),
        } for r in rows]
        df = pd.DataFrame(data)
        df.to_excel(dest_path, index=False, engine="openpyxl")
        return len(rows)

    def export_audit_log_csv(self, dest_path: str) -> int:
        """Export the full activity/audit log to CSV; returns the row count."""
        rows = self._db.get_audit_log()
        with open(dest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.AUDIT_HEADERS, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow({
                    "timestamp": r["timestamp"],
                    "action":    r["action"],
                    "entity":    r["entity"],
                    "entity_id": r["entity_id"],
                    "user_id":   r["user_id"],
                    "details":   r["details"] or "",
                })
        return len(rows)

    # ── Import ────────────────────────────────────────────────────────────────

    def import_csv(self, user_id: int, src_path: str) -> tuple[int, list[str]]:
        """
        Import transactions from CSV.
        Expected columns: date, description, amount, category (optional), account (optional).
        Returns (imported_count, list_of_errors).
        """
        errors: list[str] = []
        imported = 0
        accounts = {a["account_name"]: a["id"] for a in self._db.get_accounts(user_id)}
        categories = {c["name"]: c["id"] for c in self._db.get_categories()}

        with open(src_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                try:
                    amount = float(row.get("amount", 0))
                    date = row.get("date", "").strip()
                    description = row.get("description", "").strip()
                    if not date or not description:
                        errors.append(f"Row {i}: missing date or description")
                        continue

                    account_name = row.get("account", "").strip()
                    account_id = accounts.get(account_name)
                    if not account_id:
                        # Use first account as fallback
                        account_id = next(iter(accounts.values()), None)
                    if not account_id:
                        errors.append(f"Row {i}: no accounts available")
                        continue

                    cat_name = row.get("category", "").strip()
                    category_id = categories.get(cat_name)

                    self._db.create_transaction(
                        account_id=account_id,
                        category_id=category_id,
                        date=date,
                        description=description,
                        amount=amount,
                        notes=row.get("notes", "").strip(),
                    )
                    imported += 1
                except Exception as e:
                    errors.append(f"Row {i}: {e}")

        return imported, errors

    def import_excel(self, user_id: int, src_path: str) -> tuple[int, list[str]]:
        """Import from Excel (.xlsx). Delegates to import_csv after converting."""
        tmp_csv = str(src_path).replace(".xlsx", "_tmp.csv")
        df = pd.read_excel(src_path, engine="openpyxl")
        df.columns = [c.lower() for c in df.columns]
        df.to_csv(tmp_csv, index=False)
        result = self.import_csv(user_id, tmp_csv)
        Path(tmp_csv).unlink(missing_ok=True)
        return result
