"""
tests/test_net_worth.py
Tests for DatabaseManager.get_net_worth_history — the dashboard net-worth trend.
"""

from datetime import datetime


def _ym(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _shift(year: int, month: int, back: int) -> tuple[int, int]:
    """Return (year, month) `back` months before the given month."""
    idx = year * 12 + (month - 1) - back
    return idx // 12, idx % 12 + 1


def test_returns_requested_number_of_months(db, user_id, account_id):
    history = db.get_net_worth_history(user_id, 12)
    assert len(history) == 12
    # Chronological, ending on the current month.
    now = datetime.now()
    assert history[-1]["month"] == _ym(now.year, now.month)
    assert history == sorted(history, key=lambda p: p["month"])


def test_latest_point_equals_current_total_balance(db, user_id, account_id, savings_id):
    history = db.get_net_worth_history(user_id, 6)
    expected = db.get_total_balance(user_id)
    assert history[-1]["balance"] == round(expected, 2)


def test_history_unwinds_past_transactions(db, user_id, account_id):
    """A transaction last month is reflected from that month on, but not before it."""
    now = datetime.now()
    ly, lm = _shift(now.year, now.month, 1)   # last month (txn month)
    py, pm = _shift(now.year, now.month, 2)   # two months ago (before the txn)
    # Account starts at 1000 (fixture). Add +500 income dated last month.
    db.create_transaction(account_id, None, f"{_ym(ly, lm)}-15", "Bonus", 500.0)

    history = {p["month"]: p["balance"] for p in db.get_net_worth_history(user_id, 3)}
    # End-of-month balances include transactions dated within that month.
    assert history[_ym(now.year, now.month)] == 1500.0  # current
    assert history[_ym(ly, lm)] == 1500.0               # txn month
    assert history[_ym(py, pm)] == 1000.0               # before the txn


def test_zero_months_returns_empty(db, user_id):
    assert db.get_net_worth_history(user_id, 0) == []


def test_no_accounts_is_flat_zero(db, user_id):
    history = db.get_net_worth_history(user_id, 4)
    assert len(history) == 4
    assert all(p["balance"] == 0.0 for p in history)
