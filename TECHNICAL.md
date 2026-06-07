# Budget Manager — Technical Documentation

> **Version:** 1.0.1 · **Python:** 3.12+ · **Last updated:** June 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Architecture](#4-architecture)
5. [Database Schema](#5-database-schema)
6. [Services Layer](#6-services-layer)
7. [Views Layer](#7-views-layer)
8. [Theme System](#8-theme-system)
9. [Security](#9-security)
10. [Installation & Running](#10-installation--running)
11. [Testing](#11-testing)
12. [Bug Fixes (v1.0.1)](#12-bug-fixes-v101)
13. [Extending the Application](#13-extending-the-application)

---

## 1. Project Overview

Budget Manager is a desktop personal finance application built with Python 3.12+ and PyQt6. It follows an MVC architecture, stores data in an embedded SQLite database, and provides Matplotlib charts alongside PDF/CSV/Excel export.

**Key capabilities:**

- Dashboard with live charts (pie + bar) and summary cards
- Full transaction CRUD with date/category/account filtering
- Monthly budget tracking with colour-coded progress bars
- Financial goals with progress tracking and deposit flow
- Account management with automatic running balance updates
- Recurring transaction engine (auto-posted at startup)
- Reports with PDF, CSV, and Excel export
- Dark and light QSS themes with live switching
- bcrypt authentication, multi-user support
- Automatic daily backup with 30-backup rolling retention
- CSV and Excel data import via Pandas
- 35+ pytest unit and integration tests

---

## 2. Technology Stack

| Component | Library / Version | Purpose |
|---|---|---|
| UI Framework | PyQt6 ≥ 6.4 | Cross-platform desktop GUI — widgets, signals/slots, QSS styling |
| Database | sqlite3 (stdlib) | Embedded relational storage; WAL mode; parameterised queries |
| Charts | Matplotlib ≥ 3.7 | Pie and bar charts embedded via the `QtAgg` backend |
| Data Processing | Pandas ≥ 2.0 | CSV/Excel import, tabular export, report aggregation |
| Password Hashing | bcrypt ≥ 4.0 | Secure one-way hashing for user passwords |
| PDF Reports | ReportLab ≥ 4.0 | Monthly PDF generation: summary, categories, budgets, transactions |
| Excel Export | openpyxl ≥ 3.1 | Write `.xlsx` files from Pandas DataFrames |
| Date Utilities | python-dateutil | Advance recurring transaction due-dates across all frequencies |
| Testing | pytest + pytest-cov | Unit/integration tests with coverage reporting |

---

## 3. Project Structure

```
budget_app/
├── main.py                         # Entry point; --seed / --reset / --theme flags
├── requirements.txt                # pip dependencies
├── README.md                       # User-facing guide
├── data/                           # SQLite database (auto-created at runtime)
├── backups/                        # Automatic and manual backup files
├── scripts/
│   └── seed_sample_data.py         # Demo data seeder (demo@budget.app / demo1234)
├── database/
│   ├── __init__.py
│   └── schema.py                   # DatabaseManager class, DDL, seed categories
├── services/
│   ├── __init__.py
│   ├── auth_service.py             # bcrypt register/login
│   ├── backup_service.py           # create / list / restore / prune (keep 30)
│   ├── import_export_service.py    # CSV + Excel import/export via Pandas
│   └── recurring_service.py        # Auto-post due recurring transactions
├── reports/
│   ├── __init__.py
│   └── pdf_report.py               # ReportLab monthly PDF report
├── views/
│   ├── __init__.py
│   ├── theme.py                    # DARK_QSS / LIGHT_QSS colour tokens
│   ├── widgets.py                  # Reusable: SummaryCard, GoalProgressCard, BudgetBar
│   ├── login_view.py               # Login / register stacked dialog
│   ├── main_window.py              # Sidebar nav + QStackedWidget controller
│   ├── dashboard_view.py           # Charts + summary cards + recent transactions
│   ├── transactions_view.py        # Full CRUD + search/filter toolbar
│   ├── budget_view.py              # Monthly budgets with BudgetBar progress bars
│   ├── goals_view.py               # Goal cards with progress tracking
│   ├── accounts_view.py            # Account CRUD + running balance display
│   ├── reports_view.py             # 3-tab reports + PDF/CSV/Excel export
│   ├── recurring_view.py           # Recurring transaction CRUD
│   └── settings_view.py            # Theme, categories, backup, import
└── tests/
    ├── __init__.py
    └── test_database.py            # 35+ pytest tests
```

---

## 4. Architecture

### 4.1 MVC Pattern

| Layer | Modules | Responsibility |
|---|---|---|
| **Model** | `database/`, `services/` | All data access, business rules, persistence. Views never touch SQL directly. |
| **View** | `views/` | All PyQt6 widgets. Reads data via service/DB calls; emits signals on mutations. |
| **Controller** | `main_window.py`, `main.py` | Wires views to services, routes navigation, handles cross-view refresh signals. |

### 4.2 Signal / Slot Wiring

Cross-view communication uses Qt's signal/slot mechanism. No view holds a reference to another view — they communicate through `MainWindow`:

```
TransactionsView.transaction_changed  ──►  DashboardView.refresh
                                      ──►  BudgetView.refresh
                                      ──►  ReportsView.refresh

AccountsView.accounts_changed         ──►  DashboardView.refresh
BudgetView.budget_changed             ──►  DashboardView.refresh
SettingsView.theme_changed            ──►  MainWindow._on_theme_changed
SettingsView.data_changed             ──►  MainWindow._refresh_all
```

### 4.3 Database Thread Safety

`DatabaseManager` uses `threading.local()` to store one SQLite connection per thread. The `_conn()` method creates the connection on first call for a given thread and caches it in `_local.conn`. This makes the manager safe to call from worker threads without explicit locking.

The `_execute()` method captures a single connection reference before the `execute()` and `commit()` calls, ensuring both operations target the same connection object:

```python
def _execute(self, sql: str, params: tuple = ()) -> int:
    conn = self._conn()          # single reference — avoids double-call race
    cur  = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid
```

### 4.4 Error Handling in Dialog `_save` Methods

All dialog `_save()` methods wrap database calls in `try/except`. If the database raises (constraint violation, file lock, schema mismatch, etc.), a `QMessageBox.critical` is shown to the user and the dialog stays open. Without this, PyQt6 would absorb the exception in the slot system and the dialog would appear unresponsive with no feedback.

```python
def _save(self) -> None:
    # ... validation ...
    try:
        self._db.create_account(self._user_id, name, acct_type, balance)
    except Exception as exc:
        QMessageBox.critical(self, "Database Error",
                             "Could not save account:\n" + str(exc))
        return
    self.accept()
```

### 4.5 Startup Sequence

```
parse_args()
    └─ --seed?  →  seed_sample_data.main()
    └─ --reset? →  delete data/budget.db

QApplication.setHighDpiScaleFactorRoundingPolicy()   ← MUST precede QApplication()
QApplication()

DatabaseManager(DB_PATH)          ← WAL mode, FK ON, DDL applied
AuthService(db)
BackupService(DB_PATH, BACKUP_DIR)

LoginView.exec()                  ← blocks until authenticated or cancelled

MainWindow(db, user, backup)
    ├─ _nav_buttons / _views dicts initialised   ← BEFORE _build_sidebar()
    ├─ 8 views instantiated and added to QStackedWidget
    ├─ signals wired
    ├─ RecurringService.process_due()            ← post overdue recurring
    └─ QTimer(24h) → BackupService.create_backup("auto")

app.exec()
```

---

## 5. Database Schema

Database file: `data/budget.db` (relative to `budget_app/`). Settings: WAL journal mode, foreign keys ON. All queries use parameterised placeholders (`?`).

### Tables

#### `users`
```sql
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,            -- bcrypt hash
    currency    TEXT    NOT NULL DEFAULT 'CAD',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

#### `accounts`
```sql
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name    TEXT    NOT NULL,
    account_type    TEXT    NOT NULL
                    CHECK(account_type IN ('Checking','Savings','Credit Card','Cash')),
    current_balance REAL    NOT NULL DEFAULT 0.0
);
```

#### `categories`
```sql
CREATE TABLE IF NOT EXISTS categories (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    type    TEXT NOT NULL CHECK(type IN ('Income','Expense')),
    color   TEXT NOT NULL DEFAULT '#607D8B'
);
```
> Note: categories are global (no `user_id`). Default categories are seeded once when the table is empty.

#### `transactions`
```sql
CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    category_id  INTEGER REFERENCES categories(id),
    date         TEXT    NOT NULL,
    description  TEXT    NOT NULL,
    amount       REAL    NOT NULL,   -- positive = income, negative = expense
    notes        TEXT    DEFAULT '',
    recurring_id INTEGER REFERENCES recurring_transactions(id)
);
```

#### `budgets`
```sql
CREATE TABLE IF NOT EXISTS budgets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    month         INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    year          INTEGER NOT NULL,
    budget_amount REAL    NOT NULL DEFAULT 0.0,
    UNIQUE(category_id, month, year)
);
```
Set via `INSERT OR REPLACE` (UPSERT) — re-setting a budget for the same month/category overwrites the amount.

#### `financial_goals`
```sql
CREATE TABLE IF NOT EXISTS financial_goals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_name      TEXT    NOT NULL,
    target_amount  REAL    NOT NULL,
    current_amount REAL    NOT NULL DEFAULT 0.0,
    target_date    TEXT    NOT NULL
);
```

#### `recurring_transactions`
```sql
CREATE TABLE IF NOT EXISTS recurring_transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    amount        REAL    NOT NULL,
    frequency     TEXT    NOT NULL
                  CHECK(frequency IN ('Weekly','Bi-weekly','Monthly','Quarterly','Yearly')),
    next_due_date TEXT    NOT NULL,
    category_id   INTEGER REFERENCES categories(id),
    account_id    INTEGER REFERENCES accounts(id)
);
```

### Balance Auto-Update Logic

`DatabaseManager` keeps `accounts.current_balance` accurate on every transaction mutation:

| Operation | Balance Effect |
|---|---|
| `create_transaction(account_id, ..., amount)` | `balance += amount` |
| `update_transaction(txn_id, ..., amount)` | `balance -= old_amount`, then `balance += new_amount` |
| `delete_transaction(txn_id)` | `balance -= amount` (reversal) |

### Default Categories (seeded once on first run)

**Income:** Salary, Freelance, Investment, Other Income

**Expense:** Rent/Mortgage, Groceries, Gas, Utilities, Insurance, Entertainment, Dining Out, Healthcare, Clothing, Education, Travel, Subscriptions, Personal Care, Gifts, Miscellaneous

---

## 6. Services Layer

### 6.1 `AuthService` — `services/auth_service.py`

| Method | Signature | Returns |
|---|---|---|
| `register` | `(name, email, password, currency='CAD')` | `tuple[bool, str]` — success flag + message |
| `login` | `(email, password)` | `tuple[bool, Optional[dict], str]` — success, user dict, message |
| `hash_password` | `(plain: str)` | `str` — bcrypt hash (12 rounds) |
| `verify_password` | `(plain, hashed)` | `bool` — timing-safe bcrypt compare |

Registration validates: non-empty name, valid email format (`@` + `.`), password ≥ 6 chars, unique email. After registration the user must log in to get a session.

### 6.2 `BackupService` — `services/backup_service.py`

| Method | Description |
|---|---|
| `create_backup(label='manual')` | Copies `budget.db` → `backups/budget_YYYYMMDD_HHMMSS_{label}.db`; prunes oldest files if count > 30 |
| `list_backups()` | Returns list of backup paths sorted newest-first |
| `restore_backup(path)` | Copies selected backup over live DB; existing connections re-open automatically |

### 6.3 `RecurringService` — `services/recurring_service.py`

`process_due(user_id)` iterates all active recurring transactions. Any transaction whose `next_due_date ≤ today` is posted as a real transaction, and the due date is advanced using `python-dateutil`. Multiple missed periods are caught by a `while` loop:

```python
while date.fromisoformat(rec["next_due_date"]) <= today:
    create_transaction(...)
    next_due = _next_date(due, frequency)
    update_recurring(..., str(next_due))
```

Frequency → date delta mapping:

| Frequency | Delta |
|---|---|
| Weekly | +7 days |
| Bi-weekly | +14 days |
| Monthly | `relativedelta(months=1)` |
| Quarterly | `relativedelta(months=3)` |
| Yearly | `relativedelta(years=1)` |

### 6.4 `ImportExportService` — `services/import_export_service.py`

| Method | Description |
|---|---|
| `import_csv(user_id, path)` | Reads CSV via Pandas; maps columns `date/amount/description/category/account`; skips invalid rows; returns `(imported_count, errors)` |
| `import_excel(user_id, path)` | Same as CSV import but reads first sheet with `pd.read_excel` |
| `export_csv(user_id, path)` | Fetches all transactions; writes CSV via `DataFrame.to_csv` |
| `export_excel(user_id, path)` | Writes multi-sheet Excel: Transactions, Budgets, Accounts |

---

## 7. Views Layer

All views inherit from `QWidget` and receive `db: DatabaseManager` and `user: dict` at construction. Views never hold SQL connections directly and never import from other view modules (avoids circular dependencies).

### 7.1 View Inventory

| File | Class | Responsibility |
|---|---|---|
| `login_view.py` | `LoginView` | Modal `QDialog` with stacked login/register panels. Emits `login_success(dict)` on success. |
| `main_window.py` | `MainWindow` | `QMainWindow` hosting a 210 px fixed sidebar and `QStackedWidget` (8 views). Owns all cross-view signal wiring and the 24-hour auto-backup timer. |
| `dashboard_view.py` | `DashboardView` | 5 `SummaryCard` widgets, embedded Matplotlib pie + bar charts, recent 10 transactions table. |
| `transactions_view.py` | `TransactionsView` | `QTableWidget` with Add/Edit/Delete. Filter toolbar: date range, category, account, search text. Emits `transaction_changed` on every mutation. |
| `budget_view.py` | `BudgetView` | Month picker + per-category `BudgetBar` widgets. Quick-set budget dialog with UPSERT. Emits `budget_changed`. |
| `goals_view.py` | `GoalsView` | Card grid of `GoalProgressCard` per goal. Add/Edit/Delete + Deposit dialogs. |
| `accounts_view.py` | `AccountsView` | `QTableWidget` of accounts. Add/Edit/Delete. Emits `accounts_changed` on mutation. |
| `reports_view.py` | `ReportsView` | `QTabWidget`: Summary, Categories, Cash Flow tabs. Export buttons for PDF/CSV/Excel. |
| `recurring_view.py` | `RecurringView` | `QTableWidget` of recurring rules. Overdue rows highlighted red. |
| `settings_view.py` | `SettingsView` | Theme toggle, category CRUD, manual backup/restore, CSV/Excel import. Emits `theme_changed(str)` and `data_changed()`. |

### 7.2 Reusable Widgets — `views/widgets.py`

| Widget | Description |
|---|---|
| `SummaryCard` | Rounded card: icon + label + formatted value. Used on Dashboard. |
| `GoalProgressCard` | Card showing goal name, current/target amounts, percentage, colour-coded `QProgressBar`. |
| `BudgetBar` | `QProgressBar` subclass — green `< 70%`, yellow `< 90%`, red `≥ 90%` of monthly budget. |

---

## 8. Theme System

Themes are defined as two QSS strings in `views/theme.py`: `DARK_QSS` and `LIGHT_QSS`. Runtime switching calls `MainWindow._apply_theme(theme)`, which sets the stylesheet on the root widget and clears all child widget stylesheets to force re-painting from the parent.

### QSS Object Name Targets

| `objectName` | Used By |
|---|---|
| `sidebar` | Left navigation `QFrame` |
| `navBtn` | Sidebar `QPushButton` — `:checked` state indicates active page |
| `card` | `SummaryCard` container frames |
| `muted` | Secondary / hint `QLabel` |
| `heading` | Page title `QLabel` |
| `danger` | Delete `QPushButton` (red tint) |
| `secondary` | Cancel / secondary action `QPushButton` |

---

## 9. Security

### Password Storage
Passwords are hashed with `bcrypt` (cost factor 12). Login uses `bcrypt.checkpw()` — constant-time comparison. Plaintext passwords are never stored or logged.

### SQL Injection Prevention
Every SQL statement uses parameterised placeholders (`?`). No user-supplied string is ever interpolated into a query.

### Data Isolation
All queries include a `user_id` WHERE clause or join through `accounts.user_id`. A user can only read or modify their own accounts, transactions, budgets, goals, categories, and recurring rules.

### Backup File Safety
Backup files are written locally to `backups/`. `restore_backup` copies the file into place before deleting the old DB, so a copy failure leaves the live database intact.

---

## 10. Installation & Running

### Prerequisites
- Python 3.12 or later
- pip / pip3
- Display environment (PyQt6 requires a screen; set `DISPLAY` on headless Linux)

### Install

```bash
unzip budget_manager.zip
cd budget_app
pip install -r requirements.txt
```

### Run

| Command | Effect |
|---|---|
| `python main.py` | Normal launch |
| `python main.py --seed` | Seed demo data then launch (`demo@budget.app` / `demo1234`) |
| `python main.py --reset` | Delete DB and start fresh |
| `python main.py --theme light` | Launch with light theme |

> **Note:** Run `--reset` before `--seed` if a database already exists with a conflicting `demo@budget.app` account.

### Keyboard Shortcuts

| Shortcut | View |
|---|---|
| `Ctrl+1` | Dashboard |
| `Ctrl+2` | Transactions |
| `Ctrl+3` | Budgets |
| `Ctrl+4` | Goals |
| `Ctrl+5` | Accounts |
| `Ctrl+6` | Reports |
| `Ctrl+7` | Recurring |
| `Ctrl+8` | Settings |

---

## 11. Testing

Tests live in `tests/test_database.py` and use an in-memory SQLite database (`:memory:`) — no files created or cleaned up between runs.

```bash
pytest tests/ -v
pytest tests/ --cov=. --cov-report=term-missing
```

### Test Classes

| Class | Scenarios |
|---|---|
| `TestAuthService` | Registration success, duplicate email rejection, login success, wrong password |
| `TestAccounts` | Create, list, update, delete account |
| `TestTransactions` | Add income/expense, balance adjustment verification, update with correction, delete with reversal, filtering |
| `TestBudgets` | Set budget, list monthly budgets, UPSERT behaviour, budget vs spending |
| `TestGoals` | Create, list, update progress, complete, delete |
| `TestRecurring` | Create rule, process_due posts + advances date, inactive rules skipped, multiple missed periods |
| `TestReporting` | Monthly summary totals, category breakdown, cash-flow structure |
| `TestBackupService` | Create file, list sorted, restore, prune when > 30 |

---

## 12. Bug Fixes (v1.0.1)

### Fix 1 — `setHighDpiScaleFactorRoundingPolicy` warning (`main.py`)

**Symptom:** Console warning on startup: *"setHighDpiScaleFactorRoundingPolicy must be called before creating the QGuiApplication instance"*

**Root cause:** The call was made as an *instance method* (`app.setHighDpiScaleFactorRoundingPolicy(...)`) **after** `QApplication()` was constructed. Qt requires this to be set as a *class method* before instantiation.

**Fix:**
```python
# BEFORE (wrong)
app = QApplication(sys.argv)
app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

# AFTER (correct)
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
app = QApplication(sys.argv)
```

---

### Fix 2 — `AttributeError: '_nav_buttons'` crash on startup (`views/main_window.py`)

**Symptom:** `AttributeError: 'MainWindow' object has no attribute '_nav_buttons'` at launch.

**Root cause:** `_build_ui()` called `_build_sidebar()` first. Inside `_build_sidebar()`, the loop `self._nav_buttons[idx] = btn` ran before `self._nav_buttons` was ever initialised as a dict.

**Fix:** Move both dict initialisations before the `_build_sidebar()` call:
```python
# Initialise BEFORE building sidebar (sidebar populates these dicts)
self._views: dict[int, QWidget] = {}
self._nav_buttons: dict[int, QPushButton] = {}

root_layout.addWidget(self._build_sidebar())   # now safe to populate
```

---

### Fix 3 — Account creation silently fails (`views/accounts_view.py`, all dialogs)

**Symptom:** Clicking "Save" in the Add Account dialog appeared to do nothing. No account appeared in the list, and no error was shown.

**Root cause (primary):** Dialog `_save()` methods had no `try/except` around database calls. In PyQt6, an unhandled exception inside a slot is printed to stderr but the slot returns normally — so `self.accept()` was never reached (the dialog stayed open), giving the impression that nothing happened.

**Root cause (secondary):** `DatabaseManager._execute()` called `self._conn()` twice — once for `execute()` and once for `commit()`. While the connection cache made this safe in practice, it introduced an unnecessary re-lookup. Fixed to capture a single `conn` reference.

**Fix (accounts_view.py — same pattern applied to all dialogs):**
```python
def _save(self) -> None:
    name = self._name_edit.text().strip()
    if not name:
        QMessageBox.warning(self, "Validation", "Account name required.")
        return
    try:
        if self._account:
            self._db.update_account(self._account["id"], name, acct_type, balance)
        else:
            self._db.create_account(self._user_id, name, acct_type, balance)
    except Exception as exc:
        QMessageBox.critical(self, "Database Error",
                             "Could not save account:\n" + str(exc))
        return
    self.accept()
```

---

## 13. Extending the Application

### Adding a New View

1. Create `views/my_view.py` with a class inheriting `QWidget`; accept `db` and `user` in `__init__`.
2. Add a `refresh()` method that re-queries and re-populates widgets.
3. In `main_window.py`: add an entry to `NAV_ITEMS`, import the class, instantiate it in `_build_ui()`, and add it to `self._stack`.
4. Add a `Ctrl+N` shortcut in `_setup_shortcuts()`.

### Adding a New Service

1. Create `services/my_service.py`; accept `db: DatabaseManager` in `__init__`.
2. All queries should filter by `user_id` for data isolation.
3. Instantiate in the relevant view or in `MainWindow` and pass it down.

### Adding a New Database Table

1. Add `CREATE TABLE IF NOT EXISTS` DDL to `DatabaseManager.__init__()` in `database/schema.py`.
2. Add corresponding CRUD methods to `DatabaseManager` or a new service.
3. Add tests to `tests/test_database.py` using the existing in-memory fixture pattern.

### Adding a New Export Format

1. Add a method to `ImportExportService` (e.g. `export_ods()`).
2. Add an export button to `reports_view.py` and connect its `clicked` signal.
