"""
tests/test_budget_rollover.py
Tests for per-budget rollover: unspent (or overspent) budget carried into the
next month's effective limit (DatabaseManager rollover walk + alerts).
"""


def _expense_category(db) -> int:
    return next(c["id"] for c in db.get_categories("Expense"))


def _spend(db, account_id, category_id, amount: float, date: str):
    """Record an expense (negative) on a specific date (YYYY-MM-DD)."""
    db.create_transaction(account_id, category_id, date, "spend", -abs(amount))


def _budget(db, user_id, category_id, month, year):
    return next(
        b for b in db.get_budgets(user_id, month, year)
        if b["category_id"] == category_id
    )


def test_non_rollover_budget_has_no_carryover(db, user_id, account_id):
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, 3, 2025, 100.0)          # prior, no rollover
    _spend(db, account_id, cat, 40.0, "2025-03-10")
    db.upsert_budget(user_id, cat, 4, 2025, 100.0)          # current, no rollover
    b = _budget(db, user_id, cat, 4, 2025)
    assert b["carryover"] == 0.0
    assert b["effective_budget"] == 100.0


def test_underspend_rolls_forward_as_extra_room(db, user_id, account_id):
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, 3, 2025, 100.0, rollover=True)
    _spend(db, account_id, cat, 40.0, "2025-03-10")         # 60 left
    db.upsert_budget(user_id, cat, 4, 2025, 100.0, rollover=True)
    b = _budget(db, user_id, cat, 4, 2025)
    assert b["carryover"] == 60.0
    assert b["effective_budget"] == 160.0


def test_overspend_rolls_forward_as_debt(db, user_id, account_id):
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, 3, 2025, 100.0, rollover=True)
    _spend(db, account_id, cat, 130.0, "2025-03-10")        # 30 over
    db.upsert_budget(user_id, cat, 4, 2025, 100.0, rollover=True)
    b = _budget(db, user_id, cat, 4, 2025)
    assert b["carryover"] == -30.0
    assert b["effective_budget"] == 70.0


def test_carryover_accumulates_across_streak(db, user_id, account_id):
    cat = _expense_category(db)
    # Jan: 100 budget, spend 20 -> 80 left
    db.upsert_budget(user_id, cat, 1, 2025, 100.0, rollover=True)
    _spend(db, account_id, cat, 20.0, "2025-01-10")
    # Feb: 100 budget (+80 carried = 180), spend 50 -> 130 left
    db.upsert_budget(user_id, cat, 2, 2025, 100.0, rollover=True)
    _spend(db, account_id, cat, 50.0, "2025-02-10")
    # Mar: carry-in should be 130
    db.upsert_budget(user_id, cat, 3, 2025, 100.0, rollover=True)
    b = _budget(db, user_id, cat, 3, 2025)
    assert b["carryover"] == 130.0
    assert b["effective_budget"] == 230.0


def test_streak_stops_at_non_rollover_month(db, user_id, account_id):
    cat = _expense_category(db)
    # Prior month exists but rollover is OFF -> nothing carries in
    db.upsert_budget(user_id, cat, 3, 2025, 100.0, rollover=False)
    _spend(db, account_id, cat, 10.0, "2025-03-10")
    db.upsert_budget(user_id, cat, 4, 2025, 100.0, rollover=True)
    b = _budget(db, user_id, cat, 4, 2025)
    assert b["carryover"] == 0.0
    assert b["effective_budget"] == 100.0


def test_alerts_use_effective_budget(db, user_id, account_id):
    cat = _expense_category(db)
    # Prior underspend gives +80 room; current 100 base -> 180 effective.
    db.upsert_budget(user_id, cat, 3, 2025, 100.0, rollover=True)
    _spend(db, account_id, cat, 20.0, "2025-03-10")
    db.upsert_budget(user_id, cat, 4, 2025, 100.0, rollover=True)
    _spend(db, account_id, cat, 120.0, "2025-04-10")        # 120/180 = 67%
    alerts = db.get_budget_alerts(user_id, 4, 2025)
    assert alerts == []                                     # under 90% of effective


def test_rollover_overspend_that_wipes_room_still_alerts(db, user_id, account_id):
    # Heavy prior overspend carries a big negative, dropping this month's
    # effective budget to <= 0. It must still surface as an alert (the worst
    # case), not be silently skipped like an unset budget.
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, 3, 2025, 100.0, rollover=True)
    _spend(db, account_id, cat, 300.0, "2025-03-10")        # 200 over -> carry -200
    db.upsert_budget(user_id, cat, 4, 2025, 100.0, rollover=True)
    b = _budget(db, user_id, cat, 4, 2025)
    assert b["effective_budget"] <= 0                       # room wiped out
    alerts = db.get_budget_alerts(user_id, 4, 2025)
    assert [a["category_id"] for a in alerts] == [cat]
    assert alerts[0]["over"] is True


def test_copy_last_month_preserves_rollover_flag(db, user_id, account_id):
    cat = _expense_category(db)
    db.upsert_budget(user_id, cat, 3, 2025, 100.0, rollover=True)
    db.copy_budgets(user_id, 3, 2025, 4, 2025)
    b = _budget(db, user_id, cat, 4, 2025)
    assert b["rollover"] == 1
