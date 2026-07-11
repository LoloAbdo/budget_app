"""
tests/test_subscriptions.py
Tests for DatabaseManager.get_detected_subscriptions — recurring-charge
detection from transaction history.
"""

from datetime import date, timedelta


def _expense_cat(db) -> int:
    return next(c["id"] for c in db.get_categories("Expense"))


def _charge(db, account_id, cat, desc: str, amount: float, days_ago: int):
    d = (date.today() - timedelta(days=days_ago)).isoformat()
    db.create_transaction(account_id, cat, d, desc, -abs(amount))


def test_detects_monthly_subscription(db, user_id, account_id):
    cat = _expense_cat(db)
    for days in (0, 30, 60):
        _charge(db, account_id, cat, "Netflix", 15.99, days)

    subs = db.get_detected_subscriptions(user_id)
    assert len(subs) == 1
    s = subs[0]
    assert s["name"] == "Netflix"
    assert s["cadence"] == "monthly"
    assert s["amount"] == 15.99
    assert s["monthly_cost"] == 15.99
    assert s["occurrences"] == 3


def test_variable_amounts_are_not_a_subscription(db, user_id, account_id):
    cat = _expense_cat(db)
    for days, amt in ((0, 35.0), (30, 80.0), (60, 50.0)):
        _charge(db, account_id, cat, "Corner Grocery", amt, days)
    assert db.get_detected_subscriptions(user_id) == []


def test_irregular_cadence_is_not_a_subscription(db, user_id, account_id):
    cat = _expense_cat(db)
    for days in (0, 5, 65):        # gaps of 60 and 5 days — no regular rhythm
        _charge(db, account_id, cat, "Random Cafe", 12.00, days)
    assert db.get_detected_subscriptions(user_id) == []


def test_two_occurrences_is_too_few(db, user_id, account_id):
    cat = _expense_cat(db)
    for days in (0, 30):
        _charge(db, account_id, cat, "Spotify", 9.99, days)
    assert db.get_detected_subscriptions(user_id) == []


def test_weekly_cadence_and_monthly_normalization(db, user_id, account_id):
    cat = _expense_cat(db)
    for days in (0, 7, 14):
        _charge(db, account_id, cat, "Daily Gym", 10.00, days)

    subs = db.get_detected_subscriptions(user_id)
    assert len(subs) == 1
    s = subs[0]
    assert s["cadence"] == "weekly"
    # 10/week ≈ 43.33/month (10 * 52 / 12)
    assert s["monthly_cost"] == 43.33


def test_sorted_by_monthly_cost(db, user_id, account_id):
    cat = _expense_cat(db)
    for days in (0, 30, 60):
        _charge(db, account_id, cat, "Netflix", 50.00, days)   # 50/month
    for days in (0, 7, 14):
        _charge(db, account_id, cat, "Daily Gym", 10.00, days)  # ~43.33/month

    subs = db.get_detected_subscriptions(user_id)
    assert [s["name"] for s in subs] == ["Netflix", "Daily Gym"]


def test_price_increase_still_detected(db, user_id, account_id):
    """A modest price bump (within ~25%) shouldn't hide a subscription."""
    cat = _expense_cat(db)
    for days, amt in ((60, 15.99), (30, 15.99), (0, 17.99)):
        _charge(db, account_id, cat, "Netflix", amt, days)

    subs = db.get_detected_subscriptions(user_id)
    assert len(subs) == 1
    assert subs[0]["amount"] == 17.99   # latest charge is the reported amount
