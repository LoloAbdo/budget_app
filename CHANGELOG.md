# Changelog

All notable changes to Budget Manager are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.7.0] - 2026-06-23

### Added
- **Cash-flow forecast** — a new Forecast panel projects your combined account
  balance forward (3 / 6 / 12 months) from recurring income and expenses, with
  summary cards, a projected-balance chart, and a table of upcoming activity
  that flags any projected overdraft. Built entirely on existing data (transfers
  between your own accounts are excluded); logic in `RecurringService.forecast()`
  with new tests. English/French localized.
- **Export transactions** from the Transactions panel: a new ⤓ Export button
  saves the *currently filtered* list (date range, category, account, search) to
  CSV or Excel. English/French localized; covered by new tests.

## [1.6.0] - 2026-06-21

### Added
- **Keyboard shortcuts** on the data tables: press `Delete` to remove the
  selected row and `Enter` to edit it (matching double-click), in Transactions,
  Accounts, Recurring, and Markets (Markets supports `Delete` only). Shortcuts
  fire only while the table is focused.
- **Empty-state messages** for the Transactions, Accounts, Recurring, Savings
  (interest history), and dashboard (recent transactions) tables: instead of a
  blank grid, an empty list now shows a friendly prompt, and the CRUD tables'
  wording adapts ("nothing yet" vs. "nothing matches your filters"). English/
  French localized.
- **Shortcut hints** in the Edit/Delete/Remove button tooltips (e.g. "Delete
  selected (Del)") so the new keyboard shortcuts are discoverable.
- **Window remembers its size, position, and last-open panel** between launches
  (stored via `QSettings`).

### Fixed
- **Theme choice now persists across restarts.** The dark/light preference is
  saved per-user (new `theme` column, migration v1.0.6) just like the language,
  instead of resetting to dark every launch. An explicit `--theme` flag still
  overrides the saved value for that run.

### Changed
- `.claude/settings.local.json` is now gitignored and untracked, so per-machine
  Claude Code settings no longer land in commits and tags.

## [1.5.0] - 2026-06-20

### Added
- **Click-to-sort table columns** across every panel (Transactions, Accounts,
  Recurring, Markets, Settings ▸ Categories, Savings, and the dashboard's recent
  transactions). Click a column header to sort ascending, click again for
  descending. Currency and percentage columns sort by their underlying number
  (so `$1,000` comes after `$200`, not before), via a new
  `views/sortable.py` helper.

## [1.4.0] - 2026-06-16

### Added
- **Change password** in Settings ▸ Security: verifies the current password,
  enforces a 6-character minimum, and requires the new password to differ from
  the old one. Backed by `AuthService.change_password()` /
  `DatabaseManager.update_user_password()`. English/French localized.

### Changed
- Pinned all dependencies in `requirements.txt` to exact versions for
  reproducible release builds, and declared `python-dateutil` explicitly
  (previously only present transitively via pandas/matplotlib).

## [1.3.1] - 2026-06-16

### Fixed
- PDF report export always failed: `PDFReportGenerator.generate_monthly_report()`
  called `get_budgets()` with the wrong arguments (`month, year` instead of
  `user_id, month, year`), raising a `TypeError` before the file was written.
  Added regression tests covering the full report path, including the
  budget-status section.

## [1.3.0] - 2026-06-13

### Added
- **Budget alerts** on the dashboard: a card listing categories that have
  reached 90% or more of their monthly budget, marked "Near limit" (amber) or
  "Over budget" (red) and sorted worst-first. Backed by
  `DatabaseManager.get_budget_alerts()`. English/French localized.

## [1.2.0] - 2026-06-13

### Added
- **Net worth trend** on the dashboard: a line chart of total net worth over
  the last 12 months. Historical points are reconstructed from the current
  account balances by unwinding each month's transaction flow (no schema
  change required). Backed by `DatabaseManager.get_net_worth_history()`.

## [1.1.0] - 2026-06-11

### Added
- Database indexes on the transaction query hot paths
  (`transactions(account_id, date)`, `transactions(category_id)`,
  `transactions(transfer_id)`, `accounts(user_id)`,
  `recurring_transactions(user_id)`, `financial_goals(user_id)`). The schema
  previously had no indexes, so the main transaction list was a full table
  scan; the query planner now uses indexed lookups.

### Changed
- `--seed` is now idempotent: if the demo user already has data, seeding skips
  instead of duplicating accounts, transactions, goals and recurring entries.

### Fixed
- `--seed` crashed with a `TypeError` because `upsert_budget()` was called
  without its `user_id` argument.
- `--seed` crashed with a `UnicodeEncodeError` on the Windows (cp1252) console
  when printing the completion message, preventing the app from launching.

## [1.0.1] - earlier

### Added
- Windows installer (Inno Setup), attached to GitHub Releases alongside the
  portable executable.

## [1.0.0] - earlier

- Initial public release (portable executable only).

[Unreleased]: https://github.com/LoloAbdo/budget_app/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/LoloAbdo/budget_app/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/LoloAbdo/budget_app/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/LoloAbdo/budget_app/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/LoloAbdo/budget_app/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/LoloAbdo/budget_app/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/LoloAbdo/budget_app/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/LoloAbdo/budget_app/releases/tag/v1.0.0
