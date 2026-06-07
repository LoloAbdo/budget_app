"""
tests/test_watchlist.py
Tests for the Markets watchlist table and the per-user language column.
"""

import pytest


class TestWatchlist:
    def test_add_and_get(self, db, user_id):
        db.add_watch(user_id, "btc", "Crypto", provider_id="bitcoin", display_name="Bitcoin")
        db.add_watch(user_id, "AAPL", "Stock", provider_id="aapl.us")
        wl = db.get_watchlist(user_id)
        symbols = {w["symbol"] for w in wl}
        assert symbols == {"BTC", "AAPL"}        # symbols normalized to upper-case
        btc = next(w for w in wl if w["symbol"] == "BTC")
        assert btc["asset_type"] == "Crypto"
        assert btc["provider_id"] == "bitcoin"
        assert btc["display_name"] == "Bitcoin"

    def test_add_is_idempotent(self, db, user_id):
        first = db.add_watch(user_id, "BTC", "Crypto", provider_id="bitcoin")
        again = db.add_watch(user_id, "btc", "Crypto", provider_id="bitcoin")
        assert first == again
        assert len(db.get_watchlist(user_id)) == 1

    def test_same_symbol_different_type_allowed(self, db, user_id):
        db.add_watch(user_id, "BTC", "Crypto", provider_id="bitcoin")
        db.add_watch(user_id, "BTC", "Stock", provider_id="btc.us")
        assert len(db.get_watchlist(user_id)) == 2

    def test_update_cache(self, db, user_id):
        wid = db.add_watch(user_id, "BTC", "Crypto", provider_id="bitcoin")
        db.update_watch_cache(wid, 84358.0, -1.97, "CAD", "2026-06-06 10:55")
        w = db.get_watchlist(user_id)[0]
        assert w["last_price"] == pytest.approx(84358.0)
        assert w["last_change_pct"] == pytest.approx(-1.97)
        assert w["last_currency"] == "CAD"
        assert w["last_updated"] == "2026-06-06 10:55"

    def test_remove(self, db, user_id):
        wid = db.add_watch(user_id, "BTC", "Crypto", provider_id="bitcoin")
        db.remove_watch(wid)
        assert db.get_watchlist(user_id) == []

    def test_watchlist_isolated_per_user(self, db, user_id):
        from services.auth_service import AuthService
        AuthService(db).register("Other", "other@test.com", "password123", "CAD")
        other = db.get_user_by_email("other@test.com")["id"]
        db.add_watch(user_id, "BTC", "Crypto", provider_id="bitcoin")
        assert db.get_watchlist(other) == []


class TestLanguageColumn:
    def test_default_language_is_en(self, db, user_id):
        assert db.get_user(user_id)["language"] == "en"

    def test_update_language(self, db, user_id):
        db.update_user_language(user_id, "fr")
        assert db.get_user(user_id)["language"] == "fr"
