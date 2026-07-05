# Budget Manager — Technical Documentation

> **Version:** 1.2.0 · **Python:** 3.12+ · **Stack:** PyQt6 · SQLite · Matplotlib · **Last updated:** June 2026
>
> 🇬🇧 **English** below · 🇫🇷 **Version française** [plus bas](#-documentation-technique-français)

---

# 🇬🇧 Technical Documentation (English)

## Table of Contents

1. [Overview](#1-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Architecture](#4-architecture)
5. [Database Schema & Migrations](#5-database-schema--migrations)
6. [Services Layer](#6-services-layer)
7. [Views Layer](#7-views-layer)
8. [Internationalization (i18n)](#8-internationalization-i18n)
9. [Theme System](#9-theme-system)
10. [Security](#10-security)
11. [Data Locations](#11-data-locations)
12. [Build & Release Pipeline](#12-build--release-pipeline)
13. [Testing](#13-testing)
14. [Extending the Application](#14-extending-the-application)

---

## 1. Overview

Budget Manager is a desktop personal-finance application for Windows (and runnable from source on any desktop OS). It uses a layered architecture: PyQt6 views on top, a service layer for business logic, and a single `DatabaseManager` that owns all SQL against an embedded SQLite database. Charts are rendered with Matplotlib; reports export to PDF/CSV/Excel.

**Capabilities:** dashboard with spending, income-vs-expense, and 12-month net-worth charts; transaction CRUD with transfers, search, and filtering; monthly budgets; financial goals; multi-account management with auto-updated balances; a recurring-transaction/transfer engine; reports with export; savings/interest tracking; a keyless stocks-and-crypto markets watchlist; English/French localization; bcrypt auth; rolling automatic backups; and a GitHub update check with one-click auto-update on the installed build.

---

## 2. Technology Stack

| Component | Library | Purpose |
|---|---|---|
| UI framework | PyQt6 ≥ 6.6 | Desktop GUI — widgets, signals/slots, QSS styling |
| Database | sqlite3 (stdlib) | Embedded storage; parameterized queries; per-thread connections |
| Charts | Matplotlib ≥ 3.8 | Pie, bar, and line charts via the `QtAgg` backend |
| Data processing | pandas ≥ 2.1 | CSV/Excel import & export |
| Password hashing | bcrypt ≥ 4.1 | One-way password hashing |
| PDF reports | reportlab ≥ 4.0 | Monthly PDF generation |
| Excel export | openpyxl ≥ 3.1 | `.xlsx` workbooks |
| Date math | python-dateutil | Advancing recurring due-dates (transitive dependency) |
| Testing | pytest (+ pytest-qt, pytest-cov) | Unit/integration tests |
| Packaging | PyInstaller + Inno Setup | Portable `.exe` and Windows installer |

---

## 3. Project Structure

```
budget_app/
├── main.py                         # Entry point; --seed / --reset / --theme flags; data-path logic
├── version.py                      # __version__ + GitHub coordinates (single source of truth)
├── requirements.txt
├── README.md · USER_GUIDE.md · TECHNICAL.md · CHANGELOG.md
├── build.ps1 · build_installer.ps1 · installer.iss · BudgetManager.spec
├── .github/workflows/
│   ├── ci.yml                      # pytest on push/PR
│   └── release.yml                 # tag-triggered build + publish (installer + portable exe)
├── scripts/
│   └── seed_sample_data.py         # Idempotent demo-data seeder (demo@budget.app / demo1234)
├── database/
│   └── schema.py                   # DatabaseManager: DDL, migrations, all CRUD/analytics SQL
├── services/
│   ├── auth_service.py             # bcrypt register/login
│   ├── backup_service.py           # create / list / restore / prune (keep 30)
│   ├── import_export_service.py    # CSV + Excel import/export (pandas)
│   ├── recurring_service.py        # Auto-post due recurring transactions & transfers
│   ├── market_service.py           # Keyless stock/crypto quotes + FX conversion
│   └── update_service.py           # GitHub "latest release" version check
├── reports/
│   └── pdf_report.py               # ReportLab monthly PDF
├── views/
│   ├── theme.py                    # DARK_QSS / LIGHT_QSS + chart_colors()
│   ├── i18n.py                     # tr(), set_language(), EN→FR table, month abbreviations
│   ├── widgets.py                  # SummaryCard, GoalProgressCard, BudgetBar
│   ├── login_view.py · main_window.py
│   ├── dashboard_view.py · transactions_view.py · budget_view.py · goals_view.py
│   ├── accounts_view.py · reports_view.py · recurring_view.py
│   ├── savings_view.py · markets_view.py · settings_view.py
│   └── update_check.py             # Update-check UI glue
└── tests/                          # pytest; conftest.py fixtures (db, user_id, account_id, savings_id)
```

---

## 4. Architecture

### 4.1 Layers

| Layer | Modules | Responsibility |
|---|---|---|
| **Data** | `database/schema.py` | All SQL, parameterized. Views never touch SQL directly. |
| **Services** | `services/` | Business logic with no Qt dependency (auth, backup, import/export, recurring, markets, update). |
| **Views** | `views/` | All PyQt6 widgets. Read via DB/service calls; emit signals on mutation. |
| **Controller** | `main.py`, `main_window.py` | Startup wiring, navigation, cross-view refresh. |

### 4.2 Signal/Slot wiring
Views never reference each other; they communicate through `MainWindow`. Mutations in one view (e.g. `TransactionsView.transaction_changed`) trigger `refresh()` on dependent views (Dashboard, Budgets, Reports, Savings). `SettingsView` emits `theme_changed` and `language_changed`, which `MainWindow` applies app-wide.

### 4.3 Database thread safety
`DatabaseManager` stores **one SQLite connection per thread** via `threading.local()`. `_local` is a per-**instance** attribute (not a class attribute) — this is required so the test suite's many `DatabaseManager` instances don't share a connection. The market service performs network I/O on worker threads, which is why per-thread connections matter.

### 4.4 Dialog error handling
Every dialog `_save()` wraps DB calls in `try/except` and shows a `QMessageBox.critical` on failure (otherwise PyQt6 would swallow the exception in the slot and the dialog would appear frozen with no feedback).

### 4.5 Startup sequence
```
parse_args()  →  --reset deletes DB · --seed runs seed_sample_data.main()
QApplication.setHighDpiScaleFactorRoundingPolicy(...)   # MUST precede QApplication()
QApplication()  →  apply DARK_QSS
DatabaseManager(DB_PATH) · AuthService · BackupService
LoginView.exec()        # blocks until authenticated
set_language(user["language"])
MainWindow(db, user, backup, theme)   # builds 10 views, wires signals, auto-backup timer
app.exec()
```

---

## 5. Database Schema & Migrations

Parameterized queries throughout; foreign keys ON. Tables: `users`, `accounts`, `categories`, `transactions`, `budgets`, `financial_goals`, `recurring_transactions`, `watchlist`, `fx_rates`, `recovery_codes`, `category_rules`.

**Key columns & relationships:**
- `users` — bcrypt `password`, `currency` (the **home currency**, default CAD), `language` (`'en'`/`'fr'`).
- `accounts` — `account_type` ∈ {Checking, Savings, Credit Card, Cash}, `current_balance` (kept current on every transaction mutation), `currency` (the account's own currency; transaction amounts live in it).
- `fx_rates` — cached exchange rates (`base`, `quote`, `rate`, `updated`; PK `(base, quote)`). `set_fx_rate()` stores **both directions**. Aggregate queries convert per-account amounts into the home currency via the `DatabaseManager._FX` SQL fragment — `COALESCE((SELECT rate …), 1.0)` — so a missing rate degrades to 1:1 instead of failing. No rate history is kept: historical conversions use the current rate (documented approximation).
- `categories` — **global** (no `user_id`); `type` ∈ {Income, Expense}. Includes a system **Interest** category used for savings/interest tracking.
- `transactions` — signed `amount` (income +, expense −) in the **account's currency**; `transfer_id` self-reference links the two legs of a transfer (excluded from income/expense aggregates). Cross-currency transfers store a different amount per leg (`create_transfer(..., to_amount=)`).
- `budgets` — `UNIQUE(user_id, category_id, month, year)`; set via UPSERT.
- `recurring_transactions` — `frequency` ∈ {Weekly, Bi-weekly, Monthly, Quarterly, Yearly}; optional `to_account_id` for recurring transfers; optional `end_date` (NULL = no end) after which the rule stops posting; `is_active` (1/0) to pause a rule without deleting it.
- `watchlist` — markets symbols with cached last price/change/currency; `UNIQUE(user_id, symbol, asset_type)`.
- `recovery_codes` — one-time password-reset codes: `code_hash` (bcrypt of the normalized code — plaintext is never stored), `used_at` (NULL = still usable; kept after use so "codes remaining" and the reset history stay honest). Regenerating deletes the user's previous set.
- `category_rules` — auto-categorization: `pattern` matched case-insensitively as a substring of a transaction's description → `category_id`. `match_category_rule()` picks the longest matching pattern (ties → oldest rule). Applied by the transaction dialog while typing (never overriding a manual pick) and by CSV/Excel import for rows without a category. `search_transactions()` (global Ctrl+F) also lives in `DatabaseManager`: numeric query → sign-insensitive amount match, otherwise description/notes LIKE, capped and newest-first.

**Balance auto-update:** `create_transaction` → `balance += amount`; `update_transaction` → reverse old, apply new; `delete_transaction` → `balance −= amount`.

**Migrations** run on every init via `DatabaseManager._migrate()`, each guarded so it's idempotent on existing databases:

| Label | Change |
|---|---|
| v1.0.1 | Recreate `budgets` with `user_id` + corrected UNIQUE constraint |
| v1.0.2 | Add `transactions.transfer_id` |
| v1.0.3 | Add `recurring_transactions.to_account_id` |
| v1.0.4 | Add `users.language` |
| v1.0.5 | Add performance indexes (see below) |
| v1.0.6 | Add `users.theme` |
| v1.0.7 | Add `recurring_transactions.end_date` (nullable; NULL = no end) |
| v1.0.8 | Add `recurring_transactions.is_active` (1 = active, 0 = paused) |
| v1.0.9 | Add `accounts.currency`, **backfilled from the owner's `users.currency`** (upgrades are lossless — same numbers until a foreign-currency account exists); `fx_rates` table created by the base DDL |
| v1.0.10 | Add `users.font_scale` (REAL, default 1.0) and `users.accent` (TEXT, NULL = theme default) — per-user personalization |

**Indexes (v1.0.5):** `transactions(account_id, date)`, `transactions(category_id)`, `transactions(transfer_id)`, `accounts(user_id)`, `recurring_transactions(user_id)`, `financial_goals(user_id)`. `budgets` and `watchlist` are already indexed by their UNIQUE constraints. Created with `CREATE INDEX IF NOT EXISTS`, so re-running init is safe.

**Net-worth reconstruction:** `get_net_worth_history(user_id, months=12)` returns end-of-month totals without any balance-history table. Since balances already reflect all transactions, it starts from the current total and unwinds each month's net transaction flow: `end_of_month(M-1) = end_of_month(M) − flow(M)`. Everything is in home currency (flows convert at the current cached rate). Same-currency transfers net to zero across their two legs; cross-currency legs cancel up to the drift between the transfer's rate and today's.

---

## 6. Services Layer

| Service | Highlights |
|---|---|
| **AuthService** | `register()` (validates name/email/password length, unique email), `login()`; bcrypt hashing with constant-time verify. Recovery codes: `generate_recovery_codes()` returns 8 one-time codes (`XXXX-XXXX-XXXX`, `secrets`-based, lookalike-free alphabet) and stores only bcrypt hashes; `reset_password_with_code()` burns the matched code and sets the new password, returning the **same generic error** for unknown e-mail, no codes, or wrong code (no account probing). Input is normalized (case/dashes/spaces ignored). |
| **BackupService** | `create_backup(label)` writes `backups/budget_<timestamp>_<label>.db` and prunes to the 30 most recent; `list_backups()`, `restore_backup(path)`. |
| **RecurringService** | `process_due(user_id)` posts every rule whose `next_due_date ≤ today`, advancing the date with `dateutil.relativedelta`; a `while` loop catches up multiple missed periods. Handles transfers (`to_account_id`), skips paused rules (`is_active = 0`), and stops posting once a rule's occurrence passes its optional `end_date` (both also honored by `forecast()`). |
| **ImportExportService** | CSV/Excel import (column map: `date, amount, description, category, account`; invalid rows skipped, returns counts) and CSV/multi-sheet Excel export. Rows without a usable category are run through the user's auto-categorization rules. |
| **market_service** | Module of functions (not a class): keyless quotes from CoinGecko (crypto) and Stooq/Yahoo (stocks), `get_fx_rate()` conversion to the user's currency, and `fetch_quotes()` which batches stock requests into one call. |
| **FxService** | Keeps the `fx_rates` cache fresh for multi-currency accounts: `required_pairs()` derives the (account currency → home) pairs, `needs_refresh()` checks staleness (>24 h), `refresh()` fetches via `market_service.get_fx_rate` and stores both directions. Failed fetches keep the previous cached value (offline-safe). Also exports `CURRENCIES`, the UI picker list. |
| **update_service** | `check_for_update()` queries the GitHub "latest release" API, compares the tag to `version.__version__` via `is_newer()`, and captures the installer asset's download URL plus the `SHA256SUMS.txt` asset URL. On the installed build (`can_auto_update()`), Settings ▸ About offers one-click update: `download_file()` fetches `BudgetManagerSetup.exe`, `verify_installer()` checks its size against the release metadata and its SHA-256 against the published checksums (fail-closed: a bad or unfetchable checksum deletes the download and aborts; releases without checksums get the size check only), then `launch_installer()` runs it silently and the app quits so Inno upgrades in place and relaunches. Source/portable stay notify-only. |

---

## 7. Views Layer

All views inherit `QWidget`, take `db` and `user` in `__init__`, expose `refresh()`, and never import other view modules.

| File / Class | Responsibility |
|---|---|
| `login_view.LoginView` | Modal login/register dialog; emits `login_success(dict)`. |
| `main_window.MainWindow` | Sidebar (`NAV_ITEMS`, 10 entries) + `QStackedWidget`; owns signal wiring, `Ctrl+1…0` shortcuts, and the 24-hour auto-backup timer. |
| `dashboard_view.DashboardView` | 5 summary cards; spending donut, income-vs-expense bars, and the **net-worth line chart**; recent transactions. |
| `transactions_view.TransactionsView` | CRUD + transfers; date/category/account/search filters; emits `transaction_changed`. |
| `budget_view.BudgetView` | Month picker + per-category `BudgetBar`; UPSERT; emits `budget_changed`. |
| `goals_view.GoalsView` | `GoalProgressCard` grid; add/edit/delete/deposit. |
| `accounts_view.AccountsView` | Account CRUD; emits `accounts_changed`. |
| `reports_view.ReportsView` | Summary / Categories / Cash Flow tabs; PDF/CSV/Excel export. |
| `recurring_view.RecurringView` | Recurring-rule CRUD; overdue rows highlighted. |
| `savings_view.SavingsView` | Savings-account grouping; interest this month/year/all-time cards, interest-over-time chart, history table. |
| `markets_view.MarketsView` | Watchlist; add/remove symbols; manual refresh (auto-refresh defaults to Off). |
| `settings_view.SettingsView` | Tabs: Appearance (theme + language), Currency (home currency + cached FX rates + manual refresh), Categories, Backup & Restore, Import Data, About (version + update check). Emits `theme_changed`, `language_changed`, `data_changed`. |
| `fx_refresh.FxRefreshWorker` | `QRunnable` that runs `FxService.refresh()` off the UI thread; used by the Settings Currency tab and MainWindow's quiet startup refresh. |
| `winutil` | Windows-only chrome: `apply_title_bar()` flips the native title bar dark/light via `DwmSetWindowAttribute`, and `TitleBarFilter` (installed app-wide in `main.py`) applies the current mode — driven by `theme.is_dark_theme()` — to every top-level window as it appears. No-ops on other platforms. |

**Reusable widgets (`views/widgets.py`):** `SummaryCard` (optional `delta=(text, color)` line from `delta_text()`/`delta_points()` — percent vs previous period, `invert=True` for metrics where up is bad), `GoalProgressCard`, `BudgetBar` (green <70%, yellow <90%, red ≥90%), `category_dot()` (cached colored-circle icons that tag categories in tables), `EmptyState` (icon + message + optional CTA button; `make_empty_state()` builds one).

**Chart styling (`views/chartutil.py`):** importing it points matplotlib at the UI font (Segoe UI with fallbacks); `money_axis(ax, axis="y")` formats ticks via `compact_money()` (`1500 → "1.5k"`). Used by every chart view.

**Toasts (`views/toast.py`):** `show_toast(any_widget, message, kind)` shows a transient pill (child of the widget's window — no focus stealing) that fades in/out via `QGraphicsOpacityEffect` + `QPropertyAnimation`; one at a time, new replaces old. Kinds: success/info/warning/error.

**App icon:** `assets/icon.ico` (multi-size, generated by `scripts/make_icon.py` — rerun only to change the design; the file is committed). Wired in four places: `app.setWindowIcon` + `SetCurrentProcessExplicitAppUserModelID` in `main.py`, `--icon`/`--add-data "assets;assets"` in both build scripts and `release.yml`, and `SetupIconFile` in `installer.iss`.

---

## 8. Internationalization (i18n)

`views/i18n.py` is the translation layer. **English is the source/key**: `tr("English text")` looks up the active language's table and falls back to the key itself when a translation is missing. French strings live in `_FR`. `set_language(code)` / `get_language()` switch the active language; the user's choice is persisted in `users.language` and applied at startup.

**DB-writing combos** display localized text but **store English values** (e.g. account types, frequencies), so the database stays language-independent. `month_abbr()` returns localized month abbreviations for charts.

---

## 9. Theme System

`views/theme.py` is registry-based: `THEMES` maps a stored key → (English label, palette dict), currently **dark, light, midnight, ocean, forest, sunset, sand**. The QSS is *generated* from the palette by `_qss()`, so adding a theme = adding one palette dict with the same token set (enforced by `tests/test_themes.py`) and registering it. `theme_qss(key)` returns the (cached) stylesheet, falling back to dark for unknown keys; `available_themes()` feeds the Settings combo (labels go through `tr()`); `--theme` accepts any registry key. Runtime switching reapplies the stylesheet at the root and clears child stylesheets to force repaint. `chart_colors()` returns a theme-aware palette (`bg`, `fg`, `muted`, `grid`, `income`, `expense`, `accent`) so Matplotlib figures match the active theme — the net-worth line uses `accent`.

**Personalization layers on top of the registry.** `set_font_scale(0.9–1.25)` scales every generated `font-size` (QSS cache is keyed on theme + scale + accent). `set_accent("#hex" | None)` overrides the accent tokens of *every* theme via `effective_palette()`: the gradient pair, hovers and the soft selection fill are all derived from the one chosen color (`_lighten`/`_darken`/`_mix` color math), so any accent works on any theme. Both are per-user (`users.font_scale` / `users.accent`) and applied in `main.py` after login (and on re-login after sign-out). A font-scale change rebuilds the UI in place — the same pattern as a language change — so code-created `QFont`s pick it up too.

**Bundled font (`views/fonts.py` + `assets/fonts/`):** Inter (Regular/Medium/SemiBold/Bold, OFL license included) is registered with Qt at startup (`load_fonts`) and with matplotlib (`chartutil`), and leads the QSS `font-family` list. `ui_font(pt, weight)` is the single source for code-created fonts: bundled family, user scale, and tabular numerals (`tnum` via `QFont.setFeature`, Qt 6.7+) so digits are fixed-width and amount columns align. Missing font files degrade to Segoe UI.

Common `objectName` targets: `sidebar`, `navBtn` (`:checked` = active), `card`, `heading`, `subheading`, `muted`, `danger`, `secondary`.

---

## 10. Security

- **Passwords:** bcrypt hashed; constant-time verify; never logged or stored in plaintext.
- **Recovery codes:** one-time codes for forgotten-password resets; only bcrypt hashes stored, single-use (burned on success), generic error message regardless of failure cause so the flow can't probe which e-mails exist. Codes never appear in the audit log.
- **SQL injection:** every statement uses `?` placeholders; no string interpolation of user input.
- **Data isolation:** queries filter by `user_id` (directly or via `accounts.user_id`); a user only sees their own data.
- **Backups:** written locally; `restore_backup` copies into place so a failure leaves the live DB intact.
- **Network:** the market and update services make outbound HTTPS calls to public, keyless endpoints only; no credentials are transmitted.
- **Verified updates:** the auto-updater validates the downloaded installer's size and SHA-256 against the release's published `SHA256SUMS.txt` (generated by `release.yml`) before executing it; any mismatch deletes the file and surfaces an error.

---

## 11. Data Locations

| Run mode | Data root |
|---|---|
| Source (`python main.py`) | `./data` (project folder) — keeps dev data working |
| Frozen `.exe` | `%APPDATA%\BudgetManager` (Windows) / `~/.local/share/BudgetManager` |

A one-file PyInstaller build unpacks to a temp dir Windows wipes on exit, so data **must not** live next to the executable. Consequently the source app and the packaged app use **separate** databases.

---

## 12. Build & Release Pipeline

**Local builds:**
```powershell
.\build.ps1            # dist\BudgetManager.exe (PyInstaller one-file)
.\build_installer.ps1  # installer_output\BudgetManagerSetup.exe (Inno Setup)
```

**Automated release** (`.github/workflows/release.yml`, triggered by pushing a `vX.Y.Z` tag):
1. Bump `__version__` in `version.py` to match the tag (the workflow **verifies** this and fails otherwise).
2. `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. A Windows runner builds the portable exe + installer and publishes a GitHub Release with both attached.

The publish step is **idempotent**: it creates the release if missing, otherwise uploads assets with `--clobber`, so a pre-existing release or a workflow re-run won't strand the binaries. **Do not pre-create the release manually** — just push the tag.

**CI** (`.github/workflows/ci.yml`) runs `pytest` on every push/PR.

---

## 13. Testing

Tests live in `tests/` and use isolated temp-file databases via `conftest.py` fixtures (`db`, `user_id`, `account_id`, `savings_id`).

```powershell
pytest                       # full suite (config in pytest.ini); must stay green
```

Coverage spans database CRUD, auth, recurring transfers, savings/interest, markets, watchlist, i18n, the update service, and net-worth history. An autouse conftest fixture drops bcrypt to its minimum cost (4 rounds) so password/recovery-code tests run in milliseconds instead of ~250 ms per hash; verification is cost-agnostic, so nothing tested changes. **Note:** `pytest --cov` can fail with a PyO3/bcrypt "initialized once" error in some environments — that's coverage re-importing bcrypt, not a real test failure. Plain `pytest` is clean.

---

## 14. Extending the Application

**New view:** create `views/x_view.py` (inherit `QWidget`, accept `db`/`user`, implement `refresh()`); add it to `NAV_ITEMS` and the `QStackedWidget` in `main_window.py`; wire any cross-view signals; add a `Ctrl+N` shortcut.

**New service:** create `services/x_service.py` taking `db`; keep it Qt-free and filter by `user_id`.

**New table/column:** add DDL to `SCHEMA_SQL` and an **idempotent** step in `_migrate()` (guard with a `PRAGMA table_info` check or `IF NOT EXISTS`); add CRUD methods and tests.

**New translatable string:** wrap user-facing text in `tr("...")` and add the French entry to `_FR` in `views/i18n.py`.

**New release:** bump `version.py`, add a `CHANGELOG.md` entry, merge, then tag.

---
---

# 🇫🇷 Documentation technique (Français)

> **Version :** 1.2.0 · **Python :** 3.12+ · **Pile :** PyQt6 · SQLite · Matplotlib

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Pile technologique](#2-pile-technologique)
3. [Structure du projet](#3-structure-du-projet)
4. [Architecture](#4-architecture-fr)
5. [Schéma de base de données et migrations](#5-schéma-de-base-de-données-et-migrations)
6. [Couche de services](#6-couche-de-services)
7. [Couche de vues](#7-couche-de-vues)
8. [Internationalisation (i18n)](#8-internationalisation-i18n-fr)
9. [Système de thème](#9-système-de-thème)
10. [Sécurité](#10-sécurité)
11. [Emplacements des données](#11-emplacements-des-données)
12. [Chaîne de compilation et de publication](#12-chaîne-de-compilation-et-de-publication)
13. [Tests](#13-tests-fr)
14. [Étendre l'application](#14-étendre-lapplication)

---

## 1. Vue d'ensemble

Budget Manager est une application de finances personnelles de bureau pour Windows (et exécutable depuis le code source sur tout système). Elle suit une architecture en couches : des vues PyQt6 en haut, une couche de services pour la logique métier, et un unique `DatabaseManager` qui possède tout le SQL contre une base SQLite embarquée. Les graphiques sont produits avec Matplotlib ; les rapports s'exportent en PDF/CSV/Excel.

**Fonctionnalités :** tableau de bord avec graphiques des dépenses, revenus vs dépenses et valeur nette sur 12 mois ; CRUD des transactions avec virements, recherche et filtres ; budgets mensuels ; objectifs financiers ; gestion multi-comptes avec soldes mis à jour automatiquement ; moteur de transactions/virements récurrents ; rapports avec export ; suivi de l'épargne et des intérêts ; liste de surveillance d'actions et crypto sans clé ; localisation anglais/français ; authentification bcrypt ; sauvegardes automatiques continues ; et une vérification de mise à jour GitHub informative seulement.

---

## 2. Pile technologique

| Composant | Bibliothèque | Rôle |
|---|---|---|
| Interface | PyQt6 ≥ 6.6 | Interface de bureau — widgets, signaux/slots, styles QSS |
| Base de données | sqlite3 (stdlib) | Stockage embarqué ; requêtes paramétrées ; connexions par thread |
| Graphiques | Matplotlib ≥ 3.8 | Camemberts, barres et courbes via le backend `QtAgg` |
| Traitement de données | pandas ≥ 2.1 | Import/export CSV/Excel |
| Hachage de mot de passe | bcrypt ≥ 4.1 | Hachage à sens unique |
| Rapports PDF | reportlab ≥ 4.0 | Génération de PDF mensuels |
| Export Excel | openpyxl ≥ 3.1 | Classeurs `.xlsx` |
| Calcul de dates | python-dateutil | Avancement des échéances récurrentes (dépendance transitive) |
| Tests | pytest (+ pytest-qt, pytest-cov) | Tests unitaires/d'intégration |
| Empaquetage | PyInstaller + Inno Setup | `.exe` portable et programme d'installation Windows |

---

## 3. Structure du projet

Voir l'arborescence dans la section anglaise [§3](#3-project-structure) — les noms de fichiers sont identiques. Points clés : `main.py` (point d'entrée + logique des chemins de données), `version.py` (source unique de la version), `database/schema.py` (tout le SQL et les migrations), `services/` (6 services sans dépendance Qt), `views/` (10 vues + `theme.py`, `i18n.py`, `widgets.py`), et `.github/workflows/` (CI + publication).

---

## 4. Architecture {#4-architecture-fr}

### 4.1 Couches

| Couche | Modules | Responsabilité |
|---|---|---|
| **Données** | `database/schema.py` | Tout le SQL, paramétré. Les vues ne touchent jamais au SQL directement. |
| **Services** | `services/` | Logique métier sans dépendance Qt (auth, sauvegarde, import/export, récurrent, marchés, mise à jour). |
| **Vues** | `views/` | Tous les widgets PyQt6. Lisent via la base/les services ; émettent des signaux à la modification. |
| **Contrôleur** | `main.py`, `main_window.py` | Démarrage, navigation, rafraîchissement inter-vues. |

### 4.2 Signaux/slots
Les vues ne se référencent jamais entre elles ; elles communiquent via `MainWindow`. Une modification dans une vue (ex. `TransactionsView.transaction_changed`) déclenche `refresh()` sur les vues dépendantes (Tableau de bord, Budgets, Rapports, Épargne). `SettingsView` émet `theme_changed` et `language_changed`, que `MainWindow` applique à toute l'application.

### 4.3 Sécurité des threads de la base
`DatabaseManager` conserve **une connexion SQLite par thread** via `threading.local()`. `_local` est un attribut **d'instance** (pas de classe) — nécessaire pour que les nombreuses instances de la suite de tests ne partagent pas une connexion. Le service de marchés effectue des E/S réseau sur des threads de travail, d'où l'importance des connexions par thread.

### 4.4 Gestion des erreurs des dialogues
Chaque `_save()` de dialogue entoure les appels à la base d'un `try/except` et affiche un `QMessageBox.critical` en cas d'échec (sinon PyQt6 absorberait l'exception dans le slot et le dialogue semblerait figé, sans retour).

### 4.5 Séquence de démarrage
Identique à la section anglaise [§4.5](#45-startup-sequence) : analyse des arguments (`--reset`/`--seed`), politique High-DPI **avant** `QApplication()`, création de la base et des services, dialogue de connexion bloquant, application de la langue, puis `MainWindow` (10 vues, câblage des signaux, minuterie de sauvegarde).

---

## 5. Schéma de base de données et migrations

Requêtes paramétrées partout ; clés étrangères activées. Tables : `users`, `accounts`, `categories`, `transactions`, `budgets`, `financial_goals`, `recurring_transactions`, `watchlist`, `fx_rates`, `recovery_codes`, `category_rules`.

**Colonnes et relations clés :**
- `users` — `password` bcrypt, `currency` (la **devise principale**, CAD par défaut), `language` (`'en'`/`'fr'`).
- `accounts` — `account_type` ∈ {Checking, Savings, Credit Card, Cash}, `current_balance` (tenu à jour à chaque mutation de transaction), `currency` (la devise propre du compte ; les montants des transactions y vivent).
- `fx_rates` — taux de change en cache (`base`, `quote`, `rate`, `updated` ; PK `(base, quote)`). `set_fx_rate()` stocke **les deux sens**. Les requêtes d'agrégation convertissent les montants par compte vers la devise principale via le fragment SQL `DatabaseManager._FX` — `COALESCE((SELECT rate …), 1.0)` — un taux manquant dégrade donc en 1:1 au lieu d'échouer. Aucun historique de taux : les conversions historiques utilisent le taux courant (approximation documentée).
- `categories` — **globales** (pas de `user_id`) ; `type` ∈ {Income, Expense}. Inclut une catégorie système **Interest** pour le suivi des intérêts.
- `transactions` — `amount` signé (revenu +, dépense −) **dans la devise du compte** ; `transfer_id` (auto-référence) lie les deux volets d'un virement (exclus des agrégats revenus/dépenses). Les virements inter-devises stockent un montant différent par volet (`create_transfer(..., to_amount=)`).
- `budgets` — `UNIQUE(user_id, category_id, month, year)` ; définis par UPSERT.
- `recurring_transactions` — `frequency` ∈ {Weekly, Bi-weekly, Monthly, Quarterly, Yearly} ; `to_account_id` optionnel pour les virements récurrents ; `end_date` optionnel (NULL = sans fin) après lequel la règle cesse de publier ; `is_active` (1/0) pour mettre une règle en pause sans la supprimer.
- `watchlist` — symboles de marchés avec dernier cours/variation/devise en cache ; `UNIQUE(user_id, symbol, asset_type)`.
- `recovery_codes` — codes de réinitialisation à usage unique : `code_hash` (bcrypt du code normalisé — jamais de clair), `used_at` (NULL = encore utilisable ; conservé après usage pour que « codes restants » et l'historique restent fidèles). La régénération supprime l'ancien jeu de l'utilisateur.
- `category_rules` — catégorisation automatique : `pattern` comparé sans casse comme sous-chaîne de la description d'une transaction → `category_id`. `match_category_rule()` retient le motif correspondant le plus long (égalité → règle la plus ancienne). Appliqué par le dialogue de transaction pendant la saisie (sans jamais écraser un choix manuel) et par l'import CSV/Excel pour les lignes sans catégorie. `search_transactions()` (Ctrl+F global) vit aussi dans `DatabaseManager` : requête numérique → correspondance de montant sans tenir compte du signe, sinon LIKE sur description/notes, plafonné et du plus récent au plus ancien.

**Mise à jour automatique des soldes :** `create_transaction` → `solde += montant` ; `update_transaction` → annule l'ancien, applique le nouveau ; `delete_transaction` → `solde −= montant`.

**Migrations** exécutées à chaque init via `_migrate()`, chacune protégée pour être idempotente : v1.0.1 (recréation de `budgets` avec `user_id`), v1.0.2 (`transactions.transfer_id`), v1.0.3 (`recurring_transactions.to_account_id`), v1.0.4 (`users.language`), v1.0.5 (index de performance), v1.0.6 (`users.theme`), v1.0.7 (`recurring_transactions.end_date`, NULL = sans fin), v1.0.8 (`recurring_transactions.is_active`, 1 = actif / 0 = en pause), v1.0.9 (`accounts.currency`, **rétro-rempli depuis la devise de l'utilisateur** — mise à niveau sans perte ; table `fx_rates` créée par le DDL de base).

**Index (v1.0.5) :** `transactions(account_id, date)`, `transactions(category_id)`, `transactions(transfer_id)`, `accounts(user_id)`, `recurring_transactions(user_id)`, `financial_goals(user_id)`. `budgets` et `watchlist` sont déjà indexés par leurs contraintes UNIQUE. Créés avec `CREATE INDEX IF NOT EXISTS`, donc ré-exécuter l'init est sans risque.

**Reconstruction de la valeur nette :** `get_net_worth_history(user_id, months=12)` renvoie les totaux de fin de mois sans table d'historique des soldes. Comme les soldes reflètent déjà toutes les transactions, on part du total actuel et on « déroule » le flux net de chaque mois : `fin_de_mois(M-1) = fin_de_mois(M) − flux(M)`. Tout est en devise principale (les flux convertissent au taux en cache courant). Les virements en même devise s'annulent sur leurs deux volets ; les volets inter-devises s'annulent à la dérive près entre le taux du virement et celui du jour.

---

## 6. Couche de services

| Service | Points clés |
|---|---|
| **AuthService** | `register()` (valide nom/courriel/longueur du mot de passe, courriel unique), `login()` ; hachage bcrypt avec vérification à temps constant. Codes de récupération : `generate_recovery_codes()` renvoie 8 codes à usage unique (`XXXX-XXXX-XXXX`, générés via `secrets`, alphabet sans caractères ambigus) et ne stocke que des hachages bcrypt ; `reset_password_with_code()` consomme le code correspondant et définit le nouveau mot de passe, avec le **même message d'erreur générique** pour courriel inconnu, absence de codes ou mauvais code (pas de sondage de comptes). La saisie est normalisée (casse/tirets/espaces ignorés). |
| **BackupService** | `create_backup(label)` écrit `backups/budget_<horodatage>_<label>.db` et élague aux 30 plus récents ; `list_backups()`, `restore_backup(path)`. |
| **RecurringService** | `process_due(user_id)` publie chaque règle dont `next_due_date ≤ aujourd'hui`, en avançant la date avec `dateutil.relativedelta` ; une boucle `while` rattrape les périodes manquées. Gère les virements (`to_account_id`), ignore les règles en pause (`is_active = 0`) et cesse de publier dès qu'une occurrence dépasse la `end_date` optionnelle (les deux étant aussi respectées par `forecast()`). |
| **ImportExportService** | Import CSV/Excel (colonnes : `date, amount, description, category, account` ; lignes invalides ignorées, renvoie les compteurs) et export CSV / Excel multi-feuilles. Les lignes sans catégorie exploitable passent par les règles de catégorisation automatique de l'utilisateur. |
| **market_service** | Module de fonctions (pas une classe) : cours sans clé depuis CoinGecko (crypto) et Stooq/Yahoo (actions), conversion `get_fx_rate()` vers la devise de l'utilisateur, et `fetch_quotes()` qui regroupe les requêtes d'actions en un seul appel. |
| **FxService** | Tient à jour le cache `fx_rates` pour les comptes multi-devises : `required_pairs()` dérive les paires (devise du compte → principale), `needs_refresh()` vérifie l'ancienneté (>24 h), `refresh()` récupère via `market_service.get_fx_rate` et stocke les deux sens. Un échec de récupération conserve la valeur en cache (sûr hors ligne). Exporte aussi `CURRENCIES`, la liste du sélecteur. |
| **update_service** | `check_for_update()` interroge l'API « latest release » de GitHub, compare le tag à `version.__version__` via `is_newer()` et récupère le lien de l'installateur ainsi que l'URL de l'actif `SHA256SUMS.txt`. Sur la version installée (`can_auto_update()`), Paramètres ▸ À propos propose la mise à jour en un clic : `download_file()` télécharge `BudgetManagerSetup.exe`, `verify_installer()` vérifie sa taille par rapport aux métadonnées de la release et son SHA-256 par rapport aux sommes publiées (échec = fermeture : une somme invalide ou impossible à récupérer supprime le téléchargement et annule ; les releases sans sommes n'ont que le contrôle de taille), puis `launch_installer()` le lance en mode silencieux et l'application se ferme pour qu'Inno mette à jour sur place et relance. Les versions source/portable restent informatives seulement. |

---

## 7. Couche de vues

Toutes les vues héritent de `QWidget`, prennent `db` et `user` dans `__init__`, exposent `refresh()`, et n'importent jamais d'autres modules de vue. L'inventaire des 10 vues correspond à la section anglaise [§7](#7-views-layer) : Login, MainWindow (barre latérale `NAV_ITEMS` + `QStackedWidget`, raccourcis `Ctrl+1…0`, minuterie de sauvegarde), Dashboard (cartes + camembert, barres, **courbe de valeur nette**), Transactions (CRUD + virements + filtres), Budgets, Goals, Accounts, Reports, Recurring, Savings, Markets, Settings (Apparence, Devise — devise principale + taux FX en cache + actualisation manuelle —, Catégories, Sauvegarde, Import, À propos). `fx_refresh.FxRefreshWorker` (QRunnable) exécute `FxService.refresh()` hors du fil UI, pour l'onglet Devise et l'actualisation silencieuse au démarrage. `winutil` (Windows uniquement) assombrit la barre de titre native selon `theme.is_dark_theme()` via `DwmSetWindowAttribute`, appliqué à chaque fenêtre par un filtre d'événements global. L'icône de l'application (`assets/icon.ico`, générée par `scripts/make_icon.py`) est branchée dans `main.py`, les scripts de build (`--icon`, `--add-data`) et `installer.iss` ; `views/widgets.py` fournit aussi `category_dot()` (pastilles de couleur des catégories), `EmptyState` (icône + message + bouton d'action pour les écrans vides) et les aides de delta (`delta_text()`/`delta_points()`) des cartes du tableau de bord. `views/chartutil.py` aligne matplotlib sur la police de l'interface et formate les axes monétaires en ticks compacts (« 1.5k ») ; `views/toast.py` affiche des notifications éphémères en fondu (`show_toast`).

**Widgets réutilisables (`views/widgets.py`) :** `SummaryCard`, `GoalProgressCard`, `BudgetBar` (vert <70 %, jaune <90 %, rouge ≥90 %).

---

## 8. Internationalisation (i18n) {#8-internationalisation-i18n-fr}

`views/i18n.py` est la couche de traduction. **L'anglais est la source/la clé** : `tr("texte anglais")` cherche dans la table de la langue active et retombe sur la clé elle-même si une traduction manque. Les chaînes françaises sont dans `_FR`. `set_language(code)` / `get_language()` changent la langue active ; le choix de l'utilisateur est conservé dans `users.language` et appliqué au démarrage.

Les **listes déroulantes qui écrivent en base** affichent du texte localisé mais **stockent des valeurs anglaises** (ex. types de compte, fréquences), pour que la base reste indépendante de la langue. `month_abbr()` renvoie les abréviations de mois localisées pour les graphiques.

---

## 9. Système de thème

`views/theme.py` repose sur un registre : `THEMES` associe une clé stockée → (libellé anglais, palette), actuellement **dark, light, midnight, ocean, forest, sunset, sand**. La QSS est *générée* depuis la palette par `_qss()` — ajouter un thème = ajouter un dict de palette avec le même jeu de jetons (vérifié par `tests/test_themes.py`) et l'enregistrer. `theme_qss(clé)` renvoie la feuille de style (en cache) avec repli sur `dark` pour les clés inconnues ; `available_themes()` alimente la liste des Paramètres (libellés passés par `tr()`) ; `--theme` accepte toute clé du registre. Le changement à l'exécution réapplique la feuille de style à la racine et efface les feuilles enfants pour forcer le redessin. `chart_colors()` renvoie une palette adaptée au thème (`bg`, `fg`, `muted`, `grid`, `income`, `expense`, `accent`) afin que les figures Matplotlib correspondent au thème — la courbe de valeur nette utilise `accent`.

**La personnalisation se superpose au registre.** `set_font_scale(0.9–1.25)` met à l'échelle chaque `font-size` générée (cache QSS indexé par thème + échelle + accent). `set_accent("#hex" | None)` remplace les jetons d'accent de *tous* les thèmes via `effective_palette()` : dégradé, survols et fond de sélection dérivent tous de la couleur choisie. Les deux préférences sont par utilisateur (`users.font_scale` / `users.accent`, migration v1.0.10) et appliquées après connexion. Un changement d'échelle reconstruit l'interface sur place (même mécanisme qu'un changement de langue). **Police embarquée** : Inter (OFL, licence incluse dans `assets/fonts/`) est enregistrée auprès de Qt (`views/fonts.py, load_fonts`) et de matplotlib, et arrive en tête de la liste `font-family` de la QSS ; `ui_font()` fournit les QFont créées par le code (famille, échelle, chiffres tabulaires `tnum` pour des colonnes de montants alignées). En cas de fichiers manquants, repli sur Segoe UI.

Cibles `objectName` courantes : `sidebar`, `navBtn` (`:checked` = actif), `card`, `heading`, `subheading`, `muted`, `danger`, `secondary`.

---

## 10. Sécurité

- **Mots de passe :** hachés avec bcrypt ; vérification à temps constant ; jamais journalisés ni stockés en clair.
- **Codes de récupération :** codes à usage unique pour réinitialiser un mot de passe oublié ; seuls des hachages bcrypt sont stockés, usage unique (consommés en cas de succès), message d'erreur générique quelle que soit la cause de l'échec pour empêcher de sonder quels courriels existent. Les codes n'apparaissent jamais dans le journal d'activité.
- **Mises à jour vérifiées :** l'auto-updater valide la taille et le SHA-256 de l'installateur téléchargé par rapport au `SHA256SUMS.txt` publié avec la release (généré par `release.yml`) avant de l'exécuter ; toute différence supprime le fichier et affiche une erreur.
- **Injection SQL :** chaque instruction utilise des `?` ; aucune interpolation de chaîne d'entrée utilisateur.
- **Isolation des données :** les requêtes filtrent par `user_id` (directement ou via `accounts.user_id`) ; un utilisateur ne voit que ses propres données.
- **Sauvegardes :** écrites localement ; `restore_backup` copie en place pour qu'un échec laisse la base active intacte.
- **Réseau :** les services de marchés et de mise à jour ne font que des appels HTTPS sortants vers des points publics sans clé ; aucun identifiant transmis.

---

## 11. Emplacements des données

| Mode d'exécution | Racine des données |
|---|---|
| Source (`python main.py`) | `./data` (dossier du projet) |
| `.exe` figé | `%APPDATA%\BudgetManager` (Windows) / `~/.local/share/BudgetManager` |

Une compilation PyInstaller mono-fichier se décompresse dans un dossier temporaire que Windows efface à la sortie ; les données ne **doivent donc pas** se trouver à côté de l'exécutable. Par conséquent, l'application source et l'application empaquetée utilisent des bases **distinctes**.

---

## 12. Chaîne de compilation et de publication

**Compilations locales :**
```powershell
.\build.ps1            # dist\BudgetManager.exe (PyInstaller mono-fichier)
.\build_installer.ps1  # installer_output\BudgetManagerSetup.exe (Inno Setup)
```

**Publication automatique** (`.github/workflows/release.yml`, déclenchée par le push d'un tag `vX.Y.Z`) :
1. Mettre `__version__` dans `version.py` au niveau du tag (le workflow le **vérifie** et échoue sinon).
2. `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. Un runner Windows compile l'exe portable + le programme d'installation et publie une Release GitHub avec les deux en pièces jointes.

L'étape de publication est **idempotente** : elle crée la release si absente, sinon téléverse les fichiers avec `--clobber`, de sorte qu'une release pré-existante ou une ré-exécution du workflow n'abandonne pas les binaires. **Ne créez pas la release manuellement à l'avance** — poussez seulement le tag.

La **CI** (`.github/workflows/ci.yml`) exécute `pytest` à chaque push/PR.

---

## 13. Tests {#13-tests-fr}

Les tests sont dans `tests/` et utilisent des bases temporaires isolées via les fixtures de `conftest.py` (`db`, `user_id`, `account_id`, `savings_id`).

```powershell
pytest                       # suite complète (config dans pytest.ini) ; doit rester verte
```

La couverture inclut le CRUD de la base, l'authentification, les virements récurrents, l'épargne/les intérêts, les marchés, la liste de surveillance, l'i18n, le service de mise à jour et l'historique de valeur nette. Une fixture conftest automatique abaisse bcrypt à son coût minimal (4 tours) pour que les tests de mots de passe/codes de récupération s'exécutent en millisecondes au lieu de ~250 ms par hachage ; la vérification étant indépendante du coût, rien de ce qui est testé ne change. **Note :** `pytest --cov` peut échouer avec une erreur PyO3/bcrypt « initialized once » dans certains environnements — c'est la couverture qui réimporte bcrypt, pas un vrai échec de test. Le `pytest` simple est propre.

---

## 14. Étendre l'application

**Nouvelle vue :** créez `views/x_view.py` (hériter de `QWidget`, accepter `db`/`user`, implémenter `refresh()`) ; ajoutez-la à `NAV_ITEMS` et au `QStackedWidget` dans `main_window.py` ; câblez les signaux inter-vues ; ajoutez un raccourci `Ctrl+N`.

**Nouveau service :** créez `services/x_service.py` prenant `db` ; gardez-le sans Qt et filtrez par `user_id`.

**Nouvelle table/colonne :** ajoutez le DDL à `SCHEMA_SQL` et une étape **idempotente** dans `_migrate()` (protégée par un `PRAGMA table_info` ou `IF NOT EXISTS`) ; ajoutez les méthodes CRUD et des tests.

**Nouvelle chaîne traduisible :** entourez le texte visible de `tr("...")` et ajoutez l'entrée française à `_FR` dans `views/i18n.py`.

**Nouvelle version :** mettez à jour `version.py`, ajoutez une entrée à `CHANGELOG.md`, fusionnez, puis taguez.
