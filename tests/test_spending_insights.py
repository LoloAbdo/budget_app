"""
tests/test_spending_insights.py
Tests for DatabaseManager.get_spending_insights — the dashboard's
month-over-month spending anomaly/trend detection.
"""

from datetime import datetime


def _now():
    n = datetime.now()
    return n.month, n.year


def _ym(offset: int):
    """(year, month) for ``offset`` whole months before the current month."""
    n = datetime.now()
    m, y = n.month - offset, n.year
    while m <= 0:
        m += 12
        y -= 1
    return y, m


def _date(offset: int, day: int = 15) -> str:
    y, m = _ym(offset)
    return f"{y:04d}-{m:02d}-{day:02d}"


def _expense_cats(db):
    return [c["id"] for c in db.get_categories("Expense")]


def _spend(db, account_id, category_id, amount: float, offset: int):
    db.create_transaction(account_id, category_id, _date(offset), "spend", -abs(amount))


def test_no_history_no_insights(db, user_id, account_id):
    """Spending only this month (no baseline) yields nothing."""
    cat = _expense_cats(db)[0]
    _spend(db, account_id, cat, 200.0, offset=0)
    month, year = _now()
    assert db.get_spending_insights(user_id, month, year) == []


def test_category_spike_detected(db, user_id, account_id):
    cat = _expense_cats(db)[0]
    for off in (1, 2, 3):
        _spend(db, account_id, cat, 100.0, offset=off)   # baseline 100/mo
    _spend(db, account_id, cat, 200.0, offset=0)          # +100% this month

    month, year = _now()
    insights = db.get_spending_insights(user_id, month, year)
    ups = [i for i in insights if i["type"] == "category_up"]
    assert len(ups) == 1
    assert round(ups[0]["pct"]) == 100
    assert ups[0]["baseline"] == 100.0


def test_category_dip_is_positive(db, user_id, account_id):
    cat = _expense_cats(db)[0]
    for off in (1, 2, 3):
        _spend(db, account_id, cat, 100.0, offset=off)
    _spend(db, account_id, cat, 20.0, offset=0)           # -80% this month

    month, year = _now()
    insights = db.get_spending_insights(user_id, month, year)
    assert len(insights) == 1
    assert insights[0]["type"] == "category_down"
    assert round(insights[0]["pct"]) == 80


def test_overall_spending_up(db, user_id, account_id):
    """A new (baseline-less) category still shows up in the overall total."""
    cats = _expense_cats(db)
    for off in (1, 2, 3):
        _spend(db, account_id, cats[0], 100.0, offset=off)
    _spend(db, account_id, cats[0], 100.0, offset=0)      # same as baseline
    _spend(db, account_id, cats[1], 100.0, offset=0)      # extra, no baseline

    month, year = _now()
    insights = db.get_spending_insights(user_id, month, year)
    assert insights[0]["type"] == "spending_up"           # warnings rank first
    assert round(insights[0]["pct"]) == 100


def test_new_category_has_no_category_insight(db, user_id, account_id):
    """Without an established baseline a category never reads as a spike."""
    cat = _expense_cats(db)[0]
    _spend(db, account_id, cat, 500.0, offset=0)
    month, year = _now()
    insights = db.get_spending_insights(user_id, month, year)
    assert all(i["type"] != "category_up" for i in insights)


def test_capped_and_warnings_first(db, user_id, account_id):
    cats = _expense_cats(db)
    for cat in cats:
        for off in (1, 2, 3):
            _spend(db, account_id, cat, 100.0, offset=off)
        _spend(db, account_id, cat, 300.0, offset=0)      # every category spikes

    month, year = _now()
    insights = db.get_spending_insights(user_id, month, year)
    assert len(insights) <= 4
    # No positive (down) insight may appear before a warning (up) insight.
    seen_down = False
    for i in insights:
        if i["type"] in ("spending_down", "category_down"):
            seen_down = True
        elif seen_down:
            raise AssertionError("a warning appeared after a positive insight")


def test_small_swings_ignored(db, user_id, account_id):
    """A tiny, sub-threshold change produces no noise."""
    cat = _expense_cats(db)[0]
    for off in (1, 2, 3):
        _spend(db, account_id, cat, 100.0, offset=off)
    _spend(db, account_id, cat, 108.0, offset=0)          # +8%, under 35%
    month, year = _now()
    assert db.get_spending_insights(user_id, month, year) == []
