"""
services/debt_service.py
Debt payoff planner — snowball and avalanche strategies.

Pure, DB-free simulation so it's easy to test: feed it plain debt dicts
({"id", "name", "balance", "apr", "min_payment"}) and it walks month by month,
accruing interest, paying minimums, then funnelling every spare dollar at one
target debt chosen by the strategy:

    avalanche — highest APR first  (mathematically cheapest)
    snowball  — smallest balance first  (fastest first win, most motivating)

The total monthly payment is held constant (sum of the original minimums plus
any extra): as each debt is cleared its minimum rolls onto the next target —
this "snowball" of freed payments is what drives the payoff.
"""

from datetime import date
from dateutil.relativedelta import relativedelta  # type: ignore[import]

STRATEGIES = ("avalanche", "snowball")

# Safety cap: if the constant monthly payment can't out-run the interest, the
# balance never clears. We stop here and report the plan as not feasible rather
# than loop forever.
_MAX_MONTHS = 1200  # 100 years


def _order(debts: list[dict], strategy: str) -> list[dict]:
    """Order active debts by which one soaks up the spare payment first."""
    if strategy == "snowball":
        return sorted(debts, key=lambda d: (d["balance"], -d["apr"]))
    # avalanche (default): attack the most expensive interest rate first
    return sorted(debts, key=lambda d: (-d["apr"], d["balance"]))


def plan(
    debts: list[dict],
    extra_payment: float = 0.0,
    strategy: str = "avalanche",
    start: date | None = None,
) -> dict:
    """Simulate paying off ``debts`` under ``strategy``.

    ``extra_payment`` is added on top of the summed minimums to form a constant
    monthly budget. Returns a dict:

        strategy        — the strategy used
        start_balance   — total owed today
        months          — months until debt-free (== _MAX_MONTHS if infeasible)
        debt_free_date  — date of the final payment (None if infeasible)
        total_interest  — interest paid over the whole plan
        total_paid      — principal + interest paid
        monthly_payment — the constant monthly budget
        feasible        — False if the payment can't clear the balances
        payoff_order    — [{id, name, month, interest_paid}, …] in the order
                          each debt is cleared
        schedule        — [{month, interest, balance}, …] remaining balance
                          after each month (for charting / tables)
    """
    if strategy not in STRATEGIES:
        strategy = "avalanche"
    start = start or date.today()

    active: list[dict] = []
    for d in debts:
        bal = round(float(d.get("balance", 0.0)), 2)
        if bal <= 0:
            continue
        active.append({
            "id": d.get("id"),
            "name": d.get("name", ""),
            "balance": bal,
            "apr": max(0.0, float(d.get("apr", 0.0))),
            "min_payment": max(0.0, float(d.get("min_payment", 0.0))),
            "interest_paid": 0.0,
        })

    start_balance = round(sum(d["balance"] for d in active), 2)
    monthly_payment = round(sum(d["min_payment"] for d in active) + max(0.0, extra_payment), 2)

    result = {
        "strategy": strategy,
        "start_balance": start_balance,
        "months": 0,
        "debt_free_date": None,
        "total_interest": 0.0,
        "total_paid": 0.0,
        "monthly_payment": monthly_payment,
        "feasible": True,
        "payoff_order": [],
        "schedule": [],
    }
    if not active:
        return result

    month = 0
    total_interest = 0.0
    while active:
        month += 1
        if month > _MAX_MONTHS:
            result["feasible"] = False
            break

        # 1. Accrue one month of interest on every active debt.
        month_interest = 0.0
        for d in active:
            i = round(d["balance"] * d["apr"] / 100.0 / 12.0, 2)
            d["balance"] = round(d["balance"] + i, 2)
            d["interest_paid"] = round(d["interest_paid"] + i, 2)
            month_interest += i
        total_interest = round(total_interest + month_interest, 2)

        # 2. Spend the constant monthly budget: minimums first (capped at each
        #    balance), then funnel whatever's left at the strategy's target.
        pool = monthly_payment
        for d in active:
            pay = min(d["min_payment"], d["balance"])
            d["balance"] = round(d["balance"] - pay, 2)
            pool = round(pool - pay, 2)
        for d in _order(active, strategy):
            if pool <= 0:
                break
            pay = min(pool, d["balance"])
            d["balance"] = round(d["balance"] - pay, 2)
            pool = round(pool - pay, 2)

        # 3. Retire any debt that hit zero this month.
        cleared, still = [], []
        for d in active:
            (cleared if d["balance"] <= 0.005 else still).append(d)
        for d in cleared:
            result["payoff_order"].append({
                "id": d["id"], "name": d["name"],
                "month": month, "interest_paid": round(d["interest_paid"], 2),
            })
        active = still

        result["schedule"].append({
            "month": month,
            "interest": round(month_interest, 2),
            "balance": round(sum(d["balance"] for d in active), 2),
        })

    result["total_interest"] = total_interest
    if result["feasible"]:
        result["months"] = month
        result["debt_free_date"] = start + relativedelta(months=month)
        result["total_paid"] = round(start_balance + total_interest, 2)
    else:
        result["months"] = _MAX_MONTHS
    return result


def compare(debts: list[dict], extra_payment: float = 0.0) -> dict:
    """Run both strategies plus the minimum-only baseline for savings figures.

    Returns ``{"avalanche": plan, "snowball": plan, "baseline": plan}`` where
    ``baseline`` is the avalanche plan with no extra payment. Each strategy plan
    also gets ``interest_saved`` / ``months_saved`` versus that baseline (0 when
    the baseline isn't feasible).
    """
    baseline = plan(debts, 0.0, "avalanche")
    out = {"baseline": baseline}
    for strat in STRATEGIES:
        p = plan(debts, extra_payment, strat)
        if baseline["feasible"] and p["feasible"]:
            p["interest_saved"] = round(baseline["total_interest"] - p["total_interest"], 2)
            p["months_saved"] = baseline["months"] - p["months"]
        else:
            p["interest_saved"] = 0.0
            p["months_saved"] = 0
        out[strat] = p
    return out
