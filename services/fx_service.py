"""
services/fx_service.py
Keeps the fx_rates cache fresh so multi-currency accounts convert correctly.

Rates come from the same keyless providers as the Markets panel
(market_service.get_fx_rate: Stooq with a Yahoo fallback). Every fetched rate
is cached in the fx_rates table (both directions), so conversion keeps working
offline with the last known rate. If a rate was never fetched, conversion
falls back to 1:1 — degraded but never blocking.
"""

from datetime import datetime, timedelta
from typing import Optional

from database import DatabaseManager
from services import market_service

# Currencies offered in the UI (signup, account dialog). The converter itself
# accepts any ISO code — this is just the curated picker list.
CURRENCIES = ["CAD", "USD", "EUR", "GBP", "AUD", "JPY", "CHF", "CNY", "INR", "MXN"]

# Cached rates older than this are considered stale and re-fetched.
MAX_AGE_HOURS = 24


class FxService:
    """Refreshes cached exchange rates for a user's account currencies."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def required_pairs(self, user_id: int) -> list[tuple[str, str]]:
        """(base, home) pairs needed to convert this user's accounts."""
        home = self._db.get_home_currency(user_id)
        return [
            (cur, home)
            for cur in self._db.get_account_currencies(user_id)
            if cur != home
        ]

    def needs_refresh(self, user_id: int, max_age_hours: int = MAX_AGE_HOURS) -> bool:
        """True if any needed rate is missing or older than *max_age_hours*."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        for base, quote in self.required_pairs(user_id):
            row = self._db.get_cached_fx_rate(base, quote)
            if row is None:
                return True
            try:
                if datetime.fromisoformat(row["updated"]) < cutoff:
                    return True
            except (TypeError, ValueError):
                return True
        return False

    def refresh(self, user_id: int) -> dict[str, Optional[float]]:
        """Fetch and cache every rate the user's accounts need.

        Returns {"USD→CAD": 1.37, ...} with None for pairs that failed
        (offline, provider down) — those keep their previously cached value.
        """
        results: dict[str, Optional[float]] = {}
        for base, quote in self.required_pairs(user_id):
            rate = market_service.get_fx_rate(base, quote)
            if rate:
                self._db.set_fx_rate(base, quote, rate)
            results[f"{base}→{quote}"] = rate
        return results
