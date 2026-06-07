# Budget Manager — User Guide

> Track your spending, plan budgets, and reach your financial goals — all in one place.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Navigating the App](#2-navigating-the-app)
3. [Dashboard](#3-dashboard)
4. [Accounts](#4-accounts)
5. [Transactions](#5-transactions)
6. [Budgets](#6-budgets)
7. [Goals](#7-goals)
8. [Recurring Transactions](#8-recurring-transactions)
9. [Reports](#9-reports)
10. [Settings](#10-settings)
11. [Keyboard Shortcuts](#11-keyboard-shortcuts)
12. [Tips & Best Practices](#12-tips--best-practices)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Getting Started

### Installing the app

1. Unzip `budget_manager.zip` to a folder of your choice.
2. Open a terminal in that folder and run:
   ```
   pip install -r requirements.txt
   ```
3. Launch the app:
   ```
   python main.py
   ```

### Try the demo first

If you want to explore the app with sample data already loaded, run:
```
python main.py --seed
```
Then log in with:
- **Email:** `demo@budget.app`
- **Password:** `demo1234`

### Creating your account

1. On the login screen, click **"Don't have an account? Register"**.
2. Fill in your name, email, and a password (at least 6 characters).
3. Choose your currency (defaults to CAD).
4. Click **Register**.
5. You'll see a confirmation — now sign in with your new credentials.

> Your password is encrypted and never stored in plain text.

---

## 2. Navigating the App

Once logged in, you'll see the main window with a **sidebar on the left** and the **content panel on the right**.

```
💰 Budget
  [Your Name]

  🏠  Dashboard
  💳  Transactions
  📊  Budgets
  🎯  Goals
  🏦  Accounts
  📈  Reports
  🔄  Recurring
  ⚙️  Settings

  🚪  Sign Out
```

Click any item in the sidebar to switch views. You can also use the keyboard shortcuts listed in [Section 11](#11-keyboard-shortcuts).

---

## 3. Dashboard

The Dashboard gives you a real-time snapshot of your finances for the current month.

### What you'll see

**Summary cards** across the top row:

| Card | What it shows |
|---|---|
| 💚 Total Income | All income transactions this month |
| 🔴 Total Expenses | All expense transactions this month |
| 💰 Net Balance | Income minus Expenses |
| 📊 Savings Rate | Percentage of income saved |
| 🎯 Goal Progress | Average progress across all active goals |

**Charts:**
- **Pie chart** — Spending breakdown by category
- **Bar chart** — Monthly income vs expenses over the year

**Recent Transactions** — A table of your last 10 transactions.

### Keeping it up to date

The Dashboard refreshes automatically whenever you add, edit, or delete a transaction, budget, or account. You don't need to do anything — it always reflects your latest data.

---

## 4. Accounts

Accounts represent the places you store or owe money — checking accounts, savings, credit cards, and cash.

### Adding an account

1. Go to **Accounts** in the sidebar.
2. Click **+ Add Account**.
3. Enter:
   - **Account Name** — e.g. "Main Checking", "Visa Credit Card"
   - **Account Type** — Checking, Savings, Credit Card, or Cash
   - **Current Balance** — your current balance (use a negative number for credit card debt)
4. Click **Save**.

### Editing an account

Double-click a row in the table, or select it and click **✏ Edit**. You can change the name, type, and balance.

> **Tip:** The balance shown for each account automatically updates every time you add or delete a transaction linked to that account. Only edit the balance directly if you need to correct a discrepancy.

### Deleting an account

Select the account and click **🗑 Delete**. You'll be asked to confirm. Deleting an account also deletes all transactions linked to it.

> **Warning:** This cannot be undone. Consider creating a backup first (see [Section 10](#10-settings)).

---

## 5. Transactions

Transactions are the heart of Budget Manager — every time money comes in or goes out, you record it here.

### Adding a transaction

1. Go to **Transactions**.
2. Click **+ Add Transaction**.
3. Fill in the form:
   - **Date** — when the transaction occurred
   - **Description** — a short label (e.g. "Groceries at IGA")
   - **Amount** — enter a **positive number for income**, a **negative number for expenses** (e.g. `-42.50` for a $42.50 expense)
   - **Category** — choose the most relevant category
   - **Account** — which account this transaction belongs to
   - **Notes** — optional extra details
4. Click **Save**.

> The linked account's balance updates automatically.

### Editing a transaction

Double-click a row, or select it and click **✏ Edit**. All fields can be changed, and the account balance will be corrected automatically.

### Deleting a transaction

Select the row and click **🗑 Delete**. The account balance will be reversed automatically.

### Filtering transactions

Use the toolbar at the top of the Transactions view to narrow down what you see:

| Filter | How to use |
|---|---|
| **Date range** | Set a start and end date |
| **Category** | Pick a category from the dropdown |
| **Account** | Pick an account from the dropdown |
| **Search** | Type a keyword to search descriptions and notes |

Click **Clear** to remove all filters and see every transaction.

---

## 6. Budgets

Budgets let you set a monthly spending limit for each category and see how you're tracking.

### Setting a budget

1. Go to **Budgets**.
2. Use the **month/year picker** at the top to select which month you're budgeting for.
3. For any expense category, click **Set Budget** (or double-click the row).
4. Enter the amount you want to spend in that category.
5. Click **Save**.

You can set budgets for as many or as few categories as you want. Unused categories are simply not tracked.

### Reading the progress bars

Each category shows a colour-coded bar:

| Colour | Meaning |
|---|---|
| 🟢 Green | Under 70% of budget spent — you're on track |
| 🟡 Yellow | 70–90% of budget spent — approaching the limit |
| 🔴 Red | Over 90% spent — at or over budget |

The bar also shows the actual amount spent vs your budget in numbers (e.g. `$320 / $400`).

### Copying a budget to another month

Currently, budgets must be set per month manually. A quick way to repeat last month's budget is to note the amounts and re-enter them for the new month. Future versions will support budget templates.

---

## 7. Goals

Goals help you save towards a specific target — an emergency fund, a holiday, a new car, anything you like.

### Creating a goal

1. Go to **Goals**.
2. Click **+ Add Goal**.
3. Enter:
   - **Goal Name** — e.g. "Emergency Fund"
   - **Target Amount** — how much you want to save
   - **Current Amount** — how much you've saved so far (can be 0)
   - **Target Date** — your deadline
4. Click **Save**.

### Adding money to a goal

1. Select the goal card.
2. Click **💰 Deposit**.
3. Enter the amount you're adding.
4. Click **Save**.

> Note: Goal deposits are tracked separately from your transaction history. They don't affect account balances — think of them as tracking progress, not moving money.

### Editing or deleting a goal

Click **✏ Edit** to change any details, or **🗑 Delete** to remove the goal entirely.

---

## 8. Recurring Transactions

Recurring transactions are bills or income that happen on a regular schedule — rent, salary, subscriptions, loan payments, etc.

### Setting up a recurring transaction

1. Go to **Recurring**.
2. Click **+ Add Recurring**.
3. Fill in:
   - **Name** — e.g. "Netflix Subscription"
   - **Amount** — positive for income, negative for an expense
   - **Frequency** — Weekly, Bi-weekly, Monthly, Quarterly, or Yearly
   - **Next Due Date** — the next time this should be posted
   - **Category** and **Account** (optional but recommended)
4. Click **Save**.

### How recurring transactions work

Every time you start the app, Budget Manager checks all your recurring rules. Any transaction whose due date is today or in the past is **automatically posted** to your transaction history, and the next due date is advanced by the frequency you set.

For example, if you set up "Netflix — $18.00 — Monthly — due 2026-06-05", when you open the app on June 5th (or later), a transaction for −$18.00 will be added automatically.

### Overdue transactions

Rows highlighted in **red** in the Recurring view are ones whose due date has already passed. They'll be posted the next time you open the app.

### Editing or deleting a recurring rule

Select the row and click **✏ Edit** or **🗑 Delete**. Deleting a rule does not delete transactions that were already posted.

---

## 9. Reports

Reports give you a deeper look at your finances over time.

### Choosing a time period

Use the **month/year pickers** at the top of the Reports view to select the period you want to analyse.

### The three report tabs

**Summary tab**
A table with totals for the selected month: total income, total expenses, net balance, and savings rate. Includes a pie chart of spending by category.

**Categories tab**
A breakdown of spending per expense category — how much you spent, what percentage of total spending it represents, and how it compares to your budget (if you set one).

**Cash Flow tab**
A bar chart showing income vs expenses for each month of the selected year, giving you a picture of seasonal trends.

### Exporting reports

Three export options are available:

| Button | Output |
|---|---|
| **Export PDF** | A formatted PDF report for the selected month, saved to a location you choose |
| **Export CSV** | A spreadsheet-friendly CSV of all your transactions |
| **Export Excel** | An Excel workbook with separate sheets for Transactions, Budgets, and Accounts |

---

## 10. Settings

### Switching themes

At the top of Settings, toggle between **Dark** and **Light** mode. The change applies instantly to the whole application.

### Managing categories

The Categories section lets you customise the categories used for transactions and budgets.

- **+ Add Category** — create a new income or expense category, pick a name and colour
- **✏ Edit** — rename a category or change its colour
- **🗑 Delete** — remove a category (transactions using it will lose their category link)

> The 19 default categories (Groceries, Rent, Salary, etc.) cover most common needs. You only need to add custom ones if your situation calls for it.

### Backups

Budget Manager automatically saves a backup of your database **every 24 hours** while the app is running. You can also create or restore backups manually:

- **Create Backup** — saves a timestamped copy of your database to the `backups/` folder
- **Restore** — select a backup from the list and restore it; your current data will be replaced

> It's a good idea to create a manual backup before importing data or making large changes.

### Importing data

To import transactions from another app or spreadsheet:

1. Export your data as CSV or Excel from the other application.
2. Make sure your file has columns named: `date`, `amount`, `description`, `category`, `account`.
3. In Settings, click **Import CSV** or **Import Excel**.
4. Select your file.
5. Budget Manager will import valid rows and report how many were imported and how many were skipped.

---

## 11. Keyboard Shortcuts

| Keys | Action |
|---|---|
| `Ctrl + 1` | Go to Dashboard |
| `Ctrl + 2` | Go to Transactions |
| `Ctrl + 3` | Go to Budgets |
| `Ctrl + 4` | Go to Goals |
| `Ctrl + 5` | Go to Accounts |
| `Ctrl + 6` | Go to Reports |
| `Ctrl + 7` | Go to Recurring |
| `Ctrl + 8` | Go to Settings |

---

## 12. Tips & Best Practices

**Set up your accounts first.** Before recording any transactions, add all your accounts (checking, savings, credit cards) with their current balances. This gives you an accurate starting point.

**Use negative amounts for expenses.** The app uses sign to distinguish income from spending — positive = money in, negative = money out. So groceries worth $65 should be entered as `-65.00`.

**Categorise everything.** Even if a category is just "Miscellaneous", categorising every transaction makes your pie charts and category reports meaningful.

**Set budgets at the start of each month.** Five minutes on the first of the month to set your category budgets will make the progress bars useful all month long.

**Use recurring for regular bills.** Setting up rent, subscriptions, and salary as recurring rules means they'll be posted automatically — you only need to manually add irregular one-off purchases.

**Export before major changes.** Before importing data or deleting old transactions, use **Export Excel** from the Reports view to keep a complete backup in a format you can open in any spreadsheet app.

**Back up regularly.** The auto-backup runs every 24 hours the app is open, but creating a manual backup from Settings before any big change is a good habit.

---

## 13. Troubleshooting

### I clicked "Save" in the Add Account dialog but nothing happened

This was a bug in v1.0.0. It has been fixed in v1.0.1 — the app will now show an error message if saving fails for any reason. Please download and replace your copy with the updated version.

If you're on v1.0.1 and the problem persists, the error message will tell you what went wrong (e.g. a database lock or a duplicate name).

### The app shows a warning about "setHighDpiScaleFactorRoundingPolicy"

This was a startup warning in v1.0.0 and is fixed in v1.0.1. It was harmless and didn't affect functionality.

### I ran `--seed` but get an error about a duplicate email

The demo account `demo@budget.app` already exists in your database. Run:
```
python main.py --reset --seed
```
`--reset` deletes the existing database first, then `--seed` creates fresh demo data.

### Charts aren't showing up on the Dashboard

Make sure `matplotlib` is installed:
```
pip install matplotlib
```
If you're running on a headless server, Matplotlib needs a display. Set the environment variable `MPLBACKEND=Agg` before launching (charts won't be interactive but will still render).

### I deleted a transaction but my account balance looks wrong

Try editing the account (Accounts → Edit) and manually correcting the balance. If this keeps happening, it may be a sign that some transactions were imported or created with inconsistent amounts — exporting to CSV and reviewing the data can help identify the issue.

### I forgot my password

Password recovery isn't built into v1.0.0. If you know your database file location (`data/budget.db`), you can:
1. Make a backup of the database file.
2. Run `python main.py --reset` to start fresh.
3. Register a new account.

If you have important data you don't want to lose, please reach out for manual database assistance.

### The app is slow when I have many transactions

The database is optimised for personal-finance scale (thousands of transactions). If you experience slowness, try filtering the Transactions view to a narrower date range rather than loading all records at once.
