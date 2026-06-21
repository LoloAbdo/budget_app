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

Current version: **1.5.0**. Releases: v1.0.0 (portable only), v1.0.1 (+ installer),
v1.1.0 (DB indexes), v1.2.0 (net-worth chart), v1.3.0 (budget alerts),
v1.4.0 (change password + pinned deps), v1.5.0 (sortable table columns).

## Architecture
- `main.py` — entry point + data-path logic.
- `database/schema.py` — `DatabaseManager` (all SQL, parameterized) + idempotent migrations run on every init (latest: v1.0.5 adds performance indexes). Analytics helpers include `get_net_worth_history()` (dashboard net-worth trend, reconstructed by unwinding monthly flow — no balance-history table) and `get_budget_alerts()` (categories ≥90% of monthly budget).
- `services/` — `auth`, `backup`, `import_export`, `recurring`, `market` (stocks/crypto), `update` (GitHub releases check).
- `views/` — PyQt6 panels; `main_window.py` wires the sidebar + signals. `theme.py` holds QSS + chart colors. `i18n.py` is the translation layer.
- `tests/` — pytest; `conftest.py` has shared fixtures (`db`, `user_id`, `account_id`, `savings_id`).
- Docs: `USER_GUIDE.md` + `TECHNICAL.md` are bilingual (English first, French after) and `CHANGELOG.md` tracks releases. Keep them current when behavior or version changes.

## Key conventions & decisions
- **i18n**: `tr("English text")` is the key (English = source). French table in `views/i18n.py`. Missing key → falls back to the key. Combos that write to the DB display localized text but store English values.
- **Data location**: source run → `./data`; frozen `.exe` → `%APPDATA%\BudgetManager`. (One-file exe unpacks to a temp dir Windows wipes, so data must live in %APPDATA%.) Source and exe therefore use **separate** databases.
- **Savings/interest**: editing a Savings account's balance records the unexplained delta as a signed "Interest" income transaction (auto-detect, with an opt-out checkbox). Summary in the Savings tab.
- **Markets**: keyless data (CoinGecko crypto + Stooq/Yahoo stocks), converted to the user's currency. Auto-refresh defaults to **Off (manual)**; stock requests are batched into one call.
- **Update check**: notify-only — compares `version.py` to the latest GitHub release and links the download; does not auto-install.

## Gotchas / lessons
- `DatabaseManager._local` is **per-instance** (not a class attr) — required so the test suite's many DB instances don't share a connection.
- `pytest --cov` can fail with a PyO3/bcrypt "initialized once" error in some envs — that's coverage re-importing bcrypt, not a test failure. Plain `pytest` is clean.
- Build artifacts (`build/`, `dist/`, `installer_output/`, `*.spec`) are gitignored — never commit the binaries; attach to Releases.
- Never commit personal data: `data/`, `backups/`, `exports/` are gitignored.
- `scripts/seed_sample_data.py` is **idempotent** — it skips if the demo user already has accounts (use `--reset` then `--seed` to re-seed). Keep console `print`s ASCII: the Windows cp1252 console crashes on emoji (`UnicodeEncodeError`). The seed script is not yet covered by tests.
- `.claude/settings.local.json` is gitignored and untracked (per-machine settings) — keep it that way so local config never lands in commits/tags.
- `requirements.txt` is fully pinned (`==`) for reproducible release builds — bump deliberately, then re-run tests + a real build before tagging.

## Working style
Commit/push only when asked. Each feature: explore → edit → verify (run tests / offscreen Qt checks / real builds) → report. PRs via `gh`; CI (`.github/workflows/ci.yml`) runs `pytest` on push/PR.
