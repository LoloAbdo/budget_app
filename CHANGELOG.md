# Changelog

All notable changes to Budget Manager are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.10.0] - 2026-07-09

### Fixed
- **Buttons now fit their label in every language.** Buttons size to their
  text instead of a fixed width, so longer translated labels (e.g. in French)
  are shown in full rather than being cut off with an ellipsis.

### Added
- **Tables remember your column widths.** Resize a column in the Transactions,
  Accounts, Recurring, Activity Log, or Dashboard tables and your widths are
  saved per user — they stay put across refreshes, tab switches, and restarts.

## [2.9.0] - 2026-07-09

### Fixed
- **Recurring transactions now post without restarting the app.** When a
  recurring item comes due while the app is left open, opening the
  **Transactions** tab posts it right away and refreshes your balances,
  budgets and reports — no need to reload the app.
- **Budget alerts no longer hide a wiped-out rollover budget.** When a heavy
  overspend rolls forward and leaves a category with no room left at all, that
  category now correctly shows as over budget instead of being skipped.

## [2.8.0] - 2026-07-08

### Added
- **Debt payoff planner.** A new **Debts** panel lets you list what you owe
  (balance, interest rate and minimum payment) and builds a payoff plan. Choose
  the **Avalanche** strategy (attack the highest interest rate first — cheapest
  overall) or **Snowball** (clear the smallest balance first — quickest win),
  add an optional extra monthly payment, and see your debt-free date, total
  interest, and how much time and interest you save versus paying only the
  minimums. Each debt shows the month it's cleared. If your payments can't keep
  up with the interest, the plan says so instead of guessing.
- **Budget rollover.** Any budget can now carry its unused amount into the next
  month — tick **Roll unused amount into next month** when adding or editing a
  budget. Overspending carries forward too (as less room next month). The
  rollover accumulates across consecutive months and is folded into the
  budget's progress bar and alerts.

## [2.7.0] - 2026-07-07

### Added
- **"Remember me" on the login screen.** Tick it and your email and password
  are saved on this computer so the next launch pre-fills them — just press
  Sign In. The password is encrypted at rest with Windows DPAPI (tied to your
  Windows account, never stored in plaintext, and unreadable by other users or
  on another machine); if encryption isn't available only the email is kept.
  Unticking it and signing in erases the saved credentials, and
  **Settings ▸ Security ▸ Saved Login** can forget them at any time.

### Changed
- **Readable Activity Log.** The activity log now reads in plain language
  instead of raw data: friendly timestamps ("Jul 7, 2026, 15:59"), plain item
  names ("Profile", "Recurring item"), and a human summary of each change
  ("Groceries · Amount: -52.40 · Date: 2026-07-07") in place of the JSON
  snapshot. Internal database IDs are hidden (the standalone ID column is gone).
  The full detail is still available via **Export**.
- **Localized What's New.** The changelog in Settings ▸ About now follows the
  app language, showing a full French translation when the app is in French and
  switching live when you change languages.

## [2.6.0] - 2026-07-07

### Added
- **What's New in About.** Settings ▸ About now shows the full changelog in a
  scrollable panel, so after updating you can see exactly what each version
  added. Rendered from the bundled `CHANGELOG.md` (a single source of truth,
  shipped with both the portable and installed builds).

## [2.5.0] - 2026-07-05

### Added
- **Four new themes.** **Nord** (calm blue-grey with a frost accent),
  **Dracula** (the classic purple-and-pink on slate), **High Contrast**
  (pure black, strong borders, vivid blue accent — an accessibility option),
  and **Sakura** (a soft cherry-blossom light theme with a rose accent),
  bringing the registry to eleven themes plus Auto.

## [2.4.0] - 2026-07-05

### Added
- **Auto-categorization rules.** Settings ▸ Rules maps description patterns to
  categories ("NETFLIX" → Subscriptions, case-insensitive substring; the
  longest matching pattern wins). Rules apply live while typing a new
  transaction (never overriding a manually picked category) and to CSV/Excel
  imports for rows without a category.
- **Global search.** Ctrl+F opens a search dialog that matches description,
  notes, or an exact amount (sign-insensitive) across all accounts and dates.
  Double-click or Enter jumps to the Transactions panel with the query applied
  and filters widened.
- **Auto theme.** A new "Auto (match Windows)" theme follows the OS light/dark
  setting and re-themes live when Windows switches modes. Available in
  Settings ▸ Appearance and as `--theme auto`.

### Security
- **Verified updates.** Each release now publishes `SHA256SUMS.txt`, and the
  in-app updater checks the installer's size and SHA-256 against it before
  launching — a corrupted or tampered download is deleted and reported instead
  of run. Releases without checksums (pre-2.4.0) still update with the size
  check only.

### Internal
- Tests hash bcrypt passwords at minimum cost (4 rounds), cutting the auth
  suite from ~28 s to ~1 s with no change to what's tested.

## [2.3.0] - 2026-07-04

### Added
- **Password recovery codes.** Settings ▸ Security can now generate 8 one-time
  recovery codes (shown once, with Copy / Save to file). A new **Forgot
  password?** flow on the login screen accepts your e-mail, one unused code,
  and a new password. Codes are stored as bcrypt hashes only, each works once,
  regenerating replaces the old set, and the reset flow returns the same
  generic error for a wrong e-mail or a wrong code so accounts can't be
  probed. Fully offline — nothing is sent anywhere.

## [2.2.0] - 2026-07-04

### Added
- **App icon.** Budget Manager finally has its own icon — a violet-gradient
  rounded square with a dollar glyph (generated by `scripts/make_icon.py`,
  committed as `assets/icon.ico`). It shows in the window title bar, the
  Windows taskbar (own AppUserModelID), the exe itself, the installer wizard,
  and Start Menu/desktop shortcuts.
- **Native title bar follows the theme.** On Windows, dark themes (Dark,
  Midnight, Ocean, Forest, Sunset) now get a dark title bar instead of the
  default white one — on every window, including dialogs and message boxes.
- **Table hover highlight.** Table cells subtly highlight under the cursor in
  every theme (selection still takes precedence).
- **Category color dots.** The Transactions table and the dashboard's Recent
  Transactions now tag each category with its color as a small dot, carrying
  the category color system beyond the charts.
- **Chart polish.** All charts now use the app's UI font (Segoe UI) instead of
  matplotlib's default, money axes show compact ticks (`1.5k`, `2.5M`) instead
  of raw numbers, and the spending donut labels each slice with its percentage
  (slices under 4% stay unlabeled to avoid clutter).
- **Dashboard deltas.** The summary cards now show how each number moved vs
  last month — "▲ 12% vs last month" in green/red (rising expenses read as
  red, rising income as green; the savings rate shows the change in points).
  Cards stay clean when there's no previous month to compare against.
- **Real empty states.** Blank panels now show an icon, a message, and — on
  Accounts, Transactions and Recurring — a call-to-action button that opens
  the relevant Add dialog. The button hides when rows are merely filtered out.
- **Toast notifications.** Actions now confirm themselves with a small pill
  that fades in at the bottom of the window and fades away ("Transaction
  added", "Transfer created", "Account deleted", recurring items posted at
  launch, "Exchange rates updated" after a background FX refresh) — replacing
  easy-to-miss status-bar messages.
- **Bundled Inter font.** The app now ships the Inter typeface (OFL-licensed,
  license included) and uses it everywhere — UI and charts — so it looks
  identical on every machine. Digits use tabular numerals, so amounts line up
  in perfect columns. Falls back to Segoe UI if the bundled files are missing.
- **Font size setting.** Settings ▸ Appearance gains a font-size picker
  (90% / 100% / 110% / 125%) that applies immediately to the entire app and is
  saved per user (`users.font_scale`, migration v1.0.10).
- **Custom accent color.** Pick any accent color (Settings ▸ Appearance) and
  every theme recolors around it — buttons, nav highlight, selections, focus
  rings and chart accents all derive from the one chosen color; Reset returns
  to the theme's own accent. Saved per user (`users.accent`).

## [2.1.0] - 2026-07-04

### Added
- **Five new UI themes.** Alongside Dark and Light: **Midnight** (pure-black
  OLED), **Ocean** (deep navy, cyan accent), **Forest** (dark green),
  **Sunset** (warm plum, rose→amber accent) and **Sand** (warm paper-like
  light theme, bronze accent). Pick one in Settings ▸ Appearance; charts
  recolor to match, the choice is saved per user, and `--theme <name>` still
  overrides it for a single run. The theme engine is now registry-based
  (`views/theme.py THEMES`) — a new theme is one palette dict, and every
  palette is checked for completeness by tests.

## [2.0.0] - 2026-07-02

### Added
- **Multi-currency accounts.** Every account now has its own currency, chosen
  when the account is created (and editable later — editing relabels; amounts
  are never silently converted). Balances and transactions display in the
  account's currency throughout the app.
- **Home-currency conversion everywhere.** The dashboard totals, net-worth
  trend, monthly income/expense charts, reports, budget spending, savings
  summaries and the cash-flow forecast all convert foreign-currency amounts
  into your home currency, so app-wide numbers stay meaningful. Mixed-currency
  totals are marked with ≈.
- **Exchange-rate cache with offline fallback.** Rates come from the same
  keyless providers as the Markets panel (Stooq, Yahoo fallback) and are
  cached in a new `fx_rates` table — both directions. The app refreshes stale
  rates (>24 h) quietly in the background on launch and keeps working offline
  with the last known rate (or 1:1 if a rate was never fetched). A new
  **Settings ▸ Currency** tab shows the cached rates and offers a manual
  refresh.
- **Cross-currency transfers.** Transferring between accounts in different
  currencies asks for the **Received Amount**, pre-estimated from the cached
  rate and editable to match what the bank actually credited. Both legs keep
  their own currency; deleting the transfer reverses both correctly. Recurring
  transfers across currencies convert automatically at the cached rate on
  posting day.
- Transaction exports (CSV/Excel) gain a `currency` column; the PDF report
  labels each transaction with its account currency.

### Changed
- **Why 2.0.0:** the database schema changes meaningfully (per-account
  `currency` column — migration v1.0.9 — plus the new `fx_rates` table), and
  every aggregate number in the app is now defined in terms of the home
  currency. Existing databases upgrade automatically and losslessly: accounts
  inherit their owner's home currency, so all numbers look exactly the same
  until you opt into a foreign-currency account.

## [1.11.0] - 2026-07-01

### Added
- **One-click auto-update (installed build).** When a newer release is found,
  Settings ▸ About now offers **⤓ Update now**: it downloads the installer with
  a progress bar, runs it silently, and closes the app so it upgrades in place
  and relaunches on the new version — no manual download/reinstall. User data in
  `%APPDATA%\BudgetManager` is untouched. Source runs and the portable one-file
  exe keep the plain download link (auto-update is limited to the installed
  build, which can safely replace itself). The installer's relaunch step now
  runs on silent installs (`skipifsilent` removed from `installer.iss`).

## [1.10.0] - 2026-07-01

### Added
- **In-app Activity Log viewer.** The audit trail (previously export-only) now
  has its own **Activity** panel: a read-only, filterable table of every
  create/update/delete, with action and item filters, free-text search, and the
  same CSV export as Settings.
- **"Upcoming Bills" on the Dashboard.** A card lists active recurring items due
  in the next 7 days (overdue items stay visible), so the schedule acts as a
  reminder without opening the Recurring panel.
- **Pause / resume recurring rules.** A rule can be paused (new `is_active`
  flag, migration v1.0.8) so it stops posting — and is excluded from the
  forecast and upcoming-bills — without deleting it or losing its settings. The
  Recurring table shows a **Status** column; a Pause/Resume button toggles it.
- **Copy last month's budgets.** A **Copy Last Month** button on the Budgets
  panel copies the previous month's budget lines into the current month,
  skipping any categories already budgeted.
- **Duplicate a transaction.** A **Duplicate** button opens the Add dialog
  pre-filled from the selected transaction (transfers excluded).

## [1.9.0] - 2026-06-30

### Added
- **End date for recurring transactions.** A recurring item (transaction or
  transfer) can now have an optional end date. In the Add/Edit dialog, tick
  **Ends on** and pick a date; once the schedule's next occurrence falls past
  that date it stops generating transactions automatically. Items with no end
  date keep running indefinitely, exactly as before. The recurring table shows
  an **Ends** column, and the cash-flow forecast respects the end date too. The
  `recurring_transactions` table gains a nullable `end_date` column (migration
  v1.0.7). New tests included.

## [1.8.0] - 2026-06-27

### Added
- **Activity log (audit trail).** Every create, update, and delete the app
  performs — transactions, transfers, accounts, categories, budgets, goals,
  recurring items, watchlist, and profile/settings changes — is recorded in a
  new append-only `audit_log` table with a timestamp and a JSON snapshot.
  Exportable to CSV from **Settings ▸ Backup & Restore ▸ Export Activity Log**.
  Noisy internal side-effects (running-balance updates, market-price refreshes)
  are intentionally not logged, and password hashes are never recorded — only
  that a change occurred. No in-app viewer; export-only. New tests included.

### Fixed
- **Money no longer drifts by fractions of a cent.** Amounts are now rounded to
  whole cents as they're stored, and every account-balance update is pinned with
  SQL `ROUND(..., 2)`. This stops the small (<$1) discrepancies between an
  account's balance and the sum of its transactions, which came from storing
  money as binary floating-point — sub-cent values entering via CSV/Excel import
  or interest deltas, plus tiny accumulation error in the running balance.
  Applies going forward; existing balances re-pin to exact cents on their next
  transaction. Covered by new tests.

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

[Unreleased]: https://github.com/LoloAbdo/budget_app/compare/v2.7.0...HEAD
[2.7.0]: https://github.com/LoloAbdo/budget_app/compare/v2.6.0...v2.7.0
[2.6.0]: https://github.com/LoloAbdo/budget_app/compare/v2.5.0...v2.6.0
[1.4.0]: https://github.com/LoloAbdo/budget_app/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/LoloAbdo/budget_app/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/LoloAbdo/budget_app/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/LoloAbdo/budget_app/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/LoloAbdo/budget_app/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/LoloAbdo/budget_app/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/LoloAbdo/budget_app/releases/tag/v1.0.0
