"""
tests/test_quick_wins.py
Tests for the quick-win features:
- pause/resume recurring rules (is_active flag)
- get_upcoming_recurring (dashboard "upcoming bills")
- copy_budgets (copy last month's budgets)
"""

import pytest
from datetime import date, timedelta
from services.recurring_service import RecurringService


class TestPauseResumeRecurring:
    def test_new_recurring_is_active_by_default(self, db, user_id, account_id):
        db.create_recurring(user_id, "Rent", -1000.0, "Monthly", str(date.today()),
                            account_id=account_id)
        assert db.get_recurring(user_id)[0]["is_active"] == 1

    def test_paused_rule_is_not_posted(self, db, user_id, account_id):
        yesterday = str(date.today() - timedelta(days=1))
        db.create_recurring(user_id, "Rent", -1000.0, "Monthly", yesterday,
                            account_id=account_id)
        rec = db.get_recurring(user_id)[0]
        db.set_recurring_active(rec["id"], False)
        assert db.get_recurring(user_id)[0]["is_active"] == 0

        assert RecurringService(db).process_due(user_id) == 0
        assert db.get_account(account_id)["current_balance"] == pytest.approx(1000.0)

    def test_resumed_rule_posts_again(self, db, user_id, account_id):
        yesterday = str(date.today() - timedelta(days=1))
        db.create_recurring(user_id, "Rent", -1000.0, "Monthly", yesterday,
                            account_id=account_id)
        rec = db.get_recurring(user_id)[0]
        db.set_recurring_active(rec["id"], False)
        assert RecurringService(db).process_due(user_id) == 0
        db.set_recurring_active(rec["id"], True)
        assert RecurringService(db).process_due(user_id) == 1
        assert db.get_account(account_id)["current_balance"] == pytest.approx(0.0)

    def test_paused_rule_excluded_from_forecast(self, db, user_id, account_id):
        db.create_recurring(user_id, "Salary", 2000.0, "Monthly", str(date.today()),
                            account_id=account_id)
        rec = db.get_recurring(user_id)[0]
        active = RecurringService(db).forecast(user_id, months=3)["end_balance"]
        db.set_recurring_active(rec["id"], False)
        paused = RecurringService(db).forecast(user_id, months=3)["end_balance"]
        assert paused < active
        # With the only rule paused, projection equals the starting balance.
        assert paused == pytest.approx(1000.0)


class TestUpcomingRecurring:
    def test_due_soon_is_included(self, db, user_id, account_id):
        in_3_days = str(date.today() + timedelta(days=3))
        db.create_recurring(user_id, "Netflix", -15.0, "Monthly", in_3_days,
                            account_id=account_id)
        upcoming = db.get_upcoming_recurring(user_id, within_days=7)
        assert [u["name"] for u in upcoming] == ["Netflix"]

    def test_far_future_is_excluded(self, db, user_id, account_id):
        in_30_days = str(date.today() + timedelta(days=30))
        db.create_recurring(user_id, "Rent", -1000.0, "Monthly", in_30_days,
                            account_id=account_id)
        assert db.get_upcoming_recurring(user_id, within_days=7) == []

    def test_overdue_is_included(self, db, user_id, account_id):
        yesterday = str(date.today() - timedelta(days=1))
        db.create_recurring(user_id, "Late Bill", -50.0, "Monthly", yesterday,
                            account_id=account_id)
        upcoming = db.get_upcoming_recurring(user_id, within_days=7)
        assert [u["name"] for u in upcoming] == ["Late Bill"]

    def test_paused_is_excluded(self, db, user_id, account_id):
        tomorrow = str(date.today() + timedelta(days=1))
        db.create_recurring(user_id, "Gym", -40.0, "Monthly", tomorrow,
                            account_id=account_id)
        rec = db.get_recurring(user_id)[0]
        db.set_recurring_active(rec["id"], False)
        assert db.get_upcoming_recurring(user_id, within_days=7) == []

    def test_past_end_date_is_excluded(self, db, user_id, account_id):
        tomorrow = str(date.today() + timedelta(days=1))
        yesterday = str(date.today() - timedelta(days=1))
        db.create_recurring(user_id, "Ended", -10.0, "Monthly", tomorrow,
                            account_id=account_id, end_date=yesterday)
        assert db.get_upcoming_recurring(user_id, within_days=7) == []


class TestCopyBudgets:
    def _cat_ids(self, db):
        cats = db.get_categories("Expense")
        return cats[0]["id"], cats[1]["id"]

    def test_copies_all_lines_to_empty_month(self, db, user_id):
        c1, c2 = self._cat_ids(db)
        db.upsert_budget(user_id, c1, 5, 2026, 300.0)
        db.upsert_budget(user_id, c2, 5, 2026, 150.0)
        copied = db.copy_budgets(user_id, 5, 2026, 6, 2026)
        assert copied == 2
        june = {b["category_id"]: b["budget_amount"]
                for b in db.get_budgets(user_id, 6, 2026)}
        assert june == {c1: 300.0, c2: 150.0}

    def test_does_not_overwrite_existing(self, db, user_id):
        c1, c2 = self._cat_ids(db)
        db.upsert_budget(user_id, c1, 5, 2026, 300.0)
        db.upsert_budget(user_id, c2, 5, 2026, 150.0)
        db.upsert_budget(user_id, c1, 6, 2026, 999.0)   # pre-existing in June
        copied = db.copy_budgets(user_id, 5, 2026, 6, 2026)
        assert copied == 1                               # only c2 was added
        june = {b["category_id"]: b["budget_amount"]
                for b in db.get_budgets(user_id, 6, 2026)}
        assert june[c1] == 999.0                         # untouched
        assert june[c2] == 150.0

    def test_empty_source_copies_nothing(self, db, user_id):
        assert db.copy_budgets(user_id, 1, 2026, 2, 2026) == 0
