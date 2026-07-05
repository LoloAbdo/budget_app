# CLAUDE.md — Budget Manager project guide

Personal-finance desktop app. **Python 3.12 · PyQt6 · SQLite · matplotlib.**
GitHub: `LoloAbdo/budget_app` (public). `gh` CLI is authenticated on this machine.

## Run / test / build / release

```powershell
python main.py                 # run from source (uses ./data/budget.db)
python main.py --seed          # seed demo data (demo@budget.app / demo1234)
pytest                         # full test suite (config in pytest.ini); 90+ tests, must stay green
.\build.ps1                    # build dist\BudgetManager.exe (PyInstaller, one-file)
.\build_installer.ps1          # build installer_output\BudgetManagerSetup.exe (Inno Setup)
```

**Releasing is automatic** via `.github/workflows/release.yml`:
1. Bump `__version__` in `version.py` (must match the tag — the workflow enforces this).
2. Commit, then `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. GitHub builds the app + installer on a Windows runner and publishes a Release
   with **both** `BudgetManagerSetup.exe` (installer) and `BudgetManager.exe` (portable).
4. Add a matching entry to `CHANGELOG.md` (Keep a Changelog format) when bumping the version.

The publish step is **idempotent** (creates the release if missing, else uploads with
`--clobber`) — so re-runs and re-pushed tags are safe. **Do not pre-create the GitHub
Release manually** — just push the tag; manually pre-creating it is what stranded v1.1.0's
binaries. After pushing a tag, the build takes ~5 min and the Release only appears at the
very last step, so "release not found" right after tagging is normal — wait or `gh run watch`.

Current version: **2.2.0**. Releases: v1.0.0 (portable only), v1.0.1 (+ installer),
v1.1.0 (DB indexes), v1.2.0 (net-worth chart), v1.3.0 (budget alerts),
v1.4.0 (change password + pinned deps), v1.5.0 (sortable table columns),
v1.6.0 (table UX polish + persisted theme/window state),
v1.7.0 (cash-flow forecast + transaction export),
v1.8.0 (money-rounding fix + activity log),
v1.9.0 (end date for recurring transactions),
v1.10.0 (activity log viewer, upcoming bills, pause/resume recurring, copy budgets, duplicate transaction),
v1.11.0 (one-click auto-update on the installed build),
v2.0.0 (multi-currency accounts + home-currency conversion),
v2.1.0 (7-theme registry: dark/light/midnight/ocean/forest/sunset/sand),
v2.2.0 (style overhaul: app icon, dark title bar, chart/table polish, deltas, empty states, toasts, bundled Inter font, font scale, custom accent).

## Architecture
- `main.py` — entry point + data-path logic.
- `database/schema.py` — `DatabaseManager` (all SQL, parameterized) + idempotent migrations run on every init (latest: v1.0.10 adds per-user `font_scale` + `accent`; v1.0.9 adds a per-account `currency` column backfilled from the owner's home currency plus the `fx_rates` cache table; v1.0.8 adds an `is_active` flag to recurring_transactions; v1.0.7 adds a nullable `end_date`; v1.0.6 adds a per-user `theme` column; v1.0.5 adds performance indexes). Every mutating method calls `_log()` to append an entry to the `audit_log` table (append-only activity trail, exported via `ImportExportService.export_audit_log_csv`); internal side-effects (balance updates, watch-cache refreshes) and password hashes are deliberately not logged. Money is rounded to cents on write via `_money()`, and balance updates use SQL `ROUND(...,2)`. Analytics helpers include `get_net_worth_history()` (dashboard net-worth trend, reconstructed by unwinding monthly flow — no balance-history table) and `get_budget_alerts()` (categories ≥90% of monthly budget).
- `services/` — `auth` (login/register + one-time password recovery codes: bcrypt-hashed in the `recovery_codes` table, generated in Settings ▸ Security, consumed by the login screen's "Forgot password?" page; the reset flow returns one generic error for every failure cause so e-mails can't be probed), `backup`, `import_export`, `recurring`, `market` (stocks/crypto), `update` (GitHub releases check), `fx` (exchange-rate cache refresh; also exports the `CURRENCIES` picker list). `RecurringService.forecast()` projects the combined balance forward from recurring income/expenses in the home currency (powers the Forecast panel; transfers excluded since they don't change net worth).
- `views/` — PyQt6 panels; `main_window.py` wires the sidebar + signals. `theme.py` holds QSS + chart colors (incl. the virtual `"auto"` theme — resolved to dark/light via `resolve_theme()` from the OS color scheme; MainWindow re-applies live on `colorSchemeChanged`). `i18n.py` is the translation layer. `activity_view.py` is a read-only in-app viewer for the `audit_log`. `search_dialog.py` is the global Ctrl+F search (debounced, jumps to the Transactions panel via `TransactionsView.apply_global_search`). `winutil.py` darkens native Windows title bars to match dark themes (app-wide event filter installed in `main.py`).
- `assets/icon.ico` — the app icon (committed; regenerate with `scripts/make_icon.py` only to change the design). Referenced by `main.py`, both build scripts + `release.yml` (`--icon`, `--add-data "assets;assets"`), and `installer.iss` — keep all four in sync.
- `tests/` — pytest; `conftest.py` has shared fixtures (`db`, `user_id`, `account_id`, `savings_id`).
- Docs: `USER_GUIDE.md` + `TECHNICAL.md` are bilingual (English first, French after) and `CHANGELOG.md` tracks releases. Keep them current when behavior or version changes.

## Key conventions & decisions
- **i18n**: `tr("English text")` is the key (English = source). French table in `views/i18n.py`. Missing key → falls back to the key. Combos that write to the DB display localized text but store English values.
- **Data location**: source run → `./data`; frozen `.exe` → `%APPDATA%\BudgetManager`. (One-file exe unpacks to a temp dir Windows wipes, so data must live in %APPDATA%.) Source and exe therefore use **separate** databases.
- **Multi-currency (v2.0.0)**: each account has a `currency`; transaction amounts live in their account's currency. All aggregates (total balance, monthly summary/totals, spending by category, budgets' `actual_spending`, net-worth history, forecast) convert to the user's home currency in SQL via the `DatabaseManager._FX` fragment — a `COALESCE(fx_rates lookup, 1.0)` multiplier, so "no rate cached" degrades to 1:1 instead of erroring. `set_fx_rate` stores **both directions**; `FxService.refresh()` fetches via `market_service.get_fx_rate`. MainWindow quietly refreshes stale rates (>24 h) at launch; Settings ▸ Currency shows the cache + manual refresh. Cross-currency transfers store a different amount per leg (`create_transfer(..., to_amount=)`). Changing an account's currency **relabels** (never converts) its amounts. No rate history is kept — historical conversions use today's rate, so net-worth history for foreign accounts is an approximation by design.
- **Savings/interest**: editing a Savings account's balance records the unexplained delta as a signed "Interest" income transaction (auto-detect, with an opt-out checkbox). Summary in the Savings tab.
- **Markets**: keyless data (CoinGecko crypto + Stooq/Yahoo stocks), converted to the user's currency. Auto-refresh defaults to **Off (manual)**; stock requests are batched into one call.
- **Update check + auto-update**: compares `version.py` to the latest GitHub release. On the **installed** build (`update_service.can_auto_update()` — frozen and not a one-file exe), Settings ▸ About shows **⤓ Update now**, which downloads `BudgetManagerSetup.exe`, **verifies it** (size vs the release asset + SHA-256 vs the release's `SHA256SUMS.txt`, generated by `release.yml`; fail-closed when a checksums asset exists, size-only for pre-2.4.0 releases), runs it silently (`/SILENT /CLOSEAPPLICATIONS /NORESTART`), and quits so the Inno installer upgrades in place and relaunches (its `[Run]` entry has no `skipifsilent`, which is what makes the silent relaunch work). Source runs and the **portable** one-file exe stay notify-only (download link). The updater is pure-Python/testable; the actual install+relaunch can only be verified on a real installed build.
- **Auto-categorization rules** (Settings ▸ Rules, `category_rules` table): case-insensitive substring on description → category; longest pattern wins. Applied live in the transaction dialog (never overrides a manual pick) and on CSV/Excel import when the row has no valid category.
- **Preferences split**: per-user prefs that belong with the data (currency, `language`, `theme`, `font_scale`, `accent` — the last two added by migration v1.0.10) live in the `users` table; per-machine window state (size/position + last-open panel) lives in `QSettings` (org `BudgetApp` / app `Budget Manager`), saved in `MainWindow.closeEvent`. `--theme` overrides the saved theme for one run.
- **Fonts & personalization**: the app bundles Inter (`assets/fonts/`, OFL license file included — keep it) loaded by `views/fonts.py`; `ui_font()` is the only sanctioned way to create QFonts in code (family + user scale + tabular numerals). Font-scale changes rebuild the UI like a language change; a custom accent overrides every theme's accent tokens via `theme.effective_palette()` (QSS cache keys on theme+scale+accent). Bundling Inter also fixed offscreen screenshot text rendering in headless checks.

## Gotchas / lessons
- `DatabaseManager._local` is **per-instance** (not a class attr) — required so the test suite's many DB instances don't share a connection.
- `pytest --cov` can fail with a PyO3/bcrypt "initialized once" error in some envs — that's coverage re-importing bcrypt, not a test failure. Plain `pytest` is clean.
- Tests run bcrypt at minimum cost via an autouse conftest fixture (`_fast_bcrypt`, 4 rounds) — don't benchmark hashing inside tests, and don't remove the fixture (the auth suite goes from ~1 s back to ~30 s without it).
- Build artifacts (`build/`, `dist/`, `installer_output/`, `*.spec`) are gitignored — never commit the binaries; attach to Releases.
- Never commit personal data: `data/`, `backups/`, `exports/` are gitignored.
- `scripts/seed_sample_data.py` is **idempotent** — it skips if the demo user already has accounts (use `--reset` then `--seed` to re-seed). Keep console `print`s ASCII: the Windows cp1252 console crashes on emoji (`UnicodeEncodeError`). The seed script is not yet covered by tests.
- `.claude/settings.local.json` is gitignored and untracked (per-machine settings) — keep it that way so local config never lands in commits/tags.
- `requirements.txt` is fully pinned (`==`) for reproducible release builds — bump deliberately, then re-run tests + a real build before tagging.

## Working style
Commit/push only when asked. Each feature: explore → edit → verify (run tests / offscreen Qt checks / real builds) → report. PRs via `gh`; CI (`.github/workflows/ci.yml`) runs `pytest` on push/PR.
