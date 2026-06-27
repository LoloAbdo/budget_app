"""
tests/test_audit_log.py
Covers the audit trail: every create/update/delete the DatabaseManager performs
is recorded in audit_log, and the CSV export emits one row per entry.
"""

import csv
import json

import pytest

from services.import_export_service import ImportExportService


def _logs(db, entity=None):
    rows = db.get_audit_log()
    return [r for r in rows if entity is None or r["entity"] == entity]


def test_transaction_crud_is_logged(db, user_id, account_id):
    cid = next(iter(c["id"] for c in db.get_categories()))
    tid = db.create_transaction(account_id, cid, "2026-01-01", "Coffee", -5.0, "")
    db.update_transaction(tid, account_id, cid, "2026-01-01", "Coffee", -6.0, "")
    db.delete_transaction(tid)

    actions = [r["action"] for r in _logs(db, "transaction")]
    assert actions == ["DELETE", "UPDATE", "INSERT"]   # newest first

    # The INSERT row carries a JSON snapshot of the amount.
    insert = [r for r in _logs(db, "transaction") if r["action"] == "INSERT"][0]
    assert json.loads(insert["details"])["amount"] == -5.0
    assert insert["entity_id"] == tid


def test_account_and_category_logged(db, user_id):
    aid = db.create_account(user_id, "Wallet", "Checking", 10.0)
    db.update_account(aid, "Wallet 2", "Checking", 20.0)
    db.delete_account(aid)
    assert [r["action"] for r in _logs(db, "account")] == ["DELETE", "UPDATE", "INSERT"]

    cid = db.create_category("Hobbies", "Expense", "#abcdef")
    db.delete_category(cid)
    assert [r["action"] for r in _logs(db, "category")] == ["DELETE", "INSERT"]


def test_transfer_logged(db, user_id, account_id, savings_id):
    db.create_transfer(account_id, savings_id, 50.0, "2026-01-01", "Move", "")
    rows = _logs(db, "transfer")
    assert len(rows) == 1 and rows[0]["action"] == "INSERT"
    assert json.loads(rows[0]["details"])["amount"] == 50.0


def test_password_change_does_not_log_hash(db, user_id):
    db.update_user_password(user_id, "super-secret-hash")
    row = [r for r in _logs(db, "user") if r["action"] == "UPDATE"][0]
    assert "super-secret-hash" not in (row["details"] or "")
    assert json.loads(row["details"]) == {"password": "changed"}


def test_balance_side_effects_not_logged(db, user_id, account_id):
    """Internal balance updates from a transaction shouldn't spam the log."""
    cid = next(iter(c["id"] for c in db.get_categories()))
    db.create_transaction(account_id, cid, "2026-01-01", "x", -5.0, "")
    # Exactly one transaction INSERT, and no separate 'account' UPDATE for the
    # running-balance change it triggered.
    assert len(_logs(db, "transaction")) == 1
    assert all(r["entity"] != "account" for r in db.get_audit_log()
               if r["action"] == "UPDATE")


def test_export_audit_log_csv(db, user_id, account_id, tmp_path):
    cid = next(iter(c["id"] for c in db.get_categories()))
    db.create_transaction(account_id, cid, "2026-01-01", "x", -5.0, "")
    out = tmp_path / "log.csv"
    n = ImportExportService(db).export_audit_log_csv(str(out))
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert n == len(rows) >= 1
    assert set(rows[0].keys()) == set(ImportExportService.AUDIT_HEADERS)
