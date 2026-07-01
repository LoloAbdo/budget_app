"""
tests/test_recurring_end_date.py
Tests for the optional end date on recurring transactions: once the next
occurrence falls past the end date, the schedule stops posting (and the
forecast stops projecting it), while end_date round-trips through the DB.
"""

import pytest
from datetime import date, timedelta
from services.recurring_service import RecurringService


class TestRecurringEndDateStorage:
    def test_end_date_round_trips(self, db, user_id, account_id):
        end = str(date.today() + timedelta(days=90))
        db.create_recurring(user_id, "Gym", -40.0, "Monthly", str(date.today()),
                            category_id=None, account_id=account_id,
                            to_account_id=None, end_date=end)
        rec = db.get_recurring(user_id)[0]
        assert rec["end_date"] == end

    def test_end_date_defaults_to_none(self, db, user_id, account_id):
        db.create_recurring(user_id, "Salary", 2000.0, "Monthly", str(date.today()),
                            category_id=None, account_id=account_id)
        assert db.get_recurring(user_id)[0]["end_date"] is None

    def test_update_can_clear_and_set_end_date(self, db, user_id, account_id):
        end = str(date.today() + timedelta(days=30))
        db.create_recurring(user_id, "Gym", -40.0, "Monthly", str(date.today()),
                            category_id=None, account_id=account_id,
                            to_account_id=None, end_date=end)
        rec = db.get_recurring(user_id)[0]
        # Clear it
        db.update_recurring(rec["id"], rec["name"], rec["amount"], rec["frequency"],
                            rec["next_due_date"], rec["category_id"],
                            rec["account_id"], None, None)
        assert db.get_recurring(user_id)[0]["end_date"] is None


class TestRecurringEndDateProcessing:
    def test_due_past_end_date_is_not_posted(self, db, user_id, account_id):
        # Due yesterday, but the schedule ended a week ago — must not post.
        yesterday = str(date.today() - timedelta(days=1))
        last_week = str(date.today() - timedelta(days=7))
        db.create_recurring(user_id, "Old Sub", -10.0, "Monthly", yesterday,
                            category_id=None, account_id=account_id,
                            to_account_id=None, end_date=last_week)
        assert RecurringService(db).process_due(user_id) == 0
        assert db.get_account(account_id)["current_balance"] == pytest.approx(1000.0)

    def test_due_within_end_date_posts(self, db, user_id, account_id):
        yesterday = str(date.today() - timedelta(days=1))
        next_year = str(date.today() + timedelta(days=365))
        db.create_recurring(user_id, "Active Sub", -10.0, "Monthly", yesterday,
                            category_id=None, account_id=account_id,
                            to_account_id=None, end_date=next_year)
        assert RecurringService(db).process_due(user_id) == 1
        assert db.get_account(account_id)["current_balance"] == pytest.approx(990.0)

    def test_stops_after_final_occurrence(self, db, user_id, account_id):
        """A weekly item ending today posts once, then stops on the next run."""
        last_week = str(date.today() - timedelta(days=7))
        today = str(date.today())
        db.create_recurring(user_id, "Ending Weekly", -5.0, "Weekly", last_week,
                            category_id=None, account_id=account_id,
                            to_account_id=None, end_date=today)
        svc = RecurringService(db)
        # First run: due last week (<= end) posts and advances to today.
        assert svc.process_due(user_id) == 1
        rec = db.get_recurring(user_id)[0]
        assert rec["end_date"] == today        # end date preserved on advance
        # Today is still <= end, so a second run posts again, advancing past end.
        assert svc.process_due(user_id) == 1
        # Now next due is past the end date — no further posts ever.
        assert svc.process_due(user_id) == 0
        assert db.get_account(account_id)["current_balance"] == pytest.approx(990.0)


class TestForecastRespectsEndDate:
    def test_forecast_stops_at_end_date(self, db, user_id, account_id):
        # Monthly income that ends in ~1 month should contribute at most once
        # to a 6-month forecast.
        today = date.today()
        end = str(today + timedelta(days=31))
        db.create_recurring(user_id, "Short Gig", 100.0, "Monthly", str(today),
                            category_id=None, account_id=account_id,
                            to_account_id=None, end_date=end)
        result = RecurringService(db).forecast(user_id, months=6)
        gig_events = [e for e in result["events"] if e["name"] == "Short Gig"]
        end_dt = date.fromisoformat(end)
        assert len(gig_events) <= 2
        assert all(e["date"] <= end_dt for e in gig_events)
        # End balance only reflects the occurrences that fell on/before the end.
        assert result["end_balance"] == pytest.approx(
            result["start_balance"] + 100.0 * len(gig_events)
        )
