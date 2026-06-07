"""
services/market_service.py
Keyless market-data fetching for the Markets watchlist.

Sources (no API key required):
  * Crypto  -> CoinGecko    (https://api.coingecko.com) — returns the user's
               currency directly via vs_currencies.
  * Stocks  -> Stooq CSV    (https://stooq.com)  with a Yahoo chart fallback.
  * FX      -> Stooq        (e.g. usdcad) with a Yahoo fallback, to convert
               non-CAD stock prices into the user's currency.

Everything here is plain Python (no Qt) so it can run on a worker thread and be
unit-tested in isolation. All network calls have short timeouts and never raise:
failures are reported per-symbol via Quote.ok = False.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

_TIMEOUT = 6  # seconds per request
_UA = "BudgetManager/1.0 (+local desktop app)"

# Popular crypto ticker -> CoinGecko id. Anything not here is resolved lazily
# against CoinGecko's full coin list (cached) the first time it's needed.
_CRYPTO_IDS: dict[str, str] = {
    "BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether", "BNB": "binancecoin",
    "SOL": "solana", "XRP": "ripple", "USDC": "usd-coin", "ADA": "cardano",
    "DOGE": "dogecoin", "TRX": "tron", "TON": "the-open-network", "DOT": "polkadot",
    "MATIC": "matic-network", "LTC": "litecoin", "SHIB": "shiba-inu",
    "AVAX": "avalanche-2", "LINK": "chainlink", "XLM": "stellar", "ATOM": "cosmos",
    "XMR": "monero", "ETC": "ethereum-classic", "BCH": "bitcoin-cash",
    "ALGO": "algorand", "VET": "vechain", "ICP": "internet-computer",
}

# Cache of the CoinGecko coins list (symbol -> id), populated on demand.
_coin_list_cache: dict[str, str] = {}


@dataclass
class Quote:
    """A normalized price quote in the user's currency."""
    symbol: str
    asset_type: str            # "Stock" | "Crypto"
    price: Optional[float] = None
    change_pct: Optional[float] = None   # day / 24h change, %
    currency: str = "CAD"
    name: str = ""
    ok: bool = False
    error: str = ""


# ── Low-level HTTP helpers ───────────────────────────────────────────────────

def _get(url: str) -> Optional[str]:
    """GET a URL and return the body text, or None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _get_json(url: str):
    body = _get(url)
    if body is None:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


# ── FX ────────────────────────────────────────────────────────────────────────

def get_fx_rate(base: str, quote: str) -> Optional[float]:
    """Return how many units of *quote* equal 1 unit of *base* (e.g. USD->CAD)."""
    base, quote = base.upper(), quote.upper()
    if base == quote:
        return 1.0
    pair = f"{base}{quote}".lower()
    # Stooq: e.g. https://stooq.com/q/l/?s=usdcad&f=sd2t2ohlcv&e=csv
    body = _get(f"https://stooq.com/q/l/?s={pair}&f=sd2t2ohlcv&e=csv")
    rate = _parse_stooq_close(body)
    if rate is not None:
        return rate
    # Yahoo fallback: USDCAD=X
    data = _get_json(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{base}{quote}=X?interval=1d&range=1d"
    )
    return _parse_yahoo_price(data)[0]


# ── Crypto (CoinGecko) ──────────────────────────────────────────────────────

def resolve_crypto_id(symbol: str) -> Optional[str]:
    """Resolve a crypto ticker (BTC) or id (bitcoin) to a CoinGecko id."""
    s = symbol.strip()
    if not s:
        return None
    upper = s.upper()
    if upper in _CRYPTO_IDS:
        return _CRYPTO_IDS[upper]
    lower = s.lower()
    # Maybe the user already gave a CoinGecko id (e.g. "bitcoin")
    if lower in _coin_list_cache.values():
        return lower
    _load_coin_list()
    return _coin_list_cache.get(upper) or (lower if lower in _coin_list_cache.values() else None)


def known_crypto_id(symbol: str) -> Optional[str]:
    """Resolve a crypto ticker to a CoinGecko id using only the built-in map
    (no network) — used when adding a symbol so the UI never blocks."""
    return _CRYPTO_IDS.get(symbol.strip().upper())


def default_stock_provider_id(symbol: str) -> str:
    """Default Stooq provider id for a stock symbol (US suffix if none given)."""
    return _stooq_symbol(symbol)


def _load_coin_list() -> None:
    global _coin_list_cache
    if _coin_list_cache:
        return
    data = _get_json("https://api.coingecko.com/api/v3/coins/list")
    if isinstance(data, list):
        # First occurrence wins (CoinGecko lists the canonical coin early).
        for entry in data:
            sym = str(entry.get("symbol", "")).upper()
            cid = entry.get("id")
            if sym and cid and sym not in _coin_list_cache:
                _coin_list_cache[sym] = cid


def fetch_crypto(items: list[dict], currency: str) -> dict[str, Quote]:
    """
    Fetch crypto quotes. *items* = [{"symbol","provider_id"}].
    Returns {symbol_upper: Quote} in *currency*.
    """
    cur = currency.lower()
    id_to_symbol: dict[str, str] = {}
    for it in items:
        cid = it.get("provider_id") or resolve_crypto_id(it["symbol"])
        if cid:
            id_to_symbol[cid] = it["symbol"].upper()

    out: dict[str, Quote] = {}
    if not id_to_symbol:
        return out

    ids = ",".join(id_to_symbol.keys())
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={urllib.parse.quote(ids)}&vs_currencies={cur}&include_24hr_change=true"
    )
    data = _get_json(url)
    for cid, sym in id_to_symbol.items():
        q = Quote(symbol=sym, asset_type="Crypto", currency=currency.upper(), name=cid)
        row = data.get(cid) if isinstance(data, dict) else None
        if row and row.get(cur) is not None:
            q.price = float(row[cur])
            chg = row.get(f"{cur}_24h_change")
            q.change_pct = float(chg) if chg is not None else None
            q.ok = True
        else:
            q.error = "not found"
        out[sym] = q
    return out


# ── Stocks (Stooq + Yahoo fallback) ─────────────────────────────────────────

def _stooq_symbol(symbol: str) -> str:
    """Stooq wants a market suffix; default US stocks to '.us'."""
    s = symbol.strip().lower()
    return s if "." in s else f"{s}.us"


def _parse_stooq_close(csv_text: Optional[str]) -> Optional[float]:
    """Parse the Close price from a single-row Stooq CSV response."""
    if not csv_text:
        return None
    lines = [ln for ln in csv_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    header = [h.strip().lower() for h in lines[0].split(",")]
    row = lines[1].split(",")
    if len(row) < len(header):
        return None
    rec = dict(zip(header, row))
    close = rec.get("close")
    if not close or close.upper() in ("N/D", "N/A", ""):
        return None
    try:
        return float(close)
    except ValueError:
        return None


def _parse_stooq_quote(csv_text: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    """Return (close, change_pct) from a Stooq ohlc CSV row (intraday day change)."""
    if not csv_text:
        return None, None
    lines = [ln for ln in csv_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return None, None
    header = [h.strip().lower() for h in lines[0].split(",")]
    rec = dict(zip(header, lines[1].split(",")))
    try:
        close = float(rec.get("close", ""))
    except ValueError:
        return None, None
    change_pct = None
    try:
        op = float(rec.get("open", ""))
        if op:
            change_pct = (close - op) / op * 100.0
    except ValueError:
        pass
    return close, change_pct


def _parse_stooq_multi(csv_text: Optional[str]) -> dict[str, tuple[Optional[float], Optional[float]]]:
    """Parse a multi-row Stooq CSV into {SYMBOL_UPPER: (close, change_pct)}."""
    res: dict[str, tuple[Optional[float], Optional[float]]] = {}
    if not csv_text:
        return res
    lines = [ln for ln in csv_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return res
    header = [h.strip().lower() for h in lines[0].split(",")]
    for ln in lines[1:]:
        rec = dict(zip(header, ln.split(",")))
        sym = (rec.get("symbol") or "").strip().upper()
        if not sym:
            continue
        close = rec.get("close")
        if not close or close.upper() in ("N/D", "N/A", ""):
            res[sym] = (None, None)
            continue
        try:
            c = float(close)
        except ValueError:
            res[sym] = (None, None)
            continue
        change_pct = None
        try:
            op = float(rec.get("open", ""))
            if op:
                change_pct = (c - op) / op * 100.0
        except ValueError:
            pass
        res[sym] = (c, change_pct)
    return res


def _parse_yahoo_price(data) -> tuple[Optional[float], Optional[float]]:
    """Return (price, change_pct) from a Yahoo v8 chart payload."""
    try:
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        change = None
        if price is not None and prev:
            change = (price - prev) / prev * 100.0
        return (float(price) if price is not None else None, change)
    except Exception:
        return None, None


def fetch_stocks(items: list[dict], currency: str) -> dict[str, Quote]:
    """
    Fetch stock quotes and convert to *currency* (assumes USD-listed unless the
    symbol carries a non-US suffix; FX applied for USD->currency only).
    *items* = [{"symbol","provider_id"}]. Returns {symbol_upper: Quote}.

    All symbols are fetched in ONE batched Stooq request to minimise calls (and
    stay well under any rate limit); only symbols Stooq can't serve fall back to
    Yahoo individually, and the FX rate is fetched at most once.
    """
    out: dict[str, Quote] = {}
    if not items:
        return out

    # Map Stooq symbol -> requested item (one row per requested symbol)
    stq_map: dict[str, dict] = {}
    for it in items:
        stq = (it.get("provider_id") or _stooq_symbol(it["symbol"])).lower()
        stq_map[stq] = it

    # One batched request for every stock symbol
    joined = ",".join(stq_map.keys())
    parsed = _parse_stooq_multi(
        _get(f"https://stooq.com/q/l/?s={urllib.parse.quote(joined)}&f=sd2t2ohlcv&e=csv")
    )

    # FX fetched at most once for the whole batch
    native = "USD"
    fx_needed = currency.upper() != native
    fx_rate = get_fx_rate(native, currency) if fx_needed else 1.0

    for stq, it in stq_map.items():
        symbol = it["symbol"].strip()
        up = symbol.upper()
        q = Quote(symbol=up, asset_type="Stock", currency=currency.upper(), name=up)

        price, change = parsed.get(stq.upper(), (None, None))
        if price is None:
            # Yahoo fallback for just this symbol
            price, change = _parse_yahoo_price(
                _get_json(
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
                    "?interval=1d&range=2d"
                )
            )
        if price is None:
            q.error = "no data"
            out[up] = q
            continue

        if fx_needed and fx_rate:
            price *= fx_rate
        q.price = price
        q.change_pct = change
        q.ok = True
        out[up] = q
    return out


# ── Unified entry point ──────────────────────────────────────────────────────

def fetch_quotes(items: list[dict], currency: str = "CAD") -> dict[tuple[str, str], Quote]:
    """
    Fetch quotes for a mixed watchlist.
    *items* = [{"symbol","asset_type","provider_id"}].
    Returns {(symbol_upper, asset_type): Quote}.
    """
    crypto = [it for it in items if it.get("asset_type") == "Crypto"]
    stocks = [it for it in items if it.get("asset_type") == "Stock"]

    result: dict[tuple[str, str], Quote] = {}
    if crypto:
        for sym, q in fetch_crypto(crypto, currency).items():
            result[(sym, "Crypto")] = q
    if stocks:
        for sym, q in fetch_stocks(stocks, currency).items():
            result[(sym, "Stock")] = q
    return result
