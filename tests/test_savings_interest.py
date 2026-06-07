"""
tests/test_savings_interest.py
Tests for the savings / interest feature (auto-detected interest entries and
the per-account interest summary).
"""

import pytest
from datetime import date


class TestInterestCategory:
    def test_interest_category_exists(self, db):
        cat = db.get_category_by_name("Interest")
        assert cat is not None
        assert cat["type"] == "Income"
        assert db.get_interest_category_id() == cat["id"]


class TestSavingsAccounts:
    def test_only_savings_returned(self, db, user_id):
        db.create_account(user_id, "Chk", "Checking", 0.0)
        s1 = db.create_account(user_id, "TFSA", "Savings", 100.0)
        s2 = db.create_account(user_id, "Crypto", "Savings", 50.0)
        ids = {a["id"] for a in db.get_savings_accounts(user_id)}
        assert ids == {s1, s2}


class TestRecordInterest:
    def test_record_interest_updates_balance_and_summary(self, db, user_id, savings_id):
        # Simulate the "1000 + 4x100 transfers, real balance 1500 -> +100 interest" flow.
        before = db.get_account(savings_id)["current_balance"]   # 1000
        db.record_interest(savings_id, 100.0, date.today().isoformat())
        after = db.get_account(savings_id)["current_balance"]
        assert after == pytest.approx(before + 100.0)

        m, y = date.today().month, date.today().year
        summ = {s["id"]: s for s in db.get_interest_summary(user_id, m, y)}
        row = summ[savings_id]
        assert row["interest_month"] == pytest.approx(100.0)
        assert row["interest_year"] == pytest.approx(100.0)
        assert row["interest_total"] == pytest.approx(100.0)
        assert row["current_balance"] == pytest.approx(after)

    def test_loss_is_negative(self, db, user_id, savings_id):
        db.record_interest(savings_id, -25.0, date.today().isoformat())
        m, y = date.today().month, date.today().year
        row = {s["id"]: s for s in db.get_interest_summary(user_id, m, y)}[savings_id]
        assert row["interest_total"] == pytest.approx(-25.0)
        assert db.get_account(savings_id)["current_balance"] == pytest.approx(975.0)

    def test_interest_entries_history(self, db, user_id, savings_id):
        db.record_interest(savings_id, 10.0, "2026-01-15")
        db.record_interest(savings_id, 20.0, "2026-02-15")
        entries = db.get_interest_entries(user_id)
        assert len(entries) == 2
        # Most recent first
        assert entries[0]["amount"] == pytest.approx(20.0)
        assert entries[0]["account_name"] == "Test Savings"

    def test_monthly_breakdown(self, db, user_id, savings_id):
        db.record_interest(savings_id, 10.0, "2026-01-15")
        db.record_interest(savings_id, 30.0, "2026-03-10")
        monthly = {int(r["month"]): r["interest"] for r in db.get_interest_monthly(user_id, 2026)}
        assert monthly.get(1) == pytest.approx(10.0)
        assert monthly.get(3) == pytest.approx(30.0)
        assert 2 not in monthly  # no February interest

    def test_summary_excludes_non_savings(self, db, user_id, account_id, savings_id):
        # Interest recorded on a Checking account shouldn't appear in the savings summary
        db.record_interest(account_id, 999.0, date.today().isoformat())
        db.record_interest(savings_id, 50.0, date.today().isoformat())
        m, y = date.today().month, date.today().year
        rows = db.get_interest_summary(user_id, m, y)
        ids = {r["id"] for r in rows}
        assert account_id not in ids          # checking account excluded
        assert savings_id in ids
