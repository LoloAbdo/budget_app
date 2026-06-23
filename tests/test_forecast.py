"""
tests/test_forecast.py
Covers RecurringService.forecast(): the cash-flow projection that drives the
Forecast panel. Verifies it starts at the current balance, applies recurring
income/expenses forward, respects the horizon, and ignores transfers.
"""

from datetime import date

from dateutil.relativedelta import relativedelta

import pytest

from services.recurring_service import RecurringService


@pytest.fixture
def svc(db):
    return RecurringService(db)


def test_empty_when_no_recurring(svc, db, user_id, account_id):
    data = svc.forecast(user_id, months=3)
    assert data["events"] == []
    # With no recurring activity, the projection is flat at today's balance.
    assert data["start_balance"] == data["end_balance"] == 1000.0


def test_monthly_expense_reduces_balance(svc, db, user_id, account_id):
    nxt = (date.today() + relativedelta(days=5)).isoformat()
    db.create_recurring(user_id, "Rent", -200.0, "Monthly", nxt, account_id=account_id)
    data = svc.forecast(user_id, months=3)
    # Next due + 2 more monthly occurrences inside a 3-month window = 3 hits.
    assert len(data["events"]) == 3
    assert data["start_balance"] == 1000.0
    assert data["end_balance"] == pytest.approx(1000.0 - 600.0)
    # Running balance is monotonically applied in chronological order.
    assert [e["balance"] for e in data["events"]] == pytest.approx([800.0, 600.0, 400.0])


def test_income_increases_balance(svc, db, user_id, account_id):
    nxt = (date.today() + relativedelta(days=1)).isoformat()
    db.create_recurring(user_id, "Salary", 500.0, "Monthly", nxt, account_id=account_id)
    data = svc.forecast(user_id, months=2)
    assert data["end_balance"] > data["start_balance"]
    assert all(e["amount"] == 500.0 for e in data["events"])


def test_horizon_limits_occurrences(svc, db, user_id, account_id):
    nxt = (date.today() + relativedelta(days=2)).isoformat()
    db.create_recurring(user_id, "Sub", -10.0, "Monthly", nxt, account_id=account_id)
    short = svc.forecast(user_id, months=1)
    long = svc.forecast(user_id, months=12)
    assert len(long["events"]) > len(short["events"])


def test_transfers_excluded(svc, db, user_id, account_id, savings_id):
    nxt = (date.today() + relativedelta(days=3)).isoformat()
    # A recurring transfer between the user's own accounts: net worth unchanged.
    db.create_recurring(
        user_id, "To Savings", 100.0, "Monthly", nxt,
        account_id=account_id, to_account_id=savings_id,
    )
    data = svc.forecast(user_id, months=6)
    assert data["events"] == []
    assert data["start_balance"] == data["end_balance"]
