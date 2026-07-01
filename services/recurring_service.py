"""
services/recurring_service.py
Processes due recurring transactions and advances their next_due_date.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta  # type: ignore[import]
from typing import Optional

from database import DatabaseManager


def _next_date(current: date, frequency: str) -> date:
    """Return the next due date for a given frequency."""
    if frequency == "Weekly":
        return current + timedelta(weeks=1)
    elif frequency == "Bi-weekly":
        return current + timedelta(weeks=2)
    elif frequency == "Monthly":
        return current + relativedelta(months=1)
    elif frequency == "Quarterly":
        return current + relativedelta(months=3)
    elif frequency == "Yearly":
        return current + relativedelta(years=1)
    return current + timedelta(days=30)


class RecurringService:
    """Checks for due recurring transactions and posts them."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def process_due(self, user_id: int) -> int:
        """
        Post all due recurring transactions for *user_id*.
        Returns the number of transactions posted.
        """
        today = date.today()
        posted = 0
        for rec in self._db.get_recurring(user_id):
            if not rec.get("is_active", 1):
                continue  # paused rules don't post until resumed
            due = date.fromisoformat(rec["next_due_date"])
            if due > today:
                continue

            # Honor an optional end date: once the next occurrence falls past it,
            # the schedule is finished — stop posting (the row stays dormant).
            end = rec.get("end_date")
            if end and due > date.fromisoformat(end):
                continue

            account_id: Optional[int] = rec.get("account_id")
            accounts = self._db.get_accounts(user_id)
            if not account_id and accounts:
                account_id = accounts[0]["id"]
            if not account_id:
                continue

            to_account_id: Optional[int] = rec.get("to_account_id")
            if to_account_id:
                # Recurring transfer — move money between both accounts (two legs)
                try:
                    self._db.create_transfer(
                        from_account_id=account_id,
                        to_account_id=to_account_id,
                        amount=abs(rec["amount"]),
                        date=str(today),
                        description=rec["name"],
                        notes="Auto-generated from recurring",
                    )
                except ValueError:
                    # Same source/dest or non-positive amount — skip without advancing
                    continue
            else:
                # Regular recurring income/expense — single-account transaction
                self._db.create_transaction(
                    account_id=account_id,
                    category_id=rec.get("category_id"),
                    date=str(today),
                    description=rec["name"],
                    amount=rec["amount"],
                    notes="Auto-generated from recurring",
                    recurring_id=rec["id"],
                )

            new_due = _next_date(due, rec["frequency"])
            self._db.update_recurring(
                rec["id"],
                rec["name"],
                rec["amount"],
                rec["frequency"],
                str(new_due),
                rec.get("category_id"),
                account_id,
                to_account_id,        # preserve transfer linkage across runs
                rec.get("end_date"),  # preserve the end date across runs
            )
            posted += 1
        return posted

    def forecast(self, user_id: int, months: int = 3) -> dict:
        """Project total balance forward from recurring income/expenses.

        Starts at the current combined balance of all accounts and walks every
        non-transfer recurring entry forward, occurrence by occurrence, up to
        *months* ahead. Transfers move money between the user's own accounts, so
        they leave net worth unchanged and are skipped.

        Returns a dict with:
            start_balance — combined balance today
            end_balance   — projected balance at the horizon
            events        — chronological list of {date, name, amount, balance}
            timeline      — [(date, balance), …] starting at today, for charting
        """
        today = date.today()
        horizon = today + relativedelta(months=months)
        start_balance = sum(a["current_balance"] for a in self._db.get_accounts(user_id))

        occurrences: list[tuple[date, str, float]] = []
        for rec in self._db.get_recurring(user_id):
            if not rec.get("is_active", 1):
                continue  # paused rules are excluded from the projection
            if rec.get("to_account_id"):
                continue  # transfers don't change net worth
            end = rec.get("end_date")
            end_dt = date.fromisoformat(end) if end else None
            due = date.fromisoformat(rec["next_due_date"])
            while due <= horizon:
                if end_dt and due > end_dt:
                    break  # schedule has ended — no further occurrences
                if due >= today:
                    occurrences.append((due, rec["name"], rec["amount"]))
                due = _next_date(due, rec["frequency"])

        occurrences.sort(key=lambda o: o[0])

        balance = start_balance
        events: list[dict] = []
        timeline: list[tuple[date, float]] = [(today, start_balance)]
        for when, name, amount in occurrences:
            balance += amount
            events.append({"date": when, "name": name, "amount": amount, "balance": balance})
            timeline.append((when, balance))

        return {
            "start_balance": start_balance,
            "end_balance": balance,
            "events": events,
            "timeline": timeline,
        }
