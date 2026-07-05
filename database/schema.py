"""
database/schema.py
Defines SQL schema strings and the DatabaseManager class for all SQLite operations.
Uses parameterized queries throughout to prevent SQL injection.
"""

import sqlite3
import os
import json
import hashlib
import threading
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta


def _money(value: Optional[float]) -> float:
    """Round a monetary value to whole cents before it is stored.

    Money is kept as SQLite REAL (binary float), which can't represent most
    decimal cents exactly. Rounding every amount to 2 places as it's written —
    and pinning the running balance with SQL ``ROUND(..., 2)`` on each update —
    keeps stored data on exact cent boundaries, so summing the rows and the
    account's running balance can't drift apart by fractions of a cent.
    """
    return round(value or 0.0, 2)


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
    language    TEXT    NOT NULL DEFAULT 'en',
    font_scale  REAL    NOT NULL DEFAULT 1.0,
    accent      TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name    TEXT    NOT NULL,
    account_type    TEXT    NOT NULL CHECK(account_type IN ('Checking','Savings','Credit Card','Cash')),
    current_balance REAL    NOT NULL DEFAULT 0.0,
    currency        TEXT    NOT NULL DEFAULT 'CAD'
);

-- Cached exchange rates: 1 unit of `base` = `rate` units of `quote`.
-- Refreshed from the keyless market providers; kept so conversion still works
-- offline using the last known rate. Both directions are stored on update.
CREATE TABLE IF NOT EXISTS fx_rates (
    base    TEXT NOT NULL,
    quote   TEXT NOT NULL,
    rate    REAL NOT NULL,
    updated TEXT NOT NULL,
    PRIMARY KEY (base, quote)
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
    end_date        TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    category_id     INTEGER REFERENCES categories(id),
    account_id      INTEGER REFERENCES accounts(id),
    to_account_id   INTEGER REFERENCES accounts(id)
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

CREATE TABLE IF NOT EXISTS watchlist (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol          TEXT    NOT NULL,
    asset_type      TEXT    NOT NULL CHECK(asset_type IN ('Stock','Crypto')),
    provider_id     TEXT,
    display_name    TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    last_price      REAL,
    last_change_pct REAL,
    last_currency   TEXT,
    last_updated    TEXT,
    UNIQUE(user_id, symbol, asset_type)
);

-- Auto-categorization rules: case-insensitive substring match on a
-- transaction's description ("NETFLIX" -> Subscriptions). Longest matching
-- pattern wins, so specific rules beat generic ones.
CREATE TABLE IF NOT EXISTS category_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern     TEXT    NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_category_rules_user ON category_rules(user_id);

-- One-time password recovery codes (bcrypt hashes only — never plaintext).
-- A used code keeps its row with used_at set, so "codes remaining" is honest
-- and the audit trail of resets stays reconstructable.
CREATE TABLE IF NOT EXISTS recovery_codes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash   TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    used_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_recovery_user ON recovery_codes(user_id);

-- Append-only audit trail. Every create/update/delete the app performs is
-- recorded here for export. Intentionally NOT foreign-keyed to the rows it
-- references, so the history survives even after the underlying row is deleted.
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    user_id     INTEGER,
    entity      TEXT    NOT NULL,
    entity_id   INTEGER,
    action      TEXT    NOT NULL CHECK(action IN ('INSERT','UPDATE','DELETE')),
    details     TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp);
"""

# ── Default seed data ─────────────────────────────────────────────────────────

# Name of the system category used to record savings interest / investment gains.
INTEREST_CATEGORY_NAME = "Interest"

DEFAULT_CATEGORIES = [
    # Income
    ("Salary",       "Income",  "#4CAF50"),
    ("Freelance",    "Income",  "#8BC34A"),
    ("Investment",   "Income",  "#009688"),
    ("Interest",     "Income",  "#00D4AA"),
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

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # Per-instance, per-thread connection cache. Must NOT be a class
        # attribute — otherwise multiple DatabaseManager instances in one
        # process (e.g. the test suite) would share a single connection.
        self._local = threading.local()
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
        self._ensure_system_categories(conn)

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

        # v1.0.2 — add transfer_id to transactions if missing
        txn_cols = [r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()]
        if "transfer_id" not in txn_cols:
            conn.execute(
                "ALTER TABLE transactions ADD COLUMN transfer_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL"
            )
            conn.commit()

        # v1.0.3 — add to_account_id to recurring_transactions if missing
        rec_cols = [r[1] for r in conn.execute("PRAGMA table_info(recurring_transactions)").fetchall()]
        if "to_account_id" not in rec_cols:
            conn.execute(
                "ALTER TABLE recurring_transactions ADD COLUMN to_account_id INTEGER REFERENCES accounts(id)"
            )
            conn.commit()

        # v1.0.7 — add optional end_date to recurring_transactions if missing.
        # NULL means "no end date" (runs indefinitely), preserving prior behavior.
        if "end_date" not in rec_cols:
            conn.execute(
                "ALTER TABLE recurring_transactions ADD COLUMN end_date TEXT"
            )
            conn.commit()

        # v1.0.8 — add is_active flag to recurring_transactions if missing.
        # 1 = active (default, prior behavior); 0 = paused (skipped when posting).
        if "is_active" not in rec_cols:
            conn.execute(
                "ALTER TABLE recurring_transactions ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
            )
            conn.commit()

        # v1.0.4 — add language preference to users if missing
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "language" not in user_cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'en'"
            )
            conn.commit()

        # v1.0.6 — add theme preference to users if missing (mirrors language)
        if "theme" not in user_cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN theme TEXT NOT NULL DEFAULT 'dark'"
            )
            conn.commit()

        # v1.0.10 — personalization: font scale (0.9–1.25, default 1.0) and an
        # optional custom accent color (NULL = the theme's own accent).
        if "font_scale" not in user_cols:
            conn.execute(
                "ALTER TABLE users ADD COLUMN font_scale REAL NOT NULL DEFAULT 1.0"
            )
            conn.commit()
        if "accent" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN accent TEXT")
            conn.commit()

        # v1.0.9 — per-account currency (multi-currency accounts). Existing
        # accounts inherit their owner's home currency, so upgraded databases
        # show exactly the same numbers as before the migration.
        acct_cols = [r[1] for r in conn.execute("PRAGMA table_info(accounts)").fetchall()]
        if "currency" not in acct_cols:
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN currency TEXT NOT NULL DEFAULT 'CAD'"
            )
            conn.execute(
                "UPDATE accounts SET currency = COALESCE("
                "(SELECT u.currency FROM users u WHERE u.id = accounts.user_id), 'CAD')"
            )
            conn.commit()

        # v1.0.5 — performance indexes for the hot query paths.
        # The main transaction list joins transactions→accounts, filters by
        # user/date/category/account and sorts by date; without indexes every
        # call is a full scan. UNIQUE constraints already index budgets and
        # watchlist, so we only add the non-unique foreign-key / filter columns.
        # CREATE INDEX IF NOT EXISTS is idempotent, so this is safe on every init.
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_transactions_account_date
                ON transactions(account_id, date);
            CREATE INDEX IF NOT EXISTS idx_transactions_category
                ON transactions(category_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_transfer
                ON transactions(transfer_id);
            CREATE INDEX IF NOT EXISTS idx_accounts_user
                ON accounts(user_id);
            CREATE INDEX IF NOT EXISTS idx_recurring_user
                ON recurring_transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_goals_user
                ON financial_goals(user_id);
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

    def _ensure_system_categories(self, conn: sqlite3.Connection) -> None:
        """Ensure required system categories exist (idempotent, for existing DBs)."""
        row = conn.execute(
            "SELECT 1 FROM categories WHERE name=? AND type='Income'",
            (INTEREST_CATEGORY_NAME,),
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO categories (name, type, color) VALUES (?,?,?)",
                (INTEREST_CATEGORY_NAME, "Income", "#00D4AA"),
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

    # ── Audit log ─────────────────────────────────────────────────────────────

    def _log(self, action: str, entity: str, entity_id: Optional[int] = None,
             details: Optional[dict] = None, user_id: Optional[int] = None) -> None:
        """Record a create/update/delete in the audit_log table.

        Best-effort: auditing must never break a real operation, so any failure
        here is swallowed. ``details`` is stored as a compact JSON snapshot.
        """
        try:
            conn = self._conn()
            conn.execute(
                "INSERT INTO audit_log (timestamp, user_id, entity, entity_id, action, details) "
                "VALUES (?,?,?,?,?,?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    user_id, entity, entity_id, action,
                    json.dumps(details, default=str) if details is not None else None,
                ),
            )
            conn.commit()
        except Exception:
            pass

    def get_audit_log(self, limit: Optional[int] = None) -> list[dict]:
        """Return audit-log rows, newest first (all rows unless *limit* given)."""
        sql = "SELECT * FROM audit_log ORDER BY id DESC"
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (int(limit),)
        return self._fetchall(sql, params)

    # ── Users ─────────────────────────────────────────────────────────────────

    def create_user(self, name: str, email: str, password_hash: str, currency: str = "CAD") -> int:
        uid = self._execute(
            "INSERT INTO users (name, email, password, currency) VALUES (?,?,?,?)",
            (name, email, password_hash, currency),
        )
        self._log("INSERT", "user", uid, {"name": name, "email": email, "currency": currency}, user_id=uid)
        return uid

    def get_user_by_email(self, email: str) -> Optional[dict]:
        return self._fetchone("SELECT * FROM users WHERE email=?", (email,))

    def get_user(self, user_id: int) -> Optional[dict]:
        return self._fetchone("SELECT * FROM users WHERE id=?", (user_id,))

    def update_user(self, user_id: int, name: str, currency: str) -> None:
        self._execute("UPDATE users SET name=?, currency=? WHERE id=?", (name, currency, user_id))
        self._log("UPDATE", "user", user_id, {"name": name, "currency": currency}, user_id=user_id)

    def update_user_language(self, user_id: int, language: str) -> None:
        self._execute("UPDATE users SET language=? WHERE id=?", (language, user_id))
        self._log("UPDATE", "user", user_id, {"language": language}, user_id=user_id)

    def update_user_theme(self, user_id: int, theme: str) -> None:
        self._execute("UPDATE users SET theme=? WHERE id=?", (theme, user_id))
        self._log("UPDATE", "user", user_id, {"theme": theme}, user_id=user_id)

    def update_user_font_scale(self, user_id: int, scale: float) -> None:
        self._execute("UPDATE users SET font_scale=? WHERE id=?", (scale, user_id))
        self._log("UPDATE", "user", user_id, {"font_scale": scale}, user_id=user_id)

    def update_user_accent(self, user_id: int, accent: Optional[str]) -> None:
        """Set (or clear, with None) the user's custom accent color."""
        self._execute("UPDATE users SET accent=? WHERE id=?", (accent, user_id))
        self._log("UPDATE", "user", user_id, {"accent": accent}, user_id=user_id)

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        self._execute("UPDATE users SET password=? WHERE id=?", (password_hash, user_id))
        # Never log the hash itself — only that a password change happened.
        self._log("UPDATE", "user", user_id, {"password": "changed"}, user_id=user_id)

    # ── Recovery codes ────────────────────────────────────────────────────────

    def replace_recovery_codes(self, user_id: int, code_hashes: list[str]) -> None:
        """Replace the user's recovery codes with a fresh set (hashes only)."""
        conn = self._conn()
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute("DELETE FROM recovery_codes WHERE user_id=?", (user_id,))
        conn.executemany(
            "INSERT INTO recovery_codes (user_id, code_hash, created_at) VALUES (?,?,?)",
            [(user_id, h, now) for h in code_hashes],
        )
        conn.commit()
        # Like passwords, the hashes themselves are deliberately not logged.
        self._log("UPDATE", "user", user_id,
                  {"recovery_codes": f"regenerated ({len(code_hashes)})"}, user_id=user_id)

    def get_unused_recovery_codes(self, user_id: int) -> list[dict]:
        return self._fetchall(
            "SELECT * FROM recovery_codes WHERE user_id=? AND used_at IS NULL",
            (user_id,),
        )

    def count_unused_recovery_codes(self, user_id: int) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) AS n FROM recovery_codes WHERE user_id=? AND used_at IS NULL",
            (user_id,),
        )
        return int(row["n"]) if row else 0

    def mark_recovery_code_used(self, code_id: int, user_id: Optional[int] = None) -> None:
        self._execute(
            "UPDATE recovery_codes SET used_at=? WHERE id=?",
            (datetime.now().isoformat(timespec="seconds"), code_id),
        )
        self._log("UPDATE", "user", user_id,
                  {"recovery_code": "used for password reset"}, user_id=user_id)

    # ── FX rates / currency conversion ───────────────────────────────────────

    # SQL fragment: multiplier that converts an amount in account `a`'s currency
    # into the home currency bound to the adjacent `?` parameter. Falls back to
    # 1.0 when no rate is cached — i.e. same currency, or FX never fetched yet.
    _FX = ("COALESCE((SELECT fx.rate FROM fx_rates fx "
           "WHERE fx.base = a.currency AND fx.quote = ?), 1.0)")

    def get_home_currency(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return (user or {}).get("currency") or "CAD"

    def set_fx_rate(self, base: str, quote: str, rate: float) -> None:
        """Cache an exchange rate (1 base = rate quote), plus its inverse so
        conversion keeps working if the user's home currency ever changes."""
        base, quote = base.upper(), quote.upper()
        if base == quote or rate <= 0:
            return
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._conn()
        for b, q, r in ((base, quote, rate), (quote, base, 1.0 / rate)):
            conn.execute(
                "INSERT INTO fx_rates (base, quote, rate, updated) VALUES (?,?,?,?) "
                "ON CONFLICT(base, quote) DO UPDATE SET rate=excluded.rate, updated=excluded.updated",
                (b, q, r, now),
            )
        conn.commit()

    def get_cached_fx_rate(self, base: str, quote: str) -> Optional[dict]:
        """Last cached rate row for base→quote, or None. Same currency → 1.0."""
        base, quote = base.upper(), quote.upper()
        if base == quote:
            return {"base": base, "quote": quote, "rate": 1.0, "updated": None}
        return self._fetchone(
            "SELECT * FROM fx_rates WHERE base=? AND quote=?", (base, quote)
        )

    def get_fx_rates(self) -> list[dict]:
        return self._fetchall("SELECT * FROM fx_rates ORDER BY base, quote")

    def convert_amount(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert using the cached rate; 1:1 when no rate is known (graceful
        offline fallback — totals stay usable, just unconverted)."""
        row = self.get_cached_fx_rate(from_currency, to_currency)
        rate = row["rate"] if row else 1.0
        return round(amount * rate, 2)

    def get_account_currencies(self, user_id: int) -> list[str]:
        """Distinct currencies across the user's accounts."""
        return [
            r["currency"]
            for r in self._fetchall(
                "SELECT DISTINCT currency FROM accounts WHERE user_id=? ORDER BY currency",
                (user_id,),
            )
        ]

    # ── Accounts ──────────────────────────────────────────────────────────────

    def get_accounts(self, user_id: int) -> list[dict]:
        return self._fetchall("SELECT * FROM accounts WHERE user_id=? ORDER BY account_name", (user_id,))

    def get_account(self, account_id: int) -> Optional[dict]:
        return self._fetchone("SELECT * FROM accounts WHERE id=?", (account_id,))

    def create_account(self, user_id: int, name: str, acct_type: str, balance: float = 0.0,
                       currency: Optional[str] = None) -> int:
        currency = (currency or self.get_home_currency(user_id)).upper()
        aid = self._execute(
            "INSERT INTO accounts (user_id, account_name, account_type, current_balance, currency) VALUES (?,?,?,?,?)",
            (user_id, name, acct_type, _money(balance), currency),
        )
        self._log("INSERT", "account", aid,
                  {"name": name, "type": acct_type, "balance": _money(balance),
                   "currency": currency}, user_id=user_id)
        return aid

    def update_account(self, account_id: int, name: str, acct_type: str, balance: float,
                       currency: Optional[str] = None) -> None:
        """Update an account. ``currency`` relabels the account; the balance and
        its transactions are NOT converted (they were always in that currency)."""
        if currency is None:
            old = self.get_account(account_id)
            currency = (old or {}).get("currency") or "CAD"
        currency = currency.upper()
        self._execute(
            "UPDATE accounts SET account_name=?, account_type=?, current_balance=?, currency=? WHERE id=?",
            (name, acct_type, _money(balance), currency, account_id),
        )
        self._log("UPDATE", "account", account_id,
                  {"name": name, "type": acct_type, "balance": _money(balance),
                   "currency": currency})

    def delete_account(self, account_id: int) -> None:
        old = self.get_account(account_id)
        self._execute("DELETE FROM accounts WHERE id=?", (account_id,))
        self._log("DELETE", "account", account_id,
                  {"name": old["account_name"], "balance": old["current_balance"]} if old else None)

    def update_account_balance(self, account_id: int, delta: float) -> None:
        self._execute(
            "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
            (_money(delta), account_id),
        )

    # ── Categories ────────────────────────────────────────────────────────────

    def get_categories(self, cat_type: Optional[str] = None) -> list[dict]:
        if cat_type:
            return self._fetchall("SELECT * FROM categories WHERE type=? ORDER BY name", (cat_type,))
        return self._fetchall("SELECT * FROM categories ORDER BY type, name")

    def get_category(self, category_id: int) -> Optional[dict]:
        return self._fetchone("SELECT * FROM categories WHERE id=?", (category_id,))

    def create_category(self, name: str, cat_type: str, color: str) -> int:
        cid = self._execute(
            "INSERT INTO categories (name, type, color) VALUES (?,?,?)",
            (name, cat_type, color),
        )
        self._log("INSERT", "category", cid, {"name": name, "type": cat_type, "color": color})
        return cid

    def update_category(self, category_id: int, name: str, cat_type: str, color: str) -> None:
        self._execute(
            "UPDATE categories SET name=?, type=?, color=? WHERE id=?",
            (name, cat_type, color, category_id),
        )
        self._log("UPDATE", "category", category_id, {"name": name, "type": cat_type, "color": color})

    def delete_category(self, category_id: int) -> None:
        old = self.get_category(category_id)
        self._execute("DELETE FROM categories WHERE id=?", (category_id,))
        self._log("DELETE", "category", category_id, {"name": old["name"]} if old else None)

    # ── Auto-categorization rules ─────────────────────────────────────────────

    def get_category_rules(self, user_id: int) -> list[dict]:
        """The user's rules with the target category's name/color for display."""
        return self._fetchall(
            """SELECT r.*, c.name AS category_name, c.color AS category_color,
                      c.type AS category_type
               FROM category_rules r
               JOIN categories c ON c.id = r.category_id
               WHERE r.user_id=? ORDER BY LOWER(r.pattern)""",
            (user_id,),
        )

    def create_category_rule(self, user_id: int, pattern: str, category_id: int) -> int:
        rid = self._execute(
            "INSERT INTO category_rules (user_id, pattern, category_id) VALUES (?,?,?)",
            (user_id, pattern.strip(), category_id),
        )
        self._log("INSERT", "category_rule", rid,
                  {"pattern": pattern.strip(), "category_id": category_id}, user_id=user_id)
        return rid

    def update_category_rule(self, rule_id: int, pattern: str, category_id: int,
                             user_id: Optional[int] = None) -> None:
        self._execute(
            "UPDATE category_rules SET pattern=?, category_id=? WHERE id=?",
            (pattern.strip(), category_id, rule_id),
        )
        self._log("UPDATE", "category_rule", rule_id,
                  {"pattern": pattern.strip(), "category_id": category_id}, user_id=user_id)

    def delete_category_rule(self, rule_id: int, user_id: Optional[int] = None) -> None:
        old = self._fetchone("SELECT * FROM category_rules WHERE id=?", (rule_id,))
        self._execute("DELETE FROM category_rules WHERE id=?", (rule_id,))
        self._log("DELETE", "category_rule", rule_id,
                  {"pattern": old["pattern"]} if old else None, user_id=user_id)

    def match_category_rule(self, user_id: int, description: str) -> Optional[int]:
        """Category id whose rule matches *description*, or None.

        Case-insensitive substring match. When several rules match, the
        longest pattern wins (most specific); ties go to the oldest rule so
        results stay deterministic.
        """
        desc = (description or "").lower().strip()
        if not desc:
            return None
        best_key: Optional[tuple[int, int]] = None
        best_cat: Optional[int] = None
        for r in self._fetchall(
            "SELECT id, pattern, category_id FROM category_rules WHERE user_id=?",
            (user_id,),
        ):
            p = (r["pattern"] or "").lower().strip()
            if p and p in desc:
                key = (len(p), -r["id"])
                if best_key is None or key > best_key:
                    best_key, best_cat = key, r["category_id"]
        return best_cat

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
                   a.account_name, a.account_type, a.currency AS account_currency
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
                      a.account_name, a.currency AS account_currency
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               LEFT JOIN categories c ON t.category_id = c.id
               WHERE t.id=?""",
            (transaction_id,),
        )

    def search_transactions(self, user_id: int, query: str, limit: int = 200) -> list[dict]:
        """Global search across all accounts and dates (powers Ctrl+F).

        A numeric query matches the amount (absolute value, so "15.99" finds
        both the expense and a refund); anything else searches description and
        notes, case-insensitively. Newest first, capped at *limit*.
        """
        q = (query or "").strip()
        if not q:
            return []
        try:
            value = abs(float(q.replace(",", ".")))
        except ValueError:
            return self.get_transactions(user_id, keyword=q, limit=limit)
        return self._fetchall(
            f"""SELECT t.*, c.name AS category_name, c.type AS category_type,
                       c.color AS category_color,
                       a.account_name, a.account_type, a.currency AS account_currency
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE a.user_id = ? AND ABS(ABS(t.amount) - ?) < 0.005
                ORDER BY t.date DESC, t.id DESC LIMIT {int(limit)}""",
            (user_id, value),
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
        amount = _money(amount)
        cur = conn.execute(
            "INSERT INTO transactions (account_id, category_id, date, description, amount, notes, recurring_id) VALUES (?,?,?,?,?,?,?)",
            (account_id, category_id, date, description, amount, notes, recurring_id),
        )
        conn.execute(
            "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
            (amount, account_id),
        )
        conn.commit()
        self._log("INSERT", "transaction", cur.lastrowid, {
            "account_id": account_id, "category_id": category_id, "date": date,
            "description": description, "amount": amount, "recurring_id": recurring_id,
        })
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
        amount = _money(amount)
        old = conn.execute("SELECT account_id, amount FROM transactions WHERE id=?", (txn_id,)).fetchone()
        if old:
            conn.execute(
                "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
                (-old["amount"], old["account_id"]),
            )
        conn.execute(
            "UPDATE transactions SET account_id=?, category_id=?, date=?, description=?, amount=?, notes=? WHERE id=?",
            (account_id, category_id, date, description, amount, notes, txn_id),
        )
        conn.execute(
            "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
            (amount, account_id),
        )
        conn.commit()
        self._log("UPDATE", "transaction", txn_id, {
            "account_id": account_id, "category_id": category_id, "date": date,
            "description": description, "amount": amount,
        })

    def delete_transaction(self, txn_id: int) -> None:
        conn = self._conn()
        old = conn.execute(
            "SELECT account_id, category_id, date, description, amount FROM transactions WHERE id=?",
            (txn_id,),
        ).fetchone()
        if old:
            conn.execute(
                "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
                (-old["amount"], old["account_id"]),
            )
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        conn.commit()
        self._log("DELETE", "transaction", txn_id, dict(old) if old else None)

    # ── Transfers ─────────────────────────────────────────────────────────────

    def create_transfer(
        self,
        from_account_id: int,
        to_account_id: int,
        amount: float,
        date: str,
        description: str,
        notes: str = "",
        to_amount: Optional[float] = None,
    ) -> tuple[int, int]:
        """Create two linked transaction legs atomically. Returns (from_id, to_id).

        ``amount`` is what leaves the source account, in its currency.
        ``to_amount`` is what arrives in the destination account, in *its*
        currency — used for cross-currency transfers. Defaults to ``amount``
        (the same-currency case).
        """
        if from_account_id == to_account_id:
            raise ValueError("Source and destination accounts must be different.")
        if amount <= 0:
            raise ValueError("Transfer amount must be greater than zero.")
        if to_amount is not None and to_amount <= 0:
            raise ValueError("Received amount must be greater than zero.")
        conn = self._conn()
        amount = _money(amount)
        to_amount = _money(to_amount) if to_amount is not None else amount
        cur_from = conn.execute(
            "INSERT INTO transactions (account_id, date, description, amount, notes) VALUES (?,?,?,?,?)",
            (from_account_id, date, description, -amount, notes),
        )
        from_id = cur_from.lastrowid
        cur_to = conn.execute(
            "INSERT INTO transactions (account_id, date, description, amount, notes, transfer_id) VALUES (?,?,?,?,?,?)",
            (to_account_id, date, description, to_amount, notes, from_id),
        )
        to_id = cur_to.lastrowid
        conn.execute("UPDATE transactions SET transfer_id=? WHERE id=?", (to_id, from_id))
        conn.execute(
            "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
            (-amount, from_account_id),
        )
        conn.execute(
            "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
            (to_amount, to_account_id),
        )
        conn.commit()
        self._log("INSERT", "transfer", from_id, {
            "from_account_id": from_account_id, "to_account_id": to_account_id,
            "amount": amount, "to_amount": to_amount, "date": date,
            "description": description,
            "from_txn_id": from_id, "to_txn_id": to_id,
        })
        return from_id, to_id

    def delete_transfer(self, txn_id: int) -> None:
        """Delete both legs of a transfer and reverse both balances atomically."""
        conn = self._conn()
        row = conn.execute(
            "SELECT id, account_id, amount, transfer_id FROM transactions WHERE id=?",
            (txn_id,),
        ).fetchone()
        if not row:
            return
        partner_id = row["transfer_id"]
        ids_to_delete = [row["id"]]
        reversals = [(row["account_id"], -row["amount"])]
        if partner_id:
            partner = conn.execute(
                "SELECT id, account_id, amount FROM transactions WHERE id=?",
                (partner_id,),
            ).fetchone()
            if partner:
                ids_to_delete.append(partner["id"])
                reversals.append((partner["account_id"], -partner["amount"]))
        for tid in ids_to_delete:
            conn.execute("UPDATE transactions SET transfer_id=NULL WHERE id=?", (tid,))
        for acct_id, delta in reversals:
            conn.execute(
                "UPDATE accounts SET current_balance = ROUND(current_balance + ?, 2) WHERE id=?",
                (delta, acct_id),
            )
        for tid in ids_to_delete:
            conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
        conn.commit()
        self._log("DELETE", "transfer", txn_id, {"deleted_txn_ids": ids_to_delete})

    # ── Budgets ───────────────────────────────────────────────────────────────

    def get_budgets(self, user_id: int, month: int, year: int) -> list[dict]:
        # Spending is converted into the user's home currency per transaction,
        # so budgets (kept in home currency) compare against a consistent total
        # even when the money left accounts held in other currencies.
        home = self.get_home_currency(user_id)
        return self._fetchall(
            f"""SELECT b.*, c.name AS category_name, c.color,
                      COALESCE((SELECT SUM(ABS(t.amount) * {self._FX})
                                FROM transactions t
                                JOIN accounts a ON t.account_id = a.id
                                WHERE t.category_id = b.category_id
                                  AND a.user_id = ?
                                  AND t.amount < 0
                                  AND t.transfer_id IS NULL
                                  AND strftime('%m', t.date) = printf('%02d', ?)
                                  AND strftime('%Y', t.date) = CAST(? AS TEXT)), 0) AS actual_spending
               FROM budgets b JOIN categories c ON b.category_id = c.id
               WHERE b.user_id=? AND b.month=? AND b.year=?
               ORDER BY c.name""",
            (home, user_id, month, year, user_id, month, year),
        )

    def get_budget_alerts(
        self, user_id: int, month: int, year: int, threshold: float = 0.9
    ) -> list[dict]:
        """
        Budgets for the given month whose spending has reached ``threshold`` of
        the limit (default 90%). Each entry adds ``ratio`` (spent / budget) and
        ``over`` (ratio >= 1.0). Sorted worst-first. Budgets of 0 are skipped.
        """
        alerts = []
        for b in self.get_budgets(user_id, month, year):
            limit = b["budget_amount"]
            if limit <= 0:
                continue
            ratio = b["actual_spending"] / limit
            if ratio >= threshold:
                alerts.append({**b, "ratio": ratio, "over": ratio >= 1.0})
        alerts.sort(key=lambda a: a["ratio"], reverse=True)
        return alerts

    def upsert_budget(self, user_id: int, category_id: int, month: int, year: int, amount: float) -> int:
        bid = self._execute(
            "INSERT INTO budgets (user_id, category_id, month, year, budget_amount) VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id, category_id, month, year) DO UPDATE SET budget_amount=excluded.budget_amount",
            (user_id, category_id, month, year, amount),
        )
        self._log("UPDATE", "budget", bid, {
            "category_id": category_id, "month": month, "year": year, "amount": amount,
        }, user_id=user_id)
        return bid

    def copy_budgets(
        self, user_id: int, from_month: int, from_year: int,
        to_month: int, to_year: int,
    ) -> int:
        """Copy budget lines from one month into another.

        Only categories that don't already have a budget in the destination
        month are added, so existing entries are never overwritten. Returns the
        number of budgets actually created.
        """
        source = self.get_budgets(user_id, from_month, from_year)
        if not source:
            return 0
        existing = {
            b["category_id"] for b in self.get_budgets(user_id, to_month, to_year)
        }
        copied = 0
        for b in source:
            if b["category_id"] in existing:
                continue
            self.upsert_budget(
                user_id, b["category_id"], to_month, to_year, b["budget_amount"]
            )
            copied += 1
        return copied

    def delete_budget(self, budget_id: int) -> None:
        self._execute("DELETE FROM budgets WHERE id=?", (budget_id,))
        self._log("DELETE", "budget", budget_id)

    # ── Financial Goals ───────────────────────────────────────────────────────

    def get_goals(self, user_id: int) -> list[dict]:
        return self._fetchall("SELECT * FROM financial_goals WHERE user_id=? ORDER BY target_date", (user_id,))

    def create_goal(self, user_id: int, name: str, target: float, current: float, target_date: str) -> int:
        gid = self._execute(
            "INSERT INTO financial_goals (user_id, goal_name, target_amount, current_amount, target_date) VALUES (?,?,?,?,?)",
            (user_id, name, target, current, target_date),
        )
        self._log("INSERT", "goal", gid, {
            "name": name, "target": target, "current": current, "target_date": target_date,
        }, user_id=user_id)
        return gid

    def update_goal(self, goal_id: int, name: str, target: float, current: float, target_date: str) -> None:
        self._execute(
            "UPDATE financial_goals SET goal_name=?, target_amount=?, current_amount=?, target_date=? WHERE id=?",
            (name, target, current, target_date, goal_id),
        )
        self._log("UPDATE", "goal", goal_id, {
            "name": name, "target": target, "current": current, "target_date": target_date,
        })

    def delete_goal(self, goal_id: int) -> None:
        self._execute("DELETE FROM financial_goals WHERE id=?", (goal_id,))
        self._log("DELETE", "goal", goal_id)

    # ── Recurring Transactions ────────────────────────────────────────────────

    def get_recurring(self, user_id: int) -> list[dict]:
        return self._fetchall(
            """SELECT r.*, c.name AS category_name,
                      a.account_name, a.currency AS account_currency,
                      ta.account_name AS to_account_name,
                      ta.currency AS to_account_currency
               FROM recurring_transactions r
               LEFT JOIN categories c ON r.category_id = c.id
               LEFT JOIN accounts a  ON r.account_id = a.id
               LEFT JOIN accounts ta ON r.to_account_id = ta.id
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
        to_account_id: Optional[int] = None,
        end_date: Optional[str] = None,
    ) -> int:
        rid = self._execute(
            "INSERT INTO recurring_transactions (user_id, name, amount, frequency, next_due_date, end_date, category_id, account_id, to_account_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, name, amount, frequency, next_due_date, end_date, category_id, account_id, to_account_id),
        )
        self._log("INSERT", "recurring", rid, {
            "name": name, "amount": amount, "frequency": frequency,
            "next_due_date": next_due_date, "end_date": end_date,
            "account_id": account_id, "to_account_id": to_account_id,
        }, user_id=user_id)
        return rid

    def update_recurring(
        self,
        rec_id: int,
        name: str,
        amount: float,
        frequency: str,
        next_due_date: str,
        category_id: Optional[int],
        account_id: Optional[int],
        to_account_id: Optional[int] = None,
        end_date: Optional[str] = None,
    ) -> None:
        self._execute(
            "UPDATE recurring_transactions SET name=?, amount=?, frequency=?, next_due_date=?, end_date=?, category_id=?, account_id=?, to_account_id=? WHERE id=?",
            (name, amount, frequency, next_due_date, end_date, category_id, account_id, to_account_id, rec_id),
        )
        self._log("UPDATE", "recurring", rec_id, {
            "name": name, "amount": amount, "frequency": frequency,
            "next_due_date": next_due_date, "end_date": end_date,
            "account_id": account_id, "to_account_id": to_account_id,
        })

    def set_recurring_active(self, rec_id: int, active: bool) -> None:
        """Pause (active=False) or resume (active=True) a recurring rule.

        A paused rule stays in the list but is skipped by ``process_due`` and the
        forecast until it is resumed, so it stops generating transactions without
        losing its history or settings.
        """
        self._execute(
            "UPDATE recurring_transactions SET is_active=? WHERE id=?",
            (1 if active else 0, rec_id),
        )
        self._log("UPDATE", "recurring", rec_id, {"is_active": 1 if active else 0})

    def get_upcoming_recurring(self, user_id: int, within_days: int = 7) -> list[dict]:
        """Active recurring rules due on or before ``today + within_days``.

        Powers the dashboard's "upcoming bills" card. Overdue rules (due before
        today, e.g. if they couldn't post) are included so they stay visible.
        Rules whose next occurrence has passed their ``end_date`` are excluded.
        Ordered soonest-due first.
        """
        horizon = (datetime.now().date() + timedelta(days=within_days)).isoformat()
        return self._fetchall(
            """SELECT r.*, c.name AS category_name,
                      a.account_name, a.currency AS account_currency,
                      ta.account_name AS to_account_name
               FROM recurring_transactions r
               LEFT JOIN categories c ON r.category_id = c.id
               LEFT JOIN accounts a  ON r.account_id = a.id
               LEFT JOIN accounts ta ON r.to_account_id = ta.id
               WHERE r.user_id = ?
                 AND r.is_active = 1
                 AND r.next_due_date <= ?
                 AND (r.end_date IS NULL OR r.next_due_date <= r.end_date)
               ORDER BY r.next_due_date, r.name""",
            (user_id, horizon),
        )

    def delete_recurring(self, rec_id: int) -> None:
        self._execute("DELETE FROM recurring_transactions WHERE id=?", (rec_id,))
        self._log("DELETE", "recurring", rec_id)

    # ── Reporting queries ─────────────────────────────────────────────────────

    def get_monthly_summary(self, user_id: int, month: int, year: int) -> dict:
        """Return income, expenses, savings for a given month (home currency)."""
        home = self.get_home_currency(user_id)
        sql = f"""
            SELECT c.type, COALESCE(SUM(t.amount * {self._FX}), 0) AS total
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE a.user_id = ?
              AND t.transfer_id IS NULL
              AND strftime('%m', t.date) = printf('%02d', ?)
              AND strftime('%Y', t.date) = CAST(? AS TEXT)
            GROUP BY c.type
        """
        rows = self._fetchall(sql, (home, user_id, month, year))
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
        home = self.get_home_currency(user_id)
        return self._fetchall(
            f"""SELECT c.name, c.color, ABS(SUM(t.amount * {self._FX})) AS total
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               JOIN categories c ON t.category_id = c.id
               WHERE a.user_id=? AND c.type='Expense'
                 AND t.transfer_id IS NULL
                 AND strftime('%m', t.date) = printf('%02d', ?)
                 AND strftime('%Y', t.date) = CAST(? AS TEXT)
               GROUP BY c.id ORDER BY total DESC""",
            (home, user_id, month, year),
        )

    def get_monthly_totals(self, user_id: int, year: int) -> list[dict]:
        """12-month income/expense breakdown for a given year (home currency)."""
        home = self.get_home_currency(user_id)
        return self._fetchall(
            f"""SELECT strftime('%m', t.date) AS month,
                      SUM(CASE WHEN c.type='Income' THEN ABS(t.amount * {self._FX}) ELSE 0 END) AS income,
                      SUM(CASE WHEN c.type='Expense' THEN ABS(t.amount * {self._FX}) ELSE 0 END) AS expenses
               FROM transactions t
               JOIN accounts a ON t.account_id = a.id
               LEFT JOIN categories c ON t.category_id = c.id
               WHERE a.user_id=? AND t.transfer_id IS NULL
               AND strftime('%Y', t.date)=CAST(? AS TEXT)
               GROUP BY month ORDER BY month""",
            (home, home, user_id, year),
        )

    def get_total_balance(self, user_id: int) -> float:
        """Combined balance of every account, converted to the home currency."""
        home = self.get_home_currency(user_id)
        row = self._fetchone(
            f"SELECT COALESCE(SUM(ROUND(a.current_balance * {self._FX}, 2)), 0) AS bal "
            "FROM accounts a WHERE a.user_id=?",
            (home, user_id),
        )
        return row["bal"] if row else 0.0

    def get_net_worth_history(self, user_id: int, months: int = 12) -> list[dict]:
        """
        Reconstruct end-of-month total net worth for the last ``months`` months.

        Account balances already reflect every transaction, so the current total
        balance is the net worth as of today. Earlier points are reconstructed by
        unwinding each month's net transaction flow:
            end_of_month(M-1) = end_of_month(M) - flow(M)
        Everything is expressed in the user's home currency: each flow converts
        at the account's *current* cached rate (historical rates aren't stored,
        so past points are an approximation for foreign-currency accounts).
        Same-currency transfers net to zero across the two legs; cross-currency
        legs cancel up to the drift between the transfer's rate and today's.
        Returns a chronological list of ``{"month": "YYYY-MM", "balance": float}``.
        """
        if months < 1:
            return []

        home = self.get_home_currency(user_id)

        # Net signed transaction flow per month (income +, expense -), converted.
        flows = {
            r["ym"]: r["flow"]
            for r in self._fetchall(
                f"""SELECT strftime('%Y-%m', t.date) AS ym,
                          COALESCE(SUM(t.amount * {self._FX}), 0) AS flow
                   FROM transactions t
                   JOIN accounts a ON t.account_id = a.id
                   WHERE a.user_id = ?
                   GROUP BY ym""",
                (home, user_id),
            )
        }

        # Build the list of target months, oldest -> current.
        now = datetime.now()
        y, m = now.year, now.month
        month_keys: list[str] = []
        for _ in range(months):
            month_keys.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        month_keys.reverse()

        # Walk backward from the current balance, unwinding each month's flow.
        balance = self.get_total_balance(user_id)
        balances: dict[str, float] = {}
        cursor = f"{now.year:04d}-{now.month:02d}"
        oldest = month_keys[0]
        while True:
            balances[cursor] = round(balance, 2)
            if cursor <= oldest:
                break
            balance -= flows.get(cursor, 0.0)  # step back one month
            cy, cm = int(cursor[:4]), int(cursor[5:])
            cm -= 1
            if cm == 0:
                cm, cy = 12, cy - 1
            cursor = f"{cy:04d}-{cm:02d}"

        return [{"month": k, "balance": balances.get(k, 0.0)} for k in month_keys]

    # ── Savings / Interest ─────────────────────────────────────────────────────

    def get_category_by_name(self, name: str) -> Optional[dict]:
        return self._fetchone("SELECT * FROM categories WHERE name=?", (name,))

    def get_interest_category_id(self) -> Optional[int]:
        """Return the id of the system 'Interest' category, if present."""
        cat = self.get_category_by_name(INTEREST_CATEGORY_NAME)
        return cat["id"] if cat else None

    def get_savings_accounts(self, user_id: int) -> list[dict]:
        return self._fetchall(
            "SELECT * FROM accounts WHERE user_id=? AND account_type='Savings' ORDER BY account_name",
            (user_id,),
        )

    def get_interest_summary(self, user_id: int, month: int, year: int) -> list[dict]:
        """
        Per savings-account interest totals for a given month/year plus all-time,
        alongside the account's current balance. Interest = transactions recorded
        under the system 'Interest' category (signed: gains +, losses −).
        """
        interest_id = self.get_interest_category_id()
        if interest_id is None:
            return []
        ym = f"{year:04d}-{month:02d}"
        yr = f"{year:04d}"
        return self._fetchall(
            """
            SELECT a.id, a.account_name, a.current_balance, a.currency,
                   COALESCE(SUM(CASE WHEN strftime('%Y-%m', t.date)=? THEN t.amount END), 0) AS interest_month,
                   COALESCE(SUM(CASE WHEN strftime('%Y',    t.date)=? THEN t.amount END), 0) AS interest_year,
                   COALESCE(SUM(t.amount), 0) AS interest_total
            FROM accounts a
            LEFT JOIN transactions t
                   ON t.account_id = a.id AND t.category_id = ?
            WHERE a.user_id = ? AND a.account_type = 'Savings'
            GROUP BY a.id
            ORDER BY a.account_name
            """,
            (ym, yr, interest_id, user_id),
        )

    def get_interest_monthly(self, user_id: int, year: int) -> list[dict]:
        """12-month interest totals across all savings accounts (home currency)."""
        interest_id = self.get_interest_category_id()
        if interest_id is None:
            return []
        home = self.get_home_currency(user_id)
        return self._fetchall(
            f"""
            SELECT strftime('%m', t.date) AS month, SUM(t.amount * {self._FX}) AS interest
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? AND a.account_type = 'Savings'
              AND t.category_id = ?
              AND strftime('%Y', t.date) = CAST(? AS TEXT)
            GROUP BY month ORDER BY month
            """,
            (home, user_id, interest_id, year),
        )

    def get_interest_entries(self, user_id: int, limit: int = 50) -> list[dict]:
        """Recent interest entries across all savings accounts (history)."""
        interest_id = self.get_interest_category_id()
        if interest_id is None:
            return []
        return self._fetchall(
            """
            SELECT t.id, t.date, t.amount, a.account_name, a.currency
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? AND a.account_type = 'Savings'
              AND t.category_id = ?
            ORDER BY t.date DESC, t.id DESC
            LIMIT ?
            """,
            (user_id, interest_id, int(limit)),
        )

    def record_interest(self, account_id: int, amount: float, date: str, note: str = "") -> int:
        """Post a signed interest/gain transaction (also updates the balance)."""
        interest_id = self.get_interest_category_id()
        return self.create_transaction(
            account_id=account_id,
            category_id=interest_id,
            date=date,
            description=INTEREST_CATEGORY_NAME,
            amount=amount,
            notes=note or "Auto-recorded from balance update",
        )

    # ── Watchlist (Markets) ────────────────────────────────────────────────────

    def get_watchlist(self, user_id: int) -> list[dict]:
        return self._fetchall(
            "SELECT * FROM watchlist WHERE user_id=? ORDER BY sort_order, asset_type, symbol",
            (user_id,),
        )

    def add_watch(
        self,
        user_id: int,
        symbol: str,
        asset_type: str,
        provider_id: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> int:
        """Add a symbol to the watchlist (ignores duplicates). Returns row id (or existing)."""
        symbol = symbol.strip().upper()
        existing = self._fetchone(
            "SELECT id FROM watchlist WHERE user_id=? AND symbol=? AND asset_type=?",
            (user_id, symbol, asset_type),
        )
        if existing:
            return existing["id"]
        wid = self._execute(
            "INSERT INTO watchlist (user_id, symbol, asset_type, provider_id, display_name) "
            "VALUES (?,?,?,?,?)",
            (user_id, symbol, asset_type, provider_id, display_name),
        )
        self._log("INSERT", "watchlist", wid, {"symbol": symbol, "asset_type": asset_type}, user_id=user_id)
        return wid

    def remove_watch(self, watch_id: int) -> None:
        self._execute("DELETE FROM watchlist WHERE id=?", (watch_id,))
        self._log("DELETE", "watchlist", watch_id)

    def update_watch_cache(
        self,
        watch_id: int,
        price: Optional[float],
        change_pct: Optional[float],
        currency: str,
        updated: str,
    ) -> None:
        """Persist the last fetched quote so it shows instantly on next launch."""
        self._execute(
            "UPDATE watchlist SET last_price=?, last_change_pct=?, last_currency=?, last_updated=? WHERE id=?",
            (price, change_pct, currency, updated, watch_id),
        )
