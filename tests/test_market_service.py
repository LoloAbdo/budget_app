"""
tests/test_market_service.py
Unit tests for the keyless market-data service. All network access is
monkeypatched, so these tests are fully offline and deterministic.
"""

import pytest
from services import market_service as ms


# ── Pure parsers ──────────────────────────────────────────────────────────────

class TestParsers:
    def test_stooq_single_close(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\nAAPL.US,2026-06-05,22:00,200,205,199,204,1000"
        assert ms._parse_stooq_close(csv) == pytest.approx(204.0)

    def test_stooq_single_quote_change(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\nAAPL.US,2026-06-05,22:00,200,205,199,204,1000"
        close, change = ms._parse_stooq_quote(csv)
        assert close == pytest.approx(204.0)
        assert change == pytest.approx(2.0)  # (204-200)/200*100

    def test_stooq_nd_returns_none(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\nFOO.US,N/D,N/D,N/D,N/D,N/D,N/D,N/D"
        assert ms._parse_stooq_quote(csv) == (None, None)
        assert ms._parse_stooq_close(csv) is None

    def test_stooq_multi(self):
        csv = ("Symbol,Date,Time,Open,High,Low,Close,Volume\n"
               "AAPL.US,2026,22:00,200,205,199,204,1\n"
               "MSFT.US,2026,22:00,400,410,395,408,1\n"
               "BAD.US,2026,N/D,N/D,N/D,N/D,N/D,N/D")
        parsed = ms._parse_stooq_multi(csv)
        assert parsed["AAPL.US"][0] == pytest.approx(204.0)
        assert parsed["MSFT.US"][0] == pytest.approx(408.0)
        assert parsed["BAD.US"] == (None, None)

    def test_yahoo_parse(self):
        data = {"chart": {"result": [{"meta": {"regularMarketPrice": 110.0,
                                               "chartPreviousClose": 100.0}}]}}
        assert ms._parse_yahoo_price(data) == (110.0, pytest.approx(10.0))

    def test_yahoo_parse_garbage(self):
        assert ms._parse_yahoo_price({}) == (None, None)
        assert ms._parse_yahoo_price(None) == (None, None)


# ── Symbol resolution (no network) ──────────────────────────────────────────

class TestResolution:
    def test_known_crypto_id(self):
        assert ms.known_crypto_id("BTC") == "bitcoin"
        assert ms.known_crypto_id("eth") == "ethereum"
        assert ms.known_crypto_id("NOPE") is None

    def test_default_stock_provider_id(self):
        assert ms.default_stock_provider_id("AAPL") == "aapl.us"
        # Explicit exchange suffix is preserved
        assert ms.default_stock_provider_id("SHOP.TO") == "shop.to"


# ── Crypto fetch (mocked CoinGecko) ──────────────────────────────────────────

class TestFetchCrypto:
    def test_success(self, monkeypatch):
        monkeypatch.setattr(ms, "_get_json",
                            lambda url: {"bitcoin": {"cad": 90000.0, "cad_24h_change": 1.5}})
        out = ms.fetch_crypto([{"symbol": "BTC", "provider_id": "bitcoin"}], "CAD")
        q = out["BTC"]
        assert q.ok and q.price == pytest.approx(90000.0)
        assert q.change_pct == pytest.approx(1.5)
        assert q.currency == "CAD"

    def test_missing_coin_marked_not_ok(self, monkeypatch):
        monkeypatch.setattr(ms, "_get_json", lambda url: {})
        out = ms.fetch_crypto([{"symbol": "BTC", "provider_id": "bitcoin"}], "CAD")
        assert out["BTC"].ok is False


# ── Stock fetch (mocked Stooq + FX), incl. batching ──────────────────────────

class TestFetchStocks:
    def test_batched_single_request_and_fx(self, monkeypatch):
        calls = []

        def fake_get(url):
            calls.append(url)
            if "usdcad" in url:
                return "Symbol,Date,Time,Open,High,Low,Close,Volume\nUSDCAD,2026,22:00,1.36,1.36,1.36,1.36,0"
            return ("Symbol,Date,Time,Open,High,Low,Close,Volume\n"
                    "AAPL.US,2026,22:00,200,205,199,204,1\n"
                    "MSFT.US,2026,22:00,400,410,395,408,1\n"
                    "TSLA.US,2026,22:00,300,310,295,305,1")

        monkeypatch.setattr(ms, "_get", fake_get)
        items = [{"symbol": s, "provider_id": f"{s.lower()}.us"} for s in ("AAPL", "MSFT", "TSLA")]
        out = ms.fetch_stocks(items, "CAD")

        # 204 USD * 1.36 = 277.44 CAD
        assert out["AAPL"].price == pytest.approx(277.44, abs=0.01)
        assert out["AAPL"].ok and out["AAPL"].currency == "CAD"
        # Exactly ONE batched Stooq quote request (plus one FX request)
        quote_reqs = [u for u in calls if "stooq.com/q/l" in u and "usdcad" not in u]
        assert len(quote_reqs) == 1
        assert "aapl.us" in quote_reqs[0] and "msft.us" in quote_reqs[0] and "tsla.us" in quote_reqs[0]

    def test_no_fx_when_currency_is_usd(self, monkeypatch):
        monkeypatch.setattr(
            ms, "_get",
            lambda url: "Symbol,Date,Time,Open,High,Low,Close,Volume\nAAPL.US,2026,22:00,200,205,199,204,1",
        )
        out = ms.fetch_stocks([{"symbol": "AAPL", "provider_id": "aapl.us"}], "USD")
        assert out["AAPL"].price == pytest.approx(204.0)

    def test_yahoo_fallback_when_stooq_empty(self, monkeypatch):
        monkeypatch.setattr(ms, "_get", lambda url: "")   # Stooq returns nothing
        monkeypatch.setattr(
            ms, "_get_json",
            lambda url: {"chart": {"result": [{"meta": {"regularMarketPrice": 50.0,
                                                        "chartPreviousClose": 50.0}}]}},
        )
        out = ms.fetch_stocks([{"symbol": "AAPL", "provider_id": "aapl.us"}], "USD")
        assert out["AAPL"].ok and out["AAPL"].price == pytest.approx(50.0)

    def test_no_data_marked_not_ok(self, monkeypatch):
        monkeypatch.setattr(ms, "_get", lambda url: "")
        monkeypatch.setattr(ms, "_get_json", lambda url: None)
        out = ms.fetch_stocks([{"symbol": "ZZZZ", "provider_id": "zzzz.us"}], "USD")
        assert out["ZZZZ"].ok is False


# ── Unified entry point ──────────────────────────────────────────────────────

class TestFetchQuotes:
    def test_mixed_watchlist_keys(self, monkeypatch):
        monkeypatch.setattr(ms, "_get_json",
                            lambda url: {"bitcoin": {"usd": 90000.0, "usd_24h_change": 2.0}})
        monkeypatch.setattr(
            ms, "_get",
            lambda url: "Symbol,Date,Time,Open,High,Low,Close,Volume\nAAPL.US,2026,22:00,200,205,199,204,1",
        )
        out = ms.fetch_quotes(
            [{"symbol": "BTC", "asset_type": "Crypto", "provider_id": "bitcoin"},
             {"symbol": "AAPL", "asset_type": "Stock", "provider_id": "aapl.us"}],
            "USD",
        )
        assert ("BTC", "Crypto") in out and ("AAPL", "Stock") in out
        assert out[("BTC", "Crypto")].ok and out[("AAPL", "Stock")].ok

    def test_network_failure_never_raises(self, monkeypatch):
        # Simulate total network failure: every request returns None.
        monkeypatch.setattr(ms, "_get", lambda url: None)
        monkeypatch.setattr(ms, "_get_json", lambda url: None)
        out = ms.fetch_quotes(
            [{"symbol": "AAPL", "asset_type": "Stock", "provider_id": "aapl.us"}], "CAD"
        )
        assert out[("AAPL", "Stock")].ok is False
