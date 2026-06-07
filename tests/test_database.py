"""
tests/test_database.py
Unit tests for DatabaseManager and service layer.
Run with:  pytest tests/ -v --cov=. --cov-report=term-missing
"""

import pytest
import os
import tempfile
from datetime import date

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """Create an in-memory (temp file) DatabaseManager for each test."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from database.schema import DatabaseManager
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    mgr = DatabaseManager(path)
    yield mgr
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def user_id(db):
    """Create a test user and return their id."""
    from services.auth_service import AuthService
    auth = AuthService(db)
    ok, msg = auth.register("Test User", "test@example.com", "password123", "CAD")
    assert ok
    user = db.get_user_by_email("test@example.com")
    return user["id"]


@pytest.fixture
def account_id(db, user_id):
    """Create a test account and return its id."""
    return db.create_account(user_id, "Test Checking", "Checking", 1000.0)


@pytest.fixture
def category_id(db):
    """Return the id of the first Expense category."""
    cats = db.get_categories("Expense")
    assert cats, "Default categories should be seeded"
    return cats[0]["id"]


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuthService:
    def test_register_success(self, db):
        from services.auth_service import AuthService
        auth = AuthService(db)
        ok, msg = auth.register("Alice", "alice@test.com", "secret99")
        assert ok
        assert "success" in msg.lower()

    def test_register_duplicate_email(self, db):
        from services.auth_service import AuthService
        auth = AuthService(db)
        auth.register("Alice", "alice@test.com", "secret99")
        ok, msg = auth.register("Alice2", "alice@test.com", "another99")
        assert not ok
        assert "already exists" in msg.lower()

    def test_register_invalid_email(self, db):
        from services.auth_service import AuthService
        auth = AuthService(db)
        ok, msg = auth.register("Alice", "not-an-email", "secret99")
        assert not ok

    def test_register_short_password(self, db):
        from services.auth_service import AuthService
        auth = AuthService(db)
        ok, msg = auth.register("Alice", "alice@test.com", "abc")
        assert not ok

    def test_login_success(self, db):
        from services.auth_service import AuthService
        auth = AuthService(db)
        auth.register("Alice", "alice@test.com", "secret99")
        ok, user, msg = auth.login("alice@test.com", "secret99")
        assert ok
        assert user is not None
        assert user["email"] == "alice@test.com"

    def test_login_wrong_password(self, db):
        from services.auth_service import AuthService
        auth = AuthService(db)
        auth.register("Alice", "alice@test.com", "secret99")
        ok, user, msg = auth.login("alice@test.com", "wrong")
        assert not ok
        assert user is None

    def test_login_unknown_email(self, db):
        from services.auth_service import AuthService
        auth = AuthService(db)
        ok, user, msg = auth.login("nobody@test.com", "pass")
        assert not ok


# ── Accounts ──────────────────────────────────────────────────────────────────

class TestAccounts:
    def test_create_and_get(self, db, user_id):
        aid = db.create_account(user_id, "Savings", "Savings", 500.0)
        acct = db.get_account(aid)
        assert acct["account_name"] == "Savings"
        assert acct["current_balance"] == pytest.approx(500.0)

    def test_update(self, db, user_id):
        aid = db.create_account(user_id, "Old Name", "Cash", 0.0)
        db.update_account(aid, "New Name", "Checking", 200.0)
        acct = db.get_account(aid)
        assert acct["account_name"] == "New Name"
        assert acct["current_balance"] == pytest.approx(200.0)

    def test_delete(self, db, user_id):
        aid = db.create_account(user_id, "Temp", "Cash", 0.0)
        db.delete_account(aid)
        assert db.get_account(aid) is None

    def test_list(self, db, user_id):
        db.create_account(user_id, "A", "Checking", 0)
        db.create_account(user_id, "B", "Savings", 0)
        accounts = db.get_accounts(user_id)
        names = [a["account_name"] for a in accounts]
        assert "A" in names
        assert "B" in names


# ── Transactions ──────────────────────────────────────────────────────────────

class TestTransactions:
    def test_create_updates_balance(self, db, user_id, account_id, category_id):
        initial = db.get_account(account_id)["current_balance"]
        db.create_transaction(account_id, category_id, "2024-01-15", "Test", -50.0)
        updated = db.get_account(account_id)["current_balance"]
        assert updated == pytest.approx(initial - 50.0)

    def test_delete_reverses_balance(self, db, user_id, account_id, category_id):
        txn_id = db.create_transaction(account_id, category_id, "2024-01-15", "Test", -50.0)
        before = db.get_account(account_id)["current_balance"]
        db.delete_transaction(txn_id)
        after = db.get_account(account_id)["current_balance"]
        assert after == pytest.approx(before + 50.0)

    def test_get_transactions_filter_by_keyword(self, db, user_id, account_id):
        db.create_transaction(account_id, None, "2024-01-01", "Grocery run", -80.0)
        db.create_transaction(account_id, None, "2024-01-02", "Netflix subscription", -15.0)
        results = db.get_transactions(user_id, keyword="Netflix")
        assert len(results) == 1
        assert results[0]["description"] == "Netflix subscription"

    def test_get_transactions_filter_by_date_range(self, db, user_id, account_id):
        db.create_transaction(account_id, None, "2024-01-01", "Jan tx", -10.0)
        db.create_transaction(account_id, None, "2024-03-01", "Mar tx", -20.0)
        results = db.get_transactions(
            user_id, start_date="2024-02-01", end_date="2024-04-01"
        )
        assert len(results) == 1
        assert results[0]["description"] == "Mar tx"

    def test_update_transaction(self, db, user_id, account_id, category_id):
        txn_id = db.create_transaction(account_id, category_id, "2024-01-01", "Old", -10.0)
        db.update_transaction(txn_id, account_id, category_id, "2024-01-01", "New", -20.0, "")
        txn = db.get_transaction(txn_id)
        assert txn["description"] == "New"
        assert txn["amount"] == pytest.approx(-20.0)


# ── Budgets ───────────────────────────────────────────────────────────────────

class TestBudgets:
    def test_upsert_and_get(self, db, user_id, category_id):
        db.upsert_budget(user_id, category_id, 6, 2024, 500.0)
        budgets = db.get_budgets(user_id, 6, 2024)
        assert any(b["category_id"] == category_id and b["budget_amount"] == pytest.approx(500.0)
                   for b in budgets)

    def test_upsert_updates_existing(self, db, user_id, category_id):
        db.upsert_budget(user_id, category_id, 6, 2024, 500.0)
        db.upsert_budget(user_id, category_id, 6, 2024, 750.0)
        budgets = db.get_budgets(user_id, 6, 2024)
        match = next(b for b in budgets if b["category_id"] == category_id)
        assert match["budget_amount"] == pytest.approx(750.0)


# ── Goals ─────────────────────────────────────────────────────────────────────

class TestGoals:
    def test_create_and_list(self, db, user_id):
        db.create_goal(user_id, "Emergency Fund", 10000.0, 2000.0, "2025-12-31")
        goals = db.get_goals(user_id)
        assert any(g["goal_name"] == "Emergency Fund" for g in goals)

    def test_update_goal(self, db, user_id):
        gid = db.create_goal(user_id, "Vacation", 3000.0, 0.0, "2025-06-01")
        db.update_goal(gid, "Vacation Fund", 5000.0, 1000.0, "2025-08-01")
        goals = db.get_goals(user_id)
        g = next(x for x in goals if x["id"] == gid)
        assert g["goal_name"] == "Vacation Fund"
        assert g["target_amount"] == pytest.approx(5000.0)

    def test_delete_goal(self, db, user_id):
        gid = db.create_goal(user_id, "Temp Goal", 100.0, 0.0, "2025-01-01")
        db.delete_goal(gid)
        goals = db.get_goals(user_id)
        assert all(g["id"] != gid for g in goals)


# ── Recurring ─────────────────────────────────────────────────────────────────

class TestRecurring:
    def test_create_and_list(self, db, user_id):
        db.create_recurring(user_id, "Netflix", -15.0, "Monthly",
                            str(date.today()), None, None)
        recs = db.get_recurring(user_id)
        assert any(r["name"] == "Netflix" for r in recs)

    def test_process_due(self, db, user_id, account_id):
        from services.recurring_service import RecurringService
        svc = RecurringService(db)
        # Create a recurring that is due today
        db.create_recurring(user_id, "Rent", -1000.0, "Monthly",
                            str(date.today()), None, account_id)
        posted = svc.process_due(user_id)
        assert posted == 1
        # Next due should be advanced
        recs = db.get_recurring(user_id)
        assert recs[0]["next_due_date"] > str(date.today())


# ── Reporting ──────────────────────────────────────────────────────────────────

class TestReporting:
    def test_monthly_summary_empty(self, db, user_id):
        summary = db.get_monthly_summary(user_id, 1, 2024)
        assert summary["income"]   == pytest.approx(0.0)
        assert summary["expenses"] == pytest.approx(0.0)

    def test_monthly_summary_with_data(self, db, user_id, account_id):
        income_cat  = db.get_categories("Income")[0]["id"]
        expense_cat = db.get_categories("Expense")[0]["id"]
        db.create_transaction(account_id, income_cat,  "2024-03-01", "Salary",  3000.0)
        db.create_transaction(account_id, expense_cat, "2024-03-15", "Rent",   -1200.0)
        summary = db.get_monthly_summary(user_id, 3, 2024)
        assert summary["income"]   == pytest.approx(3000.0)
        assert summary["expenses"] == pytest.approx(1200.0)
        assert summary["savings"]  == pytest.approx(1800.0)

    def test_total_balance(self, db, user_id):
        db.create_account(user_id, "Check", "Checking", 1000.0)
        db.create_account(user_id, "Save",  "Savings",  500.0)
        bal = db.get_total_balance(user_id)
        # Previous fixture account (1000) + Check (1000) + Save (500)
        assert bal >= 1500.0


# ── Backup service ─────────────────────────────────────────────────────────────

class TestBackupService:
    def test_create_and_list(self, db, tmp_path):
        from services.backup_service import BackupService
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        svc = BackupService(db_path, str(tmp_path))
        path = svc.create_backup("test")
        assert os.path.exists(path)
        backups = svc.list_backups()
        assert len(backups) == 1
        os.unlink(db_path)

    def test_restore(self, db, tmp_path):
        from services.backup_service import BackupService
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        svc = BackupService(db_path, str(tmp_path))
        backup_path = svc.create_backup("test")
        ok = svc.restore_backup(backup_path)
        assert ok
        os.unlink(db_path)
