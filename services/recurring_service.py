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
            due = date.fromisoformat(rec["next_due_date"])
            if due > today:
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
                to_account_id,   # preserve transfer linkage across runs
            )
            posted += 1
        return posted
