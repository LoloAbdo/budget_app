"""
tests/test_budget_alerts.py
Tests for DatabaseManager.get_budget_alerts — the dashboard budget warnings.
"""

from datetime import datetime


def _now():
    n = datetime.now()
    return n.month, n.year


def _expense_category(db) -> int:
    return next(c["id"] for c in db.get_categories("Expense"))


def _spend(db, account_id, category_id, amount: float):
    """Record an expense (negative) dated today."""
    today = datetime.now().strftime("%Y-%m-%d")
    db.create_transaction(account_id, category_id, today, "spend", -abs(amount))


def test_no_budgets_means_no_alerts(db, user_id, account_id):
    month, year = _now()
    assert db.get_budget_alerts(user_id, month, year) == []


def test_under_threshold_is_not_alerted(db, user_id, account_id):
    month, year = _now()
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, month, year, 100.0)
    _spend(db, account_id, cat, 50.0)  # 50% — below the 90% default
    assert db.get_budget_alerts(user_id, month, year) == []


def test_near_limit_alerts_without_over_flag(db, user_id, account_id):
    month, year = _now()
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, month, year, 100.0)
    _spend(db, account_id, cat, 95.0)  # 95% — near but not over
    alerts = db.get_budget_alerts(user_id, month, year)
    assert len(alerts) == 1
    assert alerts[0]["over"] is False
    assert round(alerts[0]["ratio"], 2) == 0.95


def test_over_budget_sets_over_flag(db, user_id, account_id):
    month, year = _now()
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, month, year, 100.0)
    _spend(db, account_id, cat, 120.0)  # 120% — over
    alerts = db.get_budget_alerts(user_id, month, year)
    assert len(alerts) == 1
    assert alerts[0]["over"] is True


def test_alerts_sorted_worst_first(db, user_id, account_id):
    month, year = _now()
    cats = [c["id"] for c in db.get_categories("Expense")][:2]
    db.upsert_budget(user_id, cats[0], month, year, 100.0)
    db.upsert_budget(user_id, cats[1], month, year, 100.0)
    _spend(db, account_id, cats[0], 95.0)   # 95%
    _spend(db, account_id, cats[1], 150.0)  # 150%
    alerts = db.get_budget_alerts(user_id, month, year)
    assert [a["category_id"] for a in alerts] == [cats[1], cats[0]]


def test_zero_budget_is_skipped(db, user_id, account_id):
    month, year = _now()
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, month, year, 0.0)
    _spend(db, account_id, cat, 50.0)
    assert db.get_budget_alerts(user_id, month, year) == []
