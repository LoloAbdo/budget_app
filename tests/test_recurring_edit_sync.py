"""
tests/test_recurring_edit_sync.py
When a transaction created from a recurring rule is edited, the user can opt to
push the same changes back to the rule. These tests cover the DB layer that
backs that flow: get_recurring_by_id and the field-preserving update the
transaction dialog performs (name/amount/category/account change; frequency,
next due date, end date and transfer link preserved).
"""

from datetime import date, timedelta


def _make_rule(db, user_id, account_id, cat_id=None):
    end = str(date.today() + timedelta(days=90))
    rid = db.create_recurring(
        user_id, "Netflix", -15.99, "Monthly", str(date.today()),
        category_id=cat_id, account_id=account_id, to_account_id=None, end_date=end,
    )
    return rid, end


class TestGetRecurringById:
    def test_returns_the_rule(self, db, user_id, account_id):
        rid, end = _make_rule(db, user_id, account_id)
        rule = db.get_recurring_by_id(rid)
        assert rule is not None
        assert rule["id"] == rid
        assert rule["name"] == "Netflix"
        assert rule["end_date"] == end
        assert rule["account_name"] == "Test Checking"

    def test_missing_id_returns_none(self, db):
        assert db.get_recurring_by_id(999) is None


class TestEditSyncMapping:
    def test_linked_transaction_flags_recurring(self, db, user_id, account_id):
        rid, _ = _make_rule(db, user_id, account_id)
        txn_id = db.create_transaction(
            account_id, None, str(date.today()), "Netflix", -15.99,
            recurring_id=rid,
        )
        txn = db.get_transaction(txn_id)
        assert txn["recurring_id"] == rid

    def test_pushes_edits_and_preserves_schedule(self, db, user_id, account_id):
        cats = db.get_categories()
        cat_id = cats[0]["id"]
        rid, end = _make_rule(db, user_id, account_id)
        rule = db.get_recurring_by_id(rid)

        # Simulate the dialog: new name/amount/category, schedule fields kept.
        db.update_recurring(
            rid, "Netflix Premium", -19.99, rule["frequency"], rule["next_due_date"],
            cat_id, rule["account_id"], rule.get("to_account_id"), rule.get("end_date"),
        )

        updated = db.get_recurring_by_id(rid)
        assert updated["name"] == "Netflix Premium"
        assert updated["amount"] == -19.99
        assert updated["category_id"] == cat_id
        # Schedule untouched.
        assert updated["frequency"] == rule["frequency"]
        assert updated["next_due_date"] == rule["next_due_date"]
        assert updated["end_date"] == end
