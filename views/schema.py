"""
database/schema.py
Defines SQL schema strings and the DatabaseManager class for all SQLite operations.
Uses parameterized queries throughout to prevent SQL injection.
"""

import sqlite3
import os
import hashlib
import threading
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

# ── Schema DDL ───────────────────────────────────────────────────────────────

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    currency    TEXT    NOT NULL DEFAULT 'CAD',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name    TEXT    NOT NULL,
    account_type    TEXT    NOT NULL CHECK(account_type IN ('Checking','Savings','Credit Card','Cash')),
    current_balance REAL    NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS categories (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    type    TEXT NOT NULL CHECK(type IN ('Income','Expense')),
    color   TEXT NOT NULL DEFAULT '#607D8B'
);

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    frequency       TEXT    NOT NULL CHECK(frequency IN ('Weekly','Bi-weekly','Monthly','Quarterly','Yearly')),
    next_due_date   TEXT    NOT NULL,
    category_id     INTEGER REFERENCES categories(id),
    account_id      INTEGER REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    category_id     INTEGER REFERENCES categories(id),
    date            TEXT    NOT NULL,
    description     TEXT    NOT NULL,
    amount          REAL    NOT NULL,
    notes           TEXT    DEFAULT '',
    recurring_id    INTEGER REFERENCES recurring_transactions(id)
);

CREATE TABLE IF NOT EXISTS budgets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id     INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    month           INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    year            INTEGER NOT NULL,
    budget_amount   REAL    NOT NULL DEFAULT 0.0,
    UNIQUE(user_id, category_id, month, year)
);

CREATE TABLE IF NOT EXISTS financial_goals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_name       TEXT    NOT NULL,
    target_amount   REAL    NOT NULL,
    current_amount  REAL    NOT NULL DEFAULT 0.0,
    target_date     TEXT    NOT NULL
);
"""

# ── Default seed data ─────────────────────────────────────────────────────────

DEFAULT_CATEGORIES = [
    # Income
    ("Salary",       "Income",  "#4CAF50"),
    ("Freelance",    "Income",  "#8BC34A"),
    ("Investment",   "Income",  "#009688"),
    ("Other Income", "Income",  "#00BCD4"),
    # Expense
    ("Rent/Mortgage","Expense", "#F44336"),
    ("Groceries",    "Expense", "#FF5722"),
    ("Gas",          "Expense", "#FF9800"),
    ("Utilities",    "Expense", "#FFC107"),
    ("Insurance",    "Expense", "#9C27B0"),
    ("Entertainment","Expense", "#3F51B5"),
    ("Dining Out",   "Expense", "#2196F3"),
    ("Healthcare",   "Expense", "#00BCD4"),
    ("Clothing",     "Expense", "#009688"),
    ("Education",    "Expense", "#795548"),
    ("Travel",       "Expense", "#607D8B"),
    ("Subscriptions","Expense", "#E91E63"),
    ("Personal Care","Expense", "#673AB7"),
    ("Gifts",        "Expense", "#F06292"),
    ("Miscellaneous","Expense", "#90A4AE"),
]


class DatabaseManager:
    """
    Thread-safe SQLite database manager.
    All public methods return plain Python dicts/lists; no raw sqlite3.Row leaks out.
    """

    _local = threading.local()

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Connection handling ───────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Return a per-thread connection, creating it if needed."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        """Create tables, run migrations, and seed default categories."""
        conn = self._conn()
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        self._migrate(conn)
        self._seed_categories(conn)

    def _migrate(self, conn) -> None:
        """Incremental schema migrations for existing databases."""
        # v1.0.1 — budgets table needs user_id + correct UNIQUE constraint
        # ALTER TABLE cannot change constraints, so we recreate the table when needed.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(budgets)").fetchall()]
        if "user_id" not in cols:
            # Recreate with user_id column and updated UNIQUE constraint
            conn.executescript("""
                CREATE TABLE budgets_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL DEFAULT 1,
                    category_id   INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                    month         INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
                    year          INTEGER NOT NULL,
                    budget_amount REAL    NOT NULL DEFAULT 0.0,
                    UNIQUE(user_id, category_id, month, year)
                );
                INSERT INTO budgets_new (id, user_id, category_id, month, year, budget_amount)
                    SELECT id, 1, category_id, month, year, budget_amount FROM budgets;
                DROP TABLE budgets;
                ALTER TABLE budgets_new RENAME TO budgets;
            """)
            conn.commit()

    def _seed_categories(self, conn: sqlite3.Connection) -> None:
        """Insert default categories if the table is empty."""
        if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO categories (name, type, color) VALUES (?,?,?)",
                DEFAULT_CATEGORIES,
            )
            conn.commit()

    # ── Generic helpers ───────────────────────────────────────────────────────

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        rows = self._conn().execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        row = self._conn().execute(sql, params).fetchone()
        return dict(row) if row else None

    def _execute(self, sql: str, params: tuple = ()) -> int:
        """Execute a DML statement; return lastrowid."""
        conn = self._conn()          # single reference — avoids double-call race
        cur  = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    # ── Users ─────────────────────────────────────────────────────────────────

    def create_user(self, name: str, email: str, password_hash: str, currency: str = "CAD") -> int:
        return self._execute(
            "INSERT INTO users (name, email, password, currency) VALUES (?,?,?,?)",
            (name, email, password_hash, currency),
        )

    def get_user_by_email(self, email: str) -> Optional[dict]:
        return self._fetchone("SELECT * FROM users WHERE email=?", (email,))

    def get_user(self, user_id: int) -> Optional[dict]:
        return self._fetchone("SELECT * FROM users WHERE id=?", (user_id,))

    def update_user(self, user_id: int, name: str, currency: str) -> None:
        self._execute("UPDATE users SET name=?, currency=? WHERE id=?", (name, currency, user_id))

    # ── Accounts ──────────────────────────────────────────────────────────────

    def get_accounts(self, user_id: int) -> list[dict]:
        return self._fetchall("SELECT * FROM accounts WHERE user_id=? ORDER BY account_name", (user_id,))

    def get_account(self, account_id: int) -> Optional[dict]:
        return self._fetchone("SELECT * FROM accounts WHERE id=?", (account_id,))

    def create_account(self, user_id: int, name: str, acct_type: str, balance: float = 0.0) -> int:
        return self._execute(
            "INSERT INTO accounts (user_id, account_name, account_type, current_balance) VALUES (?,?,?,?)",
            (user_id, name, acct_type, balance),
        )

    def update_account(self, account_id: int, name: str, acct_type: str, balance: float) -> None:
        self._execute(
            "UPDATE accounts SET account_name=?, account_type=?, current_balance=? WHERE id=?",
            (name, acct_type, balance, account_id),
        )

    def delete_account(self, account_id: int) -> None:
        self._execute("DELETE FROM accounts WHERE id=?", (account_id,))

    def update_account_balance(self, account_id: int, delta: float) -> None:
        self._execute(
            "UPDATE accounts SET current_balance = current_balance + ? WHERE id=?",
            (delta, account_id),
        )

    # ── Categories ────────────────────────────────────────────────────────────

    def get_categories(self, cat_type: Optional[str] = None) -> list[dict]:
        if cat_type:
            return self._fetchall("SELECT * FROM categories WHERE type=? ORDER BY name", (cat_type,))
        return self._fetchall("SELECT * FROM categories ORDER BY type, name")

    def get_category(self, category_id: int) -> Optional[dict]:
        return self._fetchone("SELECT * FROM categories WHERE id=?", (category_id,))

    def create_category(self, name: str, cat_type: str, color: str) -> int:
        return self._execute(
            "INSERT INTO categories (name, type, color) VALUES (?,?,?)",
            (name, cat_type, color),
        )

    def update_category(self, category_id: int, name: str, cat_type: str, color: str) -> None:
        self._execute(
            "UPDATE categories SET name=?, type=?, color=? WHERE id=?",
            (name, cat_type, color, category_id),
        )

    def delete_category(self, category_id: int) -> None:
        self._execute("DELETE FROM categories WHERE id=?", (category_id,))

    # ── Transactions ──────────────────────────────────────────────────────────

    def get_transactions(
        self,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category_id: Optional[int] = None,
        account_id: Optional[int] = None,
        keyword: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        sql = """
            SELECT t.*, c.name AS category_name, c.type AS category_type, c.color AS category_color,
                   a.account_name, a.account_type
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE a.user_id = ?
        """
        params: list[Any] = [user_id]
        if start_date:
            sql += " AND t.date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND t.date <= ?"
            params.append(end_date)
        if category_id:
            sql += " AND t.category_id = ?"
            params.append(category_id)
        if account_id:
            sql += " AND t.account_id = ?"
            params.append(account_id)
        if keyword:
            sql += " AND (t.description LIKE ? OR t.notes LIKE ?)"
            params += [f"%{keyword}%", f"%{keyword}%"]
        sql += " ORDER BY t.date DESC, t.id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self._fetchall(sql, tuple(params))

    def get_transaction(self, transaction_id: int) -> Optional[dict]:
        return self._fetchone(
            """SELECT t.*, c.name AS category_name, c.type AS category_type,
                      a.account_name FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               LEFT JOIN categories c ON t.category_id = c.id
               WHERE t.id=?""",
            (transaction_id,),
        )

    def create_transaction(
        self,
        account_id: int,
        category_id: Optional[int],
        date: str,
        description: str,
        amount: float,
        notes: str = "",
        recurring_id: Optional[int] = None,
    ) -> int:
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO transactions (account_id, category_id, date, description, amount, notes, recurring_id) VALUES (?,?,?,?,?,?,?)",
            (account_id, category_id, date, description, amount, notes, recurring_id),
        )
        conn.execute(
            "UPDATE accounts SET current_balance = current_balance + ? WHERE id=?",
            (amount, account_id),
        )
        conn.commit()
        return cur.lastrowid

    def update_transaction(
        self,
        txn_id: int,
        account_id: int,
        category_id: Optional[int],
        date: str,
        description: str,
        amount: float,
        notes: str,
    ) -> None:
        conn = self._conn()
        old = conn.execute("SELECT account_id, amount FROM transactions WHERE id=?", (txn_id,)).fetchone()
        if old:
            conn.execute(
                "UPDATE accounts SET current_balance = current_balance + ? WHERE id=?",
                (-old["amount"], old["account_id"]),
            )
        conn.execute(
            "UPDATE transactions SET account_id=?, category_id=?, date=?, description=?, amount=?, notes=? WHERE id=?",
            (account_id, category_id, date, description, amount, notes, txn_id),
        )
        conn.execute(
            "UPDATE accounts SET current_balance = current_balance + ? WHERE id=?",
            (amount, account_id),
        )
        conn.commit()

    def delete_transaction(self, txn_id: int) -> None:
        conn = self._conn()
        old = conn.execute("SELECT account_id, amount FROM transactions WHERE id=?", (txn_id,)).fetchone()
        if old:
            conn.execute(
                "UPDATE accounts SET current_balance = current_balance + ? WHERE id=?",
                (-old["amount"], old["account_id"]),
            )
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        conn.commit()

    # ── Budgets ───────────────────────────────────────────────────────────────

    def get_budgets(self, user_id: int, month: int, year: int) -> list[dict]:
        return self._fetchall(
            """SELECT b.*, c.name AS category_name, c.color,
                      COALESCE((SELECT SUM(ABS(t.amount))
                                FROM transactions t
                                JOIN accounts a ON t.account_id = a.id
                                WHERE t.category_id = b.category_id
                                  AND a.user_id = ?
                                  AND t.amount < 0
                                  AND strftime('%m', t.date) = printf('%02d', ?)
                                  AND strftime('%Y', t.date) = CAST(? AS TEXT)), 0) AS actual_spending
               FROM budgets b JOIN categories c ON b.category_id = c.id
               WHERE b.user_id=? AND b.month=? AND b.year=?
               ORDER BY c.name""",
            (user_id, month, year, user_id, month, year),
        )

    def upsert_budget(self, user_id: int, category_id: int, month: int, year: int, amount: float) -> int:
        return self._execute(
            "INSERT INTO budgets (user_id, category_id, month, year, budget_amount) VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id, category_id, month, year) DO UPDATE SET budget_amount=excluded.budget_amount",
            (user_id, category_id, month, year, amount),
        )

    def delete_budget(self, budget_id: int) -> None:
        self._execute("DELETE FROM budgets WHERE id=?", (budget_id,))

    # ── Financial Goals ───────────────────────────────────────────────────────

    def get_goals(self, user_id: int) -> list[dict]:
        return self._fetchall("SELECT * FROM financial_goals WHERE user_id=? ORDER BY target_date", (user_id,))

    def create_goal(self, user_id: int, name: str, target: float, current: float, target_date: str) -> int:
        return self._execute(
            "INSERT INTO financial_goals (user_id, goal_name, target_amount, current_amount, target_date) VALUES (?,?,?,?,?)",
            (user_id, name, target, current, target_date),
        )

    def update_goal(self, goal_id: int, name: str, target: float, current: float, target_date: str) -> None:
        self._execute(
            "UPDATE financial_goals SET goal_name=?, target_amount=?, current_amount=?, target_date=? WHERE id=?",
            (name, target, current, target_date, goal_id),
        )

    def delete_goal(self, goal_id: int) -> None:
        self._execute("DELETE FROM financial_goals WHERE id=?", (goal_id,))

    # ── Recurring Transactions ────────────────────────────────────────────────

    def get_recurring(self, user_id: int) -> list[dict]:
        return self._fetchall(
            """SELECT r.*, c.name AS category_name, a.account_name
               FROM recurring_transactions r
               LEFT JOIN categories c ON r.category_id = c.id
               LEFT JOIN accounts a ON r.account_id = a.id
               WHERE r.user_id=? ORDER BY r.next_due_date""",
            (user_id,),
        )

    def create_recurring(
        self,
        user_id: int,
        name: str,
        amount: float,
        frequency: str,
        next_due_date: str,
        category_id: Optional[int] = None,
        account_id: Optional[int] = None,
    ) -> int:
        return self._execute(
            "INSERT INTO recurring_transactions (user_id, name, amount, frequency, next_due_date, category_id, account_id) VALUES (?,?,?,?,?,?,?)",
            (user_id, name, amount, frequency, next_due_date, category_id, account_id),
        )

    def update_recurring(
        self,
        rec_id: int,
        name: str,
        amount: float,
        frequency: str,
        next_due_date: str,
        category_id: Optional[int],
        account_id: Optional[int],
    ) -> None:
        self._execute(
            "UPDATE recurring_transactions SET name=?, amount=?, frequency=?, next_due_date=?, category_id=?, account_id=? WHERE id=?",
            (name, amount, frequency, next_due_date, category_id, account_id, rec_id),
        )

    def delete_recurring(self, rec_id: int) -> None:
        self._execute("DELETE FROM recurring_transactions WHERE id=?", (rec_id,))

    # ── Reporting queries ─────────────────────────────────────────────────────

    def get_monthly_summary(self, user_id: int, month: int, year: int) -> dict:
        """Return income, expenses, savings for a given month."""
        sql = """
            SELECT c.type, COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE a.user_id = ?
              AND strftime('%m', t.date) = printf('%02d', ?)
              AND strftime('%Y', t.date) = CAST(? AS TEXT)
            GROUP BY c.type
        """
        rows = self._fetchall(sql, (user_id, month, year))
        result = {"income": 0.0, "expenses": 0.0}
        for r in rows:
            if r["type"] == "Income":
                result["income"] = abs(r["total"])
            elif r["type"] == "Expense":
                result["expenses"] = abs(r["total"])
        result["savings"] = result["income"] - result["expenses"]
        result["savings_rate"] = (result["savings"] / result["income"] * 100) if result["income"] > 0 else 0.0
        return result

    def get_spending_by_category(self, user_id: int, month: int, year: int) -> list[dict]:
        return self._fetchall(
            """SELECT c.name, c.color, ABS(SUM(t.amount)) AS total
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               JOIN categories c ON t.category_id = c.id
               WHERE a.user_id=? AND c.type='Expense'
                 AND strftime('%m', t.date) = printf('%02d', ?)
                 AND strftime('%Y', t.date) = CAST(? AS TEXT)
               GROUP BY c.id ORDER BY total DESC""",
            (user_id, month, year),
        )

    def get_monthly_totals(self, user_id: int, year: int) -> list[dict]:
        """12-month income/expense breakdown for a given year."""
        return self._fetchall(
            """SELECT strftime('%m', t.date) AS month,
                      SUM(CASE WHEN c.type='Income' THEN ABS(t.amount) ELSE 0 END) AS income,
                      SUM(CASE WHEN c.type='Expense' THEN ABS(t.amount) ELSE 0 END) AS expenses
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               LEFT JOIN categories c ON t.category_id = c.id
               WHERE a.user_id=? AND strftime('%Y', t.date)=CAST(? AS TEXT)
               GROUP BY month ORDER BY month""",
            (user_id, year),
        )

    def get_total_balance(self, user_id: int) -> float:
        row = self._fetchone(
            "SELECT COALESCE(SUM(current_balance), 0) AS bal FROM accounts WHERE user_id=?",
            (user_id,),
        )
        return row["bal"] if row else 0.0
