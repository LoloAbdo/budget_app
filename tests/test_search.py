"""
tests/test_search.py
Global transaction search (DatabaseManager.search_transactions).
"""


def _seed(db, account_id):
    db.create_transaction(account_id, None, "2026-01-05", "NETFLIX.COM", -15.99, "monthly plan")
    db.create_transaction(account_id, None, "2026-02-10", "Grocery run", -82.45, "")
    db.create_transaction(account_id, None, "2026-03-15", "Refund", 15.99, "netflix refund")
    db.create_transaction(account_id, None, "2026-04-20", "Salary", 3000.00, "")


class TestSearchTransactions:
    def test_text_matches_description_case_insensitive(self, db, user_id, account_id):
        _seed(db, account_id)
        rows = db.search_transactions(user_id, "netflix")
        # Hits both the NETFLIX.COM description and the "netflix refund" note.
        assert {r["description"] for r in rows} == {"NETFLIX.COM", "Refund"}

    def test_text_matches_notes(self, db, user_id, account_id):
        _seed(db, account_id)
        rows = db.search_transactions(user_id, "monthly plan")
        assert [r["description"] for r in rows] == ["NETFLIX.COM"]

    def test_numeric_query_matches_amount_ignoring_sign(self, db, user_id, account_id):
        _seed(db, account_id)
        rows = db.search_transactions(user_id, "15.99")
        assert {r["description"] for r in rows} == {"NETFLIX.COM", "Refund"}

    def test_numeric_query_accepts_comma_decimal(self, db, user_id, account_id):
        _seed(db, account_id)
        rows = db.search_transactions(user_id, "15,99")
        assert len(rows) == 2

    def test_empty_query_returns_nothing(self, db, user_id, account_id):
        _seed(db, account_id)
        assert db.search_transactions(user_id, "") == []
        assert db.search_transactions(user_id, "   ") == []

    def test_no_match(self, db, user_id, account_id):
        _seed(db, account_id)
        assert db.search_transactions(user_id, "SPOTIFY") == []
        assert db.search_transactions(user_id, "999.99") == []

    def test_limit_and_order(self, db, user_id, account_id):
        for i in range(1, 6):
            db.create_transaction(account_id, None, f"2026-01-0{i}", f"COFFEE {i}", -3.00, "")
        rows = db.search_transactions(user_id, "COFFEE", limit=3)
        assert len(rows) == 3
        assert rows[0]["description"] == "COFFEE 5"   # newest first

    def test_scoped_to_user(self, db, user_id, account_id):
        from services.auth_service import AuthService
        _seed(db, account_id)
        AuthService(db).register("Other", "other@example.com", "password123")
        other_id = db.get_user_by_email("other@example.com")["id"]
        assert db.search_transactions(other_id, "NETFLIX") == []
