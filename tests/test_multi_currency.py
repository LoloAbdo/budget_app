"""
tests/test_multi_currency.py
Multi-currency accounts (v2.0.0): per-account currency, FX rate cache,
home-currency conversion of aggregates, and cross-currency transfers.
"""

import sqlite3

import pytest

from database.schema import DatabaseManager


# ── Schema / migration ────────────────────────────────────────────────────────

def test_accounts_have_currency_column(db, user_id):
    aid = db.create_account(user_id, "Plain", "Checking", 100.0)
    acct = db.get_account(aid)
    assert acct["currency"] == "CAD"   # defaults to the owner's home currency


def test_create_account_with_explicit_currency(db, user_id):
    aid = db.create_account(user_id, "US Account", "Savings", 50.0, "usd")
    assert db.get_account(aid)["currency"] == "USD"   # normalized to uppercase


def test_migration_backfills_currency_from_user(tmp_path):
    """Upgrading a pre-2.0 database gives every account its owner's currency."""
    path = str(tmp_path / "old.db")
    mgr = DatabaseManager(path)
    from services.auth_service import AuthService
    AuthService(mgr).register("Euro User", "eu@example.com", "password123", "EUR")
    uid = mgr.get_user_by_email("eu@example.com")["id"]
    aid = mgr.create_account(uid, "Konto", "Checking", 10.0)
    mgr._conn().close()
    mgr._local.conn = None

    # Simulate the pre-2.0 schema: no accounts.currency, no fx_rates table.
    raw = sqlite3.connect(path)
    raw.execute("ALTER TABLE accounts DROP COLUMN currency")
    raw.execute("DROP TABLE fx_rates")
    raw.commit()
    raw.close()

    upgraded = DatabaseManager(path)
    assert upgraded.get_account(aid)["currency"] == "EUR"
    assert upgraded.get_fx_rates() == []   # table recreated
    upgraded._conn().close()


# ── FX cache ──────────────────────────────────────────────────────────────────

def test_set_fx_rate_stores_both_directions(db):
    db.set_fx_rate("USD", "CAD", 1.25)
    assert db.get_cached_fx_rate("USD", "CAD")["rate"] == 1.25
    assert db.get_cached_fx_rate("CAD", "USD")["rate"] == pytest.approx(0.8)


def test_same_currency_rate_is_identity(db):
    assert db.get_cached_fx_rate("CAD", "CAD")["rate"] == 1.0


def test_convert_amount_uses_cached_rate_and_falls_back(db):
    db.set_fx_rate("USD", "CAD", 1.35)
    assert db.convert_amount(100.0, "USD", "CAD") == 135.0
    # No GBP rate cached — graceful 1:1 fallback instead of failing.
    assert db.convert_amount(100.0, "GBP", "CAD") == 100.0


def test_invalid_rates_are_ignored(db):
    db.set_fx_rate("USD", "CAD", 0)
    db.set_fx_rate("USD", "CAD", -2)
    db.set_fx_rate("USD", "USD", 5)
    assert db.get_cached_fx_rate("USD", "CAD") is None


def test_get_account_currencies(db, user_id, account_id):
    db.create_account(user_id, "US", "Savings", 0.0, "USD")
    db.create_account(user_id, "US 2", "Cash", 0.0, "USD")
    assert db.get_account_currencies(user_id) == ["CAD", "USD"]


# ── Converted aggregates ──────────────────────────────────────────────────────

@pytest.fixture
def usd_account(db, user_id):
    """A USD savings account holding 500 USD, with USD→CAD = 1.35 cached."""
    aid = db.create_account(user_id, "US Savings", "Savings", 500.0, "USD")
    db.set_fx_rate("USD", "CAD", 1.35)
    return aid


def test_total_balance_converts_to_home_currency(db, user_id, account_id, usd_account):
    # 1000 CAD + 500 USD * 1.35 = 1675 CAD
    assert db.get_total_balance(user_id) == pytest.approx(1675.0)


def test_monthly_summary_converts_foreign_spending(db, user_id, account_id, usd_account):
    cat = db.get_categories("Expense")[0]["id"]
    db.create_transaction(usd_account, cat, "2026-06-15", "US expense", -100.0)
    db.create_transaction(account_id, cat, "2026-06-16", "CA expense", -50.0)
    summary = db.get_monthly_summary(user_id, 6, 2026)
    assert summary["expenses"] == pytest.approx(100 * 1.35 + 50)


def test_budget_actual_spending_converts(db, user_id, usd_account):
    cat = db.get_categories("Expense")[0]["id"]
    db.upsert_budget(user_id, cat, 6, 2026, 200.0)
    db.create_transaction(usd_account, cat, "2026-06-10", "US expense", -100.0)
    budgets = db.get_budgets(user_id, 6, 2026)
    assert budgets[0]["actual_spending"] == pytest.approx(135.0)


def test_net_worth_history_is_in_home_currency(db, user_id, account_id, usd_account):
    history = db.get_net_worth_history(user_id, 1)
    assert history[-1]["balance"] == pytest.approx(1675.0)


def test_spending_by_category_converts(db, user_id, usd_account):
    from datetime import datetime
    now = datetime.now()
    cat = db.get_categories("Expense")[0]["id"]
    db.create_transaction(usd_account, cat, now.strftime("%Y-%m-%d"), "US expense", -10.0)
    rows = db.get_spending_by_category(user_id, now.month, now.year)
    assert rows[0]["total"] == pytest.approx(13.5)


# ── Cross-currency transfers ──────────────────────────────────────────────────

def test_cross_currency_transfer_legs_and_balances(db, user_id, account_id, usd_account):
    from_id, to_id = db.create_transfer(
        account_id, usd_account, 135.0, "2026-06-20", "Top up", to_amount=100.0
    )
    assert db.get_transaction(from_id)["amount"] == -135.0
    assert db.get_transaction(to_id)["amount"] == 100.0
    assert db.get_account(account_id)["current_balance"] == 865.0
    assert db.get_account(usd_account)["current_balance"] == 600.0
    # Converted net worth is unchanged (transfer at exactly the cached rate).
    assert db.get_total_balance(user_id) == pytest.approx(865 + 600 * 1.35)


def test_delete_cross_currency_transfer_reverses_both_legs(db, user_id, account_id, usd_account):
    from_id, _ = db.create_transfer(
        account_id, usd_account, 135.0, "2026-06-20", "Top up", to_amount=100.0
    )
    db.delete_transfer(from_id)
    assert db.get_account(account_id)["current_balance"] == 1000.0
    assert db.get_account(usd_account)["current_balance"] == 500.0


def test_transfer_rejects_non_positive_received_amount(db, account_id, usd_account):
    with pytest.raises(ValueError):
        db.create_transfer(account_id, usd_account, 100.0, "2026-06-20", "Bad",
                           to_amount=0)


def test_same_currency_transfer_unchanged(db, user_id, account_id):
    other = db.create_account(user_id, "Second CAD", "Cash", 0.0)
    from_id, to_id = db.create_transfer(account_id, other, 40.0, "2026-06-01", "Move")
    assert db.get_transaction(from_id)["amount"] == -40.0
    assert db.get_transaction(to_id)["amount"] == 40.0


# ── Recurring across currencies ───────────────────────────────────────────────

def test_recurring_cross_currency_transfer_converts(db, user_id, account_id, usd_account):
    from datetime import date
    from services.recurring_service import RecurringService
    db.create_recurring(
        user_id, "Monthly top-up", 135.0, "Monthly", date.today().isoformat(),
        account_id=account_id, to_account_id=usd_account,
    )
    posted = RecurringService(db).process_due(user_id)
    assert posted == 1
    # Received leg converted at the cached CAD→USD rate (inverse of 1.35).
    assert db.get_account(usd_account)["current_balance"] == pytest.approx(600.0)
    assert db.get_account(account_id)["current_balance"] == pytest.approx(865.0)


def test_forecast_converts_foreign_recurring(db, user_id, account_id, usd_account):
    from datetime import date, timedelta
    from services.recurring_service import RecurringService
    cat = db.get_categories("Expense")[0]["id"]
    soon = (date.today() + timedelta(days=3)).isoformat()
    db.create_recurring(
        user_id, "US subscription", -100.0, "Yearly", soon,
        category_id=cat, account_id=usd_account,
    )
    fc = RecurringService(db).forecast(user_id, months=1)
    assert fc["start_balance"] == pytest.approx(1675.0)   # converted
    assert fc["events"][0]["amount"] == pytest.approx(-135.0)
    assert fc["end_balance"] == pytest.approx(1675.0 - 135.0)


# ── FxService ─────────────────────────────────────────────────────────────────

def test_fx_service_required_pairs_and_refresh(db, user_id, account_id, monkeypatch):
    from services.fx_service import FxService
    from services import fx_service as fx_mod
    db.create_account(user_id, "US", "Savings", 0.0, "USD")
    db.create_account(user_id, "EU", "Cash", 0.0, "EUR")
    svc = FxService(db)

    assert svc.required_pairs(user_id) == [("EUR", "CAD"), ("USD", "CAD")]
    assert svc.needs_refresh(user_id)   # nothing cached yet

    fake_rates = {("USD", "CAD"): 1.4, ("EUR", "CAD"): 1.5}
    monkeypatch.setattr(
        fx_mod.market_service, "get_fx_rate",
        lambda base, quote: fake_rates.get((base, quote)),
    )
    results = svc.refresh(user_id)
    assert results == {"EUR→CAD": 1.5, "USD→CAD": 1.4}
    assert db.get_cached_fx_rate("USD", "CAD")["rate"] == 1.4
    assert not svc.needs_refresh(user_id)   # fresh cache


def test_fx_service_refresh_survives_offline(db, user_id, account_id, monkeypatch):
    from services.fx_service import FxService
    from services import fx_service as fx_mod
    db.create_account(user_id, "US", "Savings", 0.0, "USD")
    db.set_fx_rate("USD", "CAD", 1.33)
    monkeypatch.setattr(fx_mod.market_service, "get_fx_rate", lambda *a: None)
    results = FxService(db).refresh(user_id)
    assert results == {"USD→CAD": None}
    # Old cached value untouched — conversion keeps working offline.
    assert db.get_cached_fx_rate("USD", "CAD")["rate"] == 1.33


def test_fx_service_home_only_needs_nothing(db, user_id, account_id):
    from services.fx_service import FxService
    svc = FxService(db)
    assert svc.required_pairs(user_id) == []
    assert not svc.needs_refresh(user_id)
