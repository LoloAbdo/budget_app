"""
scripts/seed_sample_data.py
Populates the database with realistic sample data for demonstration purposes.
Run:  python scripts/seed_sample_data.py
"""

import sys
import os
import random
from datetime import date, timedelta
from pathlib import Path

# Make root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.schema import DatabaseManager
from services.auth_service import AuthService

DB_PATH = str(Path(__file__).parent.parent / "data" / "budget.db")


def main() -> None:
    db   = DatabaseManager(DB_PATH)
    auth = AuthService(db)

    # ── Create demo user ───────────────────────────────────────────────────────
    ok, msg = auth.register("Demo User", "demo@budget.app", "demo1234", "CAD")
    if not ok:
        print(f"User already exists — continuing with existing account. ({msg})")
    user = db.get_user_by_email("demo@budget.app")
    uid  = user["id"]
    print(f"User id: {uid}")

    # ── Accounts ───────────────────────────────────────────────────────────────
    chk_id = db.create_account(uid, "Main Checking", "Checking", 3_200.0)
    sav_id = db.create_account(uid, "High-Interest Savings", "Savings", 8_500.0)
    cc_id  = db.create_account(uid, "Visa Credit Card", "Credit Card", -450.0)
    print("Accounts created.")

    # ── Category map ──────────────────────────────────────────────────────────
    cats = {c["name"]: c["id"] for c in db.get_categories()}

    # ── Transactions — last 6 months ──────────────────────────────────────────
    today = date.today()
    income_entries = [
        ("Salary",     "Employer Direct Deposit", 4_800.0),
        ("Freelance",  "Consulting invoice",       850.0),
        ("Investment", "Dividend payment",          60.0),
    ]
    expense_entries = [
        ("Rent/Mortgage",  "Monthly Rent",          -1_600.0),
        ("Groceries",      "Loblaws",                 -120.0),
        ("Groceries",      "Metro grocery",            -85.0),
        ("Gas",            "Shell",                    -65.0),
        ("Utilities",      "Hydro bill",               -90.0),
        ("Utilities",      "Internet — Rogers",        -80.0),
        ("Entertainment",  "Movie night",              -35.0),
        ("Dining Out",     "Restaurant dinner",        -55.0),
        ("Subscriptions",  "Netflix",                  -18.0),
        ("Subscriptions",  "Spotify",                  -12.0),
        ("Healthcare",     "Pharmacy",                 -30.0),
        ("Clothing",       "Shopping mall",            -95.0),
        ("Personal Care",  "Haircut",                  -45.0),
        ("Insurance",      "Car insurance",           -160.0),
        ("Gas",            "Petro-Canada",             -55.0),
        ("Dining Out",     "Coffee & lunch",           -22.0),
    ]

    tx_count = 0
    for months_back in range(6):
        ref = today.replace(day=1) - timedelta(days=months_back * 30)
        # Income on 1st of month
        for cat_name, desc, amount in income_entries:
            cat_id = cats.get(cat_name)
            acct   = chk_id if "Salary" in desc else sav_id
            db.create_transaction(acct, cat_id, str(ref), desc, amount)
            tx_count += 1
        # Expenses scattered through the month
        for cat_name, desc, amount in expense_entries:
            cat_id = cats.get(cat_name)
            day    = random.randint(1, 28)
            d      = ref.replace(day=day)
            acct   = cc_id if "Subscriptions" in cat_name else chk_id
            jitter = random.uniform(0.85, 1.15)
            db.create_transaction(acct, cat_id, str(d), desc, round(amount * jitter, 2))
            tx_count += 1
    print(f"Transactions created: {tx_count}")

    # ── Budgets ────────────────────────────────────────────────────────────────
    budget_amounts = {
        "Rent/Mortgage":  1_650.0,
        "Groceries":        500.0,
        "Gas":              150.0,
        "Utilities":        200.0,
        "Entertainment":    100.0,
        "Dining Out":       200.0,
        "Subscriptions":     60.0,
        "Healthcare":       100.0,
        "Clothing":         150.0,
        "Insurance":        170.0,
    }
    for cat_name, amount in budget_amounts.items():
        cat_id = cats.get(cat_name)
        if cat_id:
            db.upsert_budget(uid, cat_id, today.month, today.year, amount)
    print("Budgets created.")

    # ── Goals ──────────────────────────────────────────────────────────────────
    db.create_goal(uid, "Emergency Fund",   20_000.0,  8_500.0, "2025-12-31")
    db.create_goal(uid, "Vacation — Japan",  5_000.0,  1_200.0, "2025-08-01")
    db.create_goal(uid, "New Laptop",        2_500.0,    750.0, "2025-03-01")
    db.create_goal(uid, "House Down Payment",80_000.0, 12_000.0, "2030-01-01")
    print("Goals created.")

    # ── Recurring ─────────────────────────────────────────────────────────────
    db.create_recurring(uid, "Netflix",        -18.0, "Monthly",   str(today.replace(day=5)),
                        cats.get("Subscriptions"), cc_id)
    db.create_recurring(uid, "Spotify",        -12.0, "Monthly",   str(today.replace(day=10)),
                        cats.get("Subscriptions"), cc_id)
    db.create_recurring(uid, "Car Insurance", -160.0, "Monthly",   str(today.replace(day=1)),
                        cats.get("Insurance"), chk_id)
    db.create_recurring(uid, "Gym Membership", -45.0, "Monthly",   str(today.replace(day=15)),
                        cats.get("Personal Care"), chk_id)
    print("Recurring transactions created.")

    print("\n[OK] Sample data seeding complete!")
    print(f"   Login with:  demo@budget.app / demo1234")
    print(f"   Database:    {DB_PATH}")


if __name__ == "__main__":
    main()
