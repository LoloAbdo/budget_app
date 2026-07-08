"""
tests/test_debt_service.py
Debt payoff planner: strategy ordering, interest, feasibility, savings, and
the DatabaseManager CRUD backing it.
"""

import math

from services import debt_service


def _debt(name, balance, apr, min_payment, id=None):
    return {"id": id, "name": name, "balance": balance, "apr": apr, "min_payment": min_payment}


def test_empty_plan_is_trivially_feasible():
    r = debt_service.plan([])
    assert r["feasible"] is True
    assert r["months"] == 0
    assert r["payoff_order"] == []
    assert r["total_interest"] == 0.0


def test_zero_interest_single_debt_months():
    # 1000 owed, 100/mo, no interest -> exactly 10 months, no interest.
    r = debt_service.plan([_debt("Loan", 1000, 0.0, 100)])
    assert r["months"] == 10
    assert r["total_interest"] == 0.0
    assert r["total_paid"] == 1000.0


def test_avalanche_clears_highest_apr_first():
    debts = [
        _debt("HighAPR", 1000, 20.0, 25, id=1),
        _debt("LowAPR",   500,  5.0, 25, id=2),
    ]
    r = debt_service.plan(debts, extra_payment=200, strategy="avalanche")
    assert r["feasible"]
    assert r["payoff_order"][0]["name"] == "HighAPR"


def test_snowball_clears_smallest_balance_first():
    debts = [
        _debt("HighAPR", 1000, 20.0, 25, id=1),
        _debt("Small",    500,  5.0, 25, id=2),
    ]
    r = debt_service.plan(debts, extra_payment=200, strategy="snowball")
    assert r["feasible"]
    assert r["payoff_order"][0]["name"] == "Small"


def test_total_paid_equals_principal_plus_interest():
    debts = [_debt("Card", 2000, 18.0, 60)]
    r = debt_service.plan(debts, extra_payment=100, strategy="avalanche")
    assert r["feasible"]
    assert math.isclose(
        r["total_paid"], r["start_balance"] + r["total_interest"], abs_tol=0.05
    )


def test_avalanche_never_costs_more_interest_than_snowball():
    debts = [
        _debt("A", 3000, 24.0, 60, id=1),
        _debt("B", 1000,  8.0, 30, id=2),
    ]
    aval = debt_service.plan(debts, 200, "avalanche")
    snow = debt_service.plan(debts, 200, "snowball")
    assert aval["total_interest"] <= snow["total_interest"] + 0.01


def test_extra_payment_saves_time_and_interest():
    debts = [_debt("Card", 5000, 19.99, 150)]
    cmp = debt_service.compare(debts, extra_payment=200)
    aval = cmp["avalanche"]
    assert aval["feasible"]
    assert aval["interest_saved"] > 0
    assert aval["months_saved"] > 0


def test_payment_below_interest_is_infeasible():
    # 30% APR on 1000 ~ 25/mo interest; a 1/mo minimum can never win.
    r = debt_service.plan([_debt("Trap", 1000, 30.0, 1)], extra_payment=0)
    assert r["feasible"] is False
    assert r["debt_free_date"] is None
    assert r["months"] == debt_service._MAX_MONTHS


def test_debt_crud_roundtrip(db, user_id):
    did = db.create_debt(user_id, "Visa", 1500.0, 19.99, 50.0)
    debts = db.get_debts(user_id)
    assert len(debts) == 1
    assert debts[0]["name"] == "Visa"
    assert debts[0]["balance"] == 1500.0
    assert debts[0]["apr"] == 19.99

    db.update_debt(did, "Visa Gold", 1200.0, 21.0, 60.0)
    d = db.get_debts(user_id)[0]
    assert d["name"] == "Visa Gold"
    assert d["balance"] == 1200.0

    db.delete_debt(did)
    assert db.get_debts(user_id) == []


def test_debt_money_is_rounded_to_cents(db, user_id):
    db.create_debt(user_id, "Rounding", 100.129, 5.0, 10.005)
    d = db.get_debts(user_id)[0]
    assert d["balance"] == 100.13
    assert d["min_payment"] == 10.01
