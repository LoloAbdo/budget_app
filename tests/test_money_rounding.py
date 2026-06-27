"""
tests/test_money_rounding.py
Guards the money-precision fix: amounts are stored on exact cent boundaries and
the running account balance never drifts from the sum of its transactions, even
over many operations or with sub-cent inputs (e.g. from CSV import).
"""

import pytest

from database.schema import _money


@pytest.mark.parametrize("raw,expected", [
    (10.004, 10.0),
    (10.006, 10.01),
    (1 / 3, 0.33),
    (-2.345, -2.35),
    (0.0, 0.0),
    (None, 0.0),
])
def test_money_rounds_to_cents(raw, expected):
    # Uses Python's round() (same banker's rounding as the f"{x:,.2f}" display),
    # so the stored value always matches what the UI shows.
    assert _money(raw) == expected


def test_incremental_balance_has_no_drift(db, user_id, account_id):
    cid = next(iter(c["id"] for c in db.get_categories()))
    for _ in range(10_000):
        db.create_transaction(account_id, cid, "2026-01-01", "x", 0.01, "")
    # 1000 start + 10,000 x 0.01 = exactly 1100.00, not 1099.9999999…
    assert db.get_account(account_id)["current_balance"] == 1100.0


def test_subcent_amounts_are_stored_as_cents(db, user_id, account_id):
    cid = next(iter(c["id"] for c in db.get_categories()))
    for _ in range(5):
        db.create_transaction(account_id, cid, "2026-01-01", "x", 10.004, "")
    amounts = [r["amount"] for r in db.get_transactions(user_id)]
    assert amounts == [10.0, 10.0, 10.0, 10.0, 10.0]


def test_balance_reconciles_with_transaction_sum(db, user_id, account_id):
    """Sum of stored amounts + starting balance == stored running balance."""
    cid = next(iter(c["id"] for c in db.get_categories()))
    for amt in (12.34, -5.67, 100.005, -0.014, 8.999):
        db.create_transaction(account_id, cid, "2026-01-01", "x", amt, "")
    rows = db.get_transactions(user_id)
    txn_sum = round(sum(r["amount"] for r in rows), 2)
    bal = db.get_account(account_id)["current_balance"]
    assert bal == round(1000.0 + txn_sum, 2)


def test_edit_and_delete_keep_balance_clean(db, user_id, account_id):
    cid = next(iter(c["id"] for c in db.get_categories()))
    tid = db.create_transaction(account_id, cid, "2026-01-01", "x", 10.004, "")
    db.update_transaction(tid, account_id, cid, "2026-01-01", "x", 3.336, "")
    assert db.get_account(account_id)["current_balance"] == round(1000.0 + 3.34, 2)
    db.delete_transaction(tid)
    assert db.get_account(account_id)["current_balance"] == 1000.0
