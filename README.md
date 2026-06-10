# 💰 Budget Manager

[![CI](https://github.com/LoloAbdo/budget_app/actions/workflows/ci.yml/badge.svg)](https://github.com/LoloAbdo/budget_app/actions/workflows/ci.yml)

A full-featured personal finance desktop application built with Python 3.12+, PyQt6, SQLite, and Matplotlib.

---

## Features

| Feature | Details |
|---------|---------|
| **Dashboard** | Summary cards, spending pie chart, income vs expense bar chart, recent transactions |
| **Transactions** | Add / edit / delete, full-text search, date range & category filters |
| **Budgets** | Monthly category budgets with visual progress bars (green/yellow/red) |
| **Financial Goals** | Progress cards with percentage completion and target date |
| **Accounts** | Checking, Savings, Credit Card, Cash — running balance auto-updated |
| **Reports** | Monthly summary, category analysis, cash-flow trend; PDF / CSV / Excel export |
| **Recurring** | Weekly / bi-weekly / monthly / quarterly / yearly auto-posting (transactions **and** transfers) |
| **Savings** | Groups all Savings accounts; auto-detects interest/gains when you update a balance; tracks interest per month / year / all-time with a chart and history |
| **Markets** | Watchlist of stocks & crypto in your currency, auto-refreshed every 5–15 min on a background thread (keyless: CoinGecko + Stooq/Yahoo) |
| **Settings** | Dark / light theme, **English / French language**, category management, backup & restore, CSV/Excel import |
| **Security** | bcrypt password hashing, parameterised SQL queries, local-only SQLite |

---

## Prerequisites

- Python 3.12 or later
- `pip` package manager

---

## Installation

```bash
# 1. Clone or unzip the project
cd budget_app

# 2. (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# Note: python-dateutil is a transitive dependency pulled in automatically.
# If you see an ImportError for dateutil, run:
#   pip install python-dateutil
```

---

## Running the Application

```bash
# Normal launch (shows login screen)
python main.py

# Launch with dark or light theme
python main.py --theme dark
python main.py --theme light

# Seed sample demo data, then launch
python main.py --seed

# Completely reset the database, then launch
python main.py --reset
```

### Demo Credentials (after --seed)
- **Email:** `demo@budget.app`
- **Password:** `demo1234`

---

## Running Tests

```bash
# Run all tests (configuration lives in pytest.ini)
pytest

# Verbose
pytest -v
```

### Test suite layout

| File | Covers |
|------|--------|
| `tests/conftest.py` | Shared fixtures (`db`, `user_id`, `account_id`, `savings_id`) |
| `tests/test_database.py` | Auth, accounts, transactions, budgets, goals, recurring, reporting, backup |
| `tests/test_market_service.py` | Quote parsers, FX, crypto/stock fetch, request batching (fully offline — network mocked) |
| `tests/test_savings_interest.py` | Interest category, `record_interest`, per-account interest summary, history |
| `tests/test_watchlist.py` | Watchlist CRUD + per-user language column |
| `tests/test_recurring_transfers.py` | Recurring transfers post both legs and stay transfers |
| `tests/test_i18n.py` | Translation fallback, language switching, month abbreviations |

> **Coverage note:** `pytest --cov` can fail in some environments with a
> `PyO3 modules … may only be initialized once` error — that's `coverage`
> re-importing bcrypt's native module, not a test failure. Plain `pytest`
> runs cleanly.

---

## Building a Standalone Windows App (.exe)

Package the app into a single executable that runs **without a Python install**,
using [PyInstaller](https://pyinstaller.org):

```powershell
# One-file build  ->  dist\BudgetManager.exe   (easiest to share)
.\build.ps1

# One-folder build ->  dist\BudgetManager\      (faster startup)
.\build.ps1 -OneDir
```

Or directly:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name BudgetManager --collect-all matplotlib main.py
```

**Where the data lives:** when running as an `.exe`, the database and backups are
stored in **`%APPDATA%\BudgetManager`**, *not* next to the executable. This keeps
your data safe across rebuilds and updates (a one-file build unpacks to a temp
folder that Windows deletes on exit). Running from source still uses the
project's local `data/` folder, so development data is unaffected.

### Building a Windows installer

For a proper installed app (Start Menu shortcut, uninstaller, no admin prompt),
build an installer with [Inno Setup](https://jrsoftware.org/isinfo.php):

```powershell
.\build_installer.ps1   # -> installer_output\BudgetManagerSetup.exe
```

It installs Inno Setup / PyInstaller if missing, builds the one-folder app, and
compiles [`installer.iss`](installer.iss) with the version from `version.py`.

> Build output (`build/`, `dist/`, `*.spec`, `installer_output/`) is gitignored —
> don't commit the ~60–90 MB binaries; attach them to a GitHub Release instead.

---

## Releasing an Update

Shipping a new version is **one command** — a GitHub Actions workflow builds the
`.exe` on a Windows runner and publishes a GitHub Release automatically.

```powershell
# 1. Bump the version in version.py   (e.g. "1.0.0" -> "1.0.1")
# 2. Commit that change
# 3. Tag and push:
git tag v1.0.1
git push origin v1.0.1
```

The [`release` workflow](.github/workflows/release.yml) then:
1. **Checks the tag matches `version.py`** (fails fast if you forgot to bump it).
2. Builds the app with PyInstaller and compiles the Inno Setup installer.
3. Creates a GitHub Release `v1.0.1` with **both** downloads attached and
   auto-generated notes:
   - `BudgetManagerSetup.exe` — the installer (Start Menu shortcut + uninstaller)
   - `BudgetManager.exe` — a portable single-file build (no install)

Users running an older build get an **"Update available"** prompt (Settings ▸
About, or at launch) and can download the new version from the Release. Their
data in `%APPDATA%\BudgetManager` is never touched.

> The tag **must** match `__version__` in `version.py` — that's what the in-app
> update check compares against. The workflow enforces this so a mislabeled
> build can't be released.

---

## Project Structure

```
budget_app/
├── main.py                       ← Application entry point
├── requirements.txt
├── data/                         ← SQLite database (auto-created)
├── backups/                      ← Automatic & manual backups
├── exports/                      ← PDF / CSV / Excel exports
├── scripts/
│   └── seed_sample_data.py       ← Demo data seeder
├── database/
│   ├── __init__.py
│   └── schema.py                 ← DatabaseManager + DDL
├── services/
│   ├── auth_service.py           ← Registration / login / bcrypt
│   ├── backup_service.py         ← Backup / restore
│   ├── import_export_service.py  ← CSV / Excel import & export
│   └── recurring_service.py      ← Auto-post due recurring transactions
├── reports/
│   └── pdf_report.py             ← ReportLab PDF generator
├── views/
│   ├── theme.py                  ← QSS stylesheets (dark / light)
│   ├── widgets.py                ← Reusable SummaryCard, GoalProgressCard, BudgetBar
│   ├── login_view.py             ← Login / register dialog
│   ├── main_window.py            ← Sidebar + content stack
│   ├── dashboard_view.py         ← Charts + recent transactions
│   ├── transactions_view.py      ← CRUD + filter
│   ├── budget_view.py            ← Monthly budgets
│   ├── goals_view.py             ← Financial goals
│   ├── accounts_view.py          ← Account management
│   ├── reports_view.py           ← Reporting + export
│   ├── recurring_view.py         ← Recurring transaction management
│   └── settings_view.py          ← Theme, categories, backup, import
└── tests/
    └── test_database.py          ← pytest unit tests
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Dashboard |
| `Ctrl+2` | Transactions |
| `Ctrl+3` | Budgets |
| `Ctrl+4` | Goals |
| `Ctrl+5` | Accounts |
| `Ctrl+6` | Reports |
| `Ctrl+7` | Recurring |
| `Ctrl+8` | Savings |
| `Ctrl+9` | Markets |
| `Ctrl+0` | Settings |

---

## Language (English / French)

The interface ships in **English** and **French**. Choose your language in
**Settings → Appearance → Language** and click **Apply Language** — the whole
window re-localises instantly, no restart needed. Your choice is saved per user
and restored on the next login.

Only the interface is translated. Your own data (custom category names,
descriptions, notes) is never altered, and fixed values such as account types
and frequencies are always stored in English internally, so the data is
identical regardless of the language you view it in.

Translations live in [`views/i18n.py`](views/i18n.py) — adding another language
is just one more table of `{english_key: translation}` plus an entry in
`LANGUAGES`.

---

## Savings & Interest

The **Savings** section groups every account of type *Savings* and tracks the
interest (or investment gains/losses) they earn over time.

Interest is detected automatically — there's no separate data entry:

1. Your recorded transfers/transactions keep each account's *expected* balance.
2. When you edit a Savings account and type in the **real** balance from your
   bank, the app records the unexplained difference as a signed **Interest**
   entry (gain = +, loss = −) and reconciles the balance.

> Example: a savings account starts at **$1,000**, four **$100** transfers come
> in (expected = $1,400), but your bank shows **$1,500** → the app records
> **$100 of interest**. Transfers are never counted as interest, so only the
> true growth is captured.

When editing a Savings balance you can untick *"Record balance change as
interest/gain"* to treat the edit as a plain correction instead. Interest
entries are normal ledger transactions under the **Interest** category, so they
also count toward your income on the dashboard.

---

## Markets (stocks & crypto watchlist)

The **Markets** tab tracks live prices for stocks and crypto you choose,
converted to your account currency.

- **Add a symbol** → pick *Stock* or *Crypto* and enter a ticker (e.g. `AAPL`,
  `BTC`). For non-US stocks add an exchange suffix, e.g. `SHOP.TO`.
- **Auto-refresh** every 5 / 10 / 15 minutes (selectable; default 10), plus a
  manual **Refresh** button and a "last updated" stamp.
- **Keyless data sources** — no API key or signup required:
  - Crypto → [CoinGecko](https://www.coingecko.com)
  - Stocks → [Stooq](https://stooq.com) (Yahoo Finance fallback)
  - USD→your-currency conversion via a live FX rate
- **Network-safe** — all fetching happens on a background thread (the UI never
  freezes); the last prices are cached so they appear instantly on launch, and
  if a refresh fails the cached values stay put with a notice.

> This is the only feature that reaches the internet. It sends just the ticker
> symbols you add to the public price endpoints above; no account data leaves
> your machine.

---

## Backup Strategy

- **Automatic:** Once per 24 hours while the app is running (saved to `backups/`)
- **Manual:** Settings → Backup & Restore → Create Backup Now
- **Restore:** Double-click any backup in the list

Up to 30 recent backups are kept; older ones are pruned automatically.

---

## Data Import Format

CSV or Excel files with these columns:

| Column | Required | Example |
|--------|----------|---------|
| `date` | ✅ | `2024-03-15` |
| `description` | ✅ | `Grocery run` |
| `amount` | ✅ | `-85.50` |
| `category` | optional | `Groceries` |
| `account` | optional | `Main Checking` |
| `notes` | optional | `Weekly shop` |

Negative amounts = expenses, positive = income.

---

## Architecture

The application follows **MVC**:

- **Model** — `database/schema.py` (`DatabaseManager`) plus service classes
- **View** — `views/` PyQt6 panels
- **Controller** — `views/main_window.py` wires signals/slots between panels

All database access uses parameterised queries (no string interpolation) to prevent SQL injection. Passwords are hashed with **bcrypt** (cost factor 12). The database lives in `data/budget.db` — never in a network-accessible path.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| PyQt6 | Desktop GUI |
| matplotlib | Charts (embedded via QtAgg backend) |
| pandas | DataFrame operations for import/export |
| bcrypt | Password hashing |
| reportlab | PDF report generation |
| openpyxl | Excel read/write |
| pytest / pytest-cov | Testing |

---

## License

MIT — free for personal and commercial use.
