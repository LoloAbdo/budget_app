"""
tests/test_category_rules.py
Auto-categorization rules: CRUD, matching semantics, and CSV import hookup.
"""

import csv

import pytest

from services.import_export_service import ImportExportService


@pytest.fixture
def groceries_id(db):
    return next(c["id"] for c in db.get_categories() if c["name"] == "Groceries")


@pytest.fixture
def subscriptions_id(db):
    return next(c["id"] for c in db.get_categories() if c["name"] == "Subscriptions")


class TestRuleCrud:
    def test_create_and_list(self, db, user_id, groceries_id):
        rid = db.create_category_rule(user_id, "COSTCO", groceries_id)
        rules = db.get_category_rules(user_id)
        assert len(rules) == 1
        assert rules[0]["id"] == rid
        assert rules[0]["pattern"] == "COSTCO"
        assert rules[0]["category_name"] == "Groceries"

    def test_update(self, db, user_id, groceries_id, subscriptions_id):
        rid = db.create_category_rule(user_id, "COSTCO", groceries_id)
        db.update_category_rule(rid, "NETFLIX", subscriptions_id, user_id=user_id)
        rule = db.get_category_rules(user_id)[0]
        assert rule["pattern"] == "NETFLIX"
        assert rule["category_id"] == subscriptions_id

    def test_delete(self, db, user_id, groceries_id):
        rid = db.create_category_rule(user_id, "COSTCO", groceries_id)
        db.delete_category_rule(rid, user_id=user_id)
        assert db.get_category_rules(user_id) == []

    def test_deleting_category_cascades(self, db, user_id):
        cid = db.create_category("Streaming", "Expense", "#123456")
        db.create_category_rule(user_id, "NETFLIX", cid)
        db.delete_category(cid)
        assert db.get_category_rules(user_id) == []

    def test_pattern_is_trimmed(self, db, user_id, groceries_id):
        db.create_category_rule(user_id, "  COSTCO  ", groceries_id)
        assert db.get_category_rules(user_id)[0]["pattern"] == "COSTCO"


class TestMatching:
    def test_case_insensitive_substring(self, db, user_id, subscriptions_id):
        db.create_category_rule(user_id, "netflix", subscriptions_id)
        assert db.match_category_rule(user_id, "NETFLIX.COM 123-456") == subscriptions_id
        assert db.match_category_rule(user_id, "Payment to NetFlix Inc") == subscriptions_id

    def test_no_match_returns_none(self, db, user_id, subscriptions_id):
        db.create_category_rule(user_id, "NETFLIX", subscriptions_id)
        assert db.match_category_rule(user_id, "SPOTIFY") is None
        assert db.match_category_rule(user_id, "") is None
        assert db.match_category_rule(user_id, "   ") is None

    def test_longest_pattern_wins(self, db, user_id, groceries_id, subscriptions_id):
        db.create_category_rule(user_id, "AMAZON", groceries_id)
        db.create_category_rule(user_id, "AMAZON PRIME", subscriptions_id)
        assert db.match_category_rule(user_id, "AMAZON PRIME VIDEO") == subscriptions_id
        assert db.match_category_rule(user_id, "AMAZON MARKETPLACE") == groceries_id

    def test_tie_goes_to_oldest_rule(self, db, user_id, groceries_id, subscriptions_id):
        db.create_category_rule(user_id, "SHOP", groceries_id)       # older
        db.create_category_rule(user_id, "STOP", subscriptions_id)   # same length
        assert db.match_category_rule(user_id, "SHOP & STOP") == groceries_id

    def test_rules_are_per_user(self, db, user_id, subscriptions_id):
        from services.auth_service import AuthService
        AuthService(db).register("Other", "other@example.com", "password123")
        other_id = db.get_user_by_email("other@example.com")["id"]
        db.create_category_rule(user_id, "NETFLIX", subscriptions_id)
        assert db.match_category_rule(other_id, "NETFLIX") is None


class TestImportAppliesRules:
    def _write_csv(self, path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["date", "description", "amount", "category", "account"]
            )
            writer.writeheader()
            writer.writerows(rows)

    def test_uncategorized_rows_get_rule_category(
        self, db, user_id, account_id, subscriptions_id, tmp_path
    ):
        db.create_category_rule(user_id, "NETFLIX", subscriptions_id)
        src = tmp_path / "import.csv"
        self._write_csv(src, [
            {"date": "2026-07-01", "description": "NETFLIX.COM", "amount": "-15.99",
             "category": "", "account": "Test Checking"},
            {"date": "2026-07-02", "description": "Mystery shop", "amount": "-5.00",
             "category": "", "account": "Test Checking"},
        ])
        imported, errors = ImportExportService(db).import_csv(user_id, str(src))
        assert imported == 2 and errors == []

        txns = {t["description"]: t for t in db.get_transactions(user_id)}
        assert txns["NETFLIX.COM"]["category_id"] == subscriptions_id
        assert txns["Mystery shop"]["category_id"] is None

    def test_explicit_category_beats_rule(
        self, db, user_id, account_id, groceries_id, subscriptions_id, tmp_path
    ):
        db.create_category_rule(user_id, "NETFLIX", subscriptions_id)
        src = tmp_path / "import.csv"
        self._write_csv(src, [
            {"date": "2026-07-01", "description": "NETFLIX.COM", "amount": "-15.99",
             "category": "Groceries", "account": "Test Checking"},
        ])
        ImportExportService(db).import_csv(user_id, str(src))
        txn = db.get_transactions(user_id)[0]
        assert txn["category_id"] == groceries_id
