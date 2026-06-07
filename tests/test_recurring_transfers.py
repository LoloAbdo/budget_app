"""
tests/test_recurring_transfers.py
Regression tests for the recurring-transfer fix: a due recurring transfer must
create BOTH transaction legs, move money between accounts, and stay typed as a
transfer (its to_account_id must survive process_due).
"""

import pytest
from datetime import date, timedelta
from services.recurring_service import RecurringService


@pytest.fixture
def two_accounts(db, user_id):
    src = db.create_account(user_id, "Cheques", "Checking", 1000.0)
    dst = db.create_account(user_id, "Crypto", "Savings", 0.0)
    return src, dst


class TestRecurringTransfer:
    def test_transfer_moves_money_and_stays_a_transfer(self, db, user_id, two_accounts):
        src, dst = two_accounts
        yesterday = str(date.today() - timedelta(days=1))
        db.create_recurring(user_id, "Weekly Crypto", 30.0, "Weekly", yesterday,
                            category_id=None, account_id=src, to_account_id=dst)

        posted = RecurringService(db).process_due(user_id)
        assert posted == 1

        # Both legs created, balances moved
        assert db.get_account(src)["current_balance"] == pytest.approx(970.0)
        assert db.get_account(dst)["current_balance"] == pytest.approx(30.0)
        txns = db.get_transactions(user_id)
        assert len(txns) == 2
        assert all(t.get("transfer_id") is not None for t in txns)

        # The recurring row must STILL be a transfer (to_account_id preserved)
        rec = db.get_recurring(user_id)[0]
        assert rec["to_account_id"] == dst
        assert rec["next_due_date"] > yesterday

    def test_regular_recurring_still_posts_single_leg(self, db, user_id, account_id):
        yesterday = str(date.today() - timedelta(days=1))
        db.create_recurring(user_id, "Netflix", -15.0, "Monthly", yesterday,
                            category_id=None, account_id=account_id, to_account_id=None)
        posted = RecurringService(db).process_due(user_id)
        assert posted == 1
        txns = db.get_transactions(user_id)
        assert len(txns) == 1
        assert txns[0].get("transfer_id") is None
        assert db.get_account(account_id)["current_balance"] == pytest.approx(985.0)

    def test_not_due_is_skipped(self, db, user_id, two_accounts):
        src, dst = two_accounts
        tomorrow = str(date.today() + timedelta(days=1))
        db.create_recurring(user_id, "Future", 30.0, "Weekly", tomorrow,
                            category_id=None, account_id=src, to_account_id=dst)
        assert RecurringService(db).process_due(user_id) == 0
        assert db.get_account(src)["current_balance"] == pytest.approx(1000.0)
