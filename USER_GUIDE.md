# Budget Manager — User Guide

> **Version 1.2.0** · Track your spending, plan budgets, watch your investments, and reach your financial goals — all in one place.
>
> 🇬🇧 **English** below · 🇫🇷 **Version française** [plus bas](#-guide-de-lutilisateur-français)

---

# 🇬🇧 User Guide (English)

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
10. [Savings & Interest](#10-savings--interest)
11. [Markets](#11-markets)
12. [Settings](#12-settings)
13. [Keyboard Shortcuts](#13-keyboard-shortcuts)
14. [Tips & Best Practices](#14-tips--best-practices)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Getting Started

### Installing the app

There are two ways to use Budget Manager on Windows:

**Option A — Installer (recommended for most people)**
1. Download `BudgetManagerSetup.exe` from the [Releases page](https://github.com/LoloAbdo/budget_app/releases/latest).
2. Run it and follow the prompts. The app installs like any normal Windows program and adds a Start-menu shortcut.

**Option B — Portable**
1. Download `BudgetManager.exe` from the [Releases page](https://github.com/LoloAbdo/budget_app/releases/latest).
2. Double-click it — no installation needed.

> **Where your data lives:** the installed/portable app keeps your database and backups in `%APPDATA%\BudgetManager`. (Running from source code instead uses a local `./data` folder — see the Technical Documentation.)

**Option C — Run from source (for developers)**
```
pip install -r requirements.txt
python main.py
```

### Try the demo first

To explore the app with realistic sample data already loaded, run from source with:
```
python main.py --seed
```
Then log in with:
- **Email:** `demo@budget.app`
- **Password:** `demo1234`

### Creating your account

1. On the login screen, switch to the **Register** panel.
2. Fill in your name, email, and a password (at least 6 characters).
3. Choose your currency (defaults to CAD). This is the currency used everywhere in the app, including Markets conversion.
4. Click **Register**, then sign in with your new credentials.

> Your password is encrypted with bcrypt and never stored in plain text.

---

## 2. Navigating the App

After logging in you'll see a **sidebar on the left** and the **content panel on the right**:

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
  🐷  Savings
  💹  Markets
  ⚙️  Settings
```

Click any item to switch views, or use the [keyboard shortcuts](#13-keyboard-shortcuts).

---

## 3. Dashboard

The Dashboard is your real-time financial snapshot for the current month.

**Summary cards** across the top:

| Card | What it shows |
|---|---|
| Total Balance | Sum of all your account balances right now |
| Monthly Income | All income this month |
| Monthly Expenses | All expenses this month |
| Net Savings | Income minus expenses this month |
| Savings Rate | Percentage of this month's income saved |

**Charts:**
- **Spending by Category** — a donut chart of where your money went this month.
- **Income vs Expenses — Monthly** — bars for each month of the current year.
- **Net Worth — Last 12 Months** *(new in 1.2.0)* — a line chart of your total net worth over the past year, so you can see whether you're trending up or down at a glance.

**Recent Transactions** — your last 10 entries.

The Dashboard refreshes automatically whenever you change a transaction, budget, or account.

---

## 4. Accounts

Accounts represent where you store or owe money — checking, savings, credit cards, and cash.

### Adding an account
1. Go to **Accounts** → **+ Add Account**.
2. Enter the **name**, **type** (Checking, Savings, Credit Card, Cash), and **current balance** (use a negative number for credit-card debt).
3. Click **Save**.

### Editing / deleting
Double-click a row (or select it and click **Edit**) to change details. Deleting an account also deletes all of its transactions.

> **Tip:** account balances update automatically as you add and remove transactions. Only edit a balance directly to correct a discrepancy — and for **Savings** accounts, doing so triggers interest tracking (see [Section 10](#10-savings--interest)).

> **Warning:** deleting is permanent. Create a backup first if unsure.

---

## 5. Transactions

Every time money moves, you record it here.

### Adding a transaction
1. Go to **Transactions** → **+ Add Transaction**.
2. Fill in **Date**, **Description**, **Amount** (positive = income, negative = expense, e.g. `-42.50`), **Category**, **Account**, and optional **Notes**.
3. Click **Save**. The account balance updates automatically.

### Transfers between accounts
Use a transfer when you move money between your own accounts (e.g. checking → savings). A transfer creates two linked entries — money out of one account and into the other — and is excluded from income/expense totals so it doesn't distort your reports.

### Editing / deleting
Editing corrects the account balance automatically; deleting reverses it.

### Filtering
The toolbar lets you filter by **date range**, **category**, **account**, and **search keyword** (matches description and notes). Click **Clear** to reset.

---

## 6. Budgets

Set a monthly spending limit per category and track it.

1. Go to **Budgets** and pick the **month/year**.
2. For any expense category, click **Set Budget** and enter an amount.

**Reading the bars:**

| Colour | Meaning |
|---|---|
| 🟢 Green | Under 70% spent — on track |
| 🟡 Yellow | 70–90% spent — approaching the limit |
| 🔴 Red | Over 90% — at or over budget |

Each bar also shows spent vs budgeted in numbers (e.g. `$320 / $400`). Budgets are per-month; re-setting the same category/month overwrites the amount.

---

## 7. Goals

Goals help you save toward a target — an emergency fund, a holiday, a new laptop.

1. **Goals** → **+ Add Goal**: enter **name**, **target amount**, **current amount**, and **target date**.
2. Use **Deposit** to add progress toward a goal.

> Goal progress is tracked separately from your accounts — it measures progress, it doesn't move real money.

---

## 8. Recurring Transactions

Recurring rules are bills or income on a schedule — rent, salary, subscriptions.

1. **Recurring** → **+ Add Recurring**: enter **name**, **amount** (signed), **frequency** (Weekly, Bi-weekly, Monthly, Quarterly, Yearly), **next due date**, and optionally a **category** and **account**.
2. Recurring **transfers** between accounts are also supported.
3. To make a rule stop on its own, tick **Ends on** and pick an **end date**. Once the next occurrence would fall after that date, the rule stops posting. Leave it unticked to run indefinitely. The **Ends** column shows each rule's end date.

**How it works:** every time you open the app, any rule whose due date is today or earlier is posted automatically, and its next due date advances. Missed periods are all caught up at once. Overdue rules appear highlighted in red. A rule with an end date stops once its schedule passes that date.

Deleting a rule does not remove transactions it already posted.

---

## 9. Reports

Deeper analysis over time. Pick a **month/year** at the top.

- **Summary** — totals for the month (income, expenses, net, savings rate) plus a category pie chart.
- **Categories** — spending per category, its share of the total, and budget comparison.
- **Cash Flow** — income vs expenses for each month of the year.

**Exports:**

| Button | Output |
|---|---|
| Export PDF | Formatted monthly report |
| Export CSV | All transactions, spreadsheet-friendly |
| Export Excel | Workbook with Transactions, Budgets, and Accounts sheets |

---

## 10. Savings & Interest

The **Savings** tab groups all of your **Savings**-type accounts and tracks the interest/gains they earn.

**How interest is detected:** when you edit a Savings account's balance, the app compares the new balance to what your recorded transactions would predict. Any unexplained difference is recorded as a signed **Interest** entry (a gain is positive, a loss negative). A checkbox lets you opt out for any individual edit (e.g. when you're just correcting a typo rather than recording real interest).

The tab shows:
- Cards for **Total Savings** and interest earned **this month / this year / all-time**.
- A chart of **interest earned over time**.
- A history table of recent interest activity per account.

---

## 11. Markets

Track a watchlist of **stocks and crypto**, converted into your account currency.

1. **Markets** → **+ Add Symbol**: choose **Stock** or **Crypto** and enter a ticker (e.g. `AAPL`, `BTC`).
2. Prices come from **keyless** public sources (CoinGecko for crypto; Stooq/Yahoo for stocks) — no API key or sign-up needed.

**Refreshing:**
- **Auto-refresh defaults to Off (manual)** to avoid unnecessary network calls — click **Refresh** when you want fresh prices.
- You can switch auto-refresh to a fixed interval (e.g. every few minutes) from the dropdown.

Prices and daily change are converted to your currency. Stock requests are batched into a single call for speed.

---

## 12. Settings

Settings has five tabs:

**Appearance**
- **Theme** — switch between Dark and Light instantly.
- **Language** — English or French. Pick a language and click **Apply Language**; the entire interface re-localizes.

**Categories**
- Add, edit, or delete income/expense categories (name + colour). The defaults cover most needs; deleting a category unlinks it from existing transactions.

**Backup & Restore**
- The app auto-saves a backup every 24 hours while running (keeping the 30 most recent).
- **Create Backup** saves a timestamped copy now; **Restore** replaces your current data with a selected backup.

**Import Data**
- Import transactions from CSV or Excel. Your file should have columns: `date`, `amount`, `description`, `category`, `account`. Valid rows are imported and a summary reports how many were imported vs skipped.

**About**
- Shows the app version and lets you check for updates. The update check is **notify-only**: it compares your version to the latest GitHub release and links the download — it never installs anything automatically.

---

## 13. Keyboard Shortcuts

| Keys | Action | Keys | Action |
|---|---|---|---|
| `Ctrl + 1` | Dashboard | `Ctrl + 6` | Reports |
| `Ctrl + 2` | Transactions | `Ctrl + 7` | Recurring |
| `Ctrl + 3` | Budgets | `Ctrl + 8` | Savings |
| `Ctrl + 4` | Goals | `Ctrl + 9` | Markets |
| `Ctrl + 5` | Accounts | `Ctrl + 0` | Settings |

---

## 14. Tips & Best Practices

- **Set up accounts first** with accurate starting balances before recording transactions.
- **Use signed amounts** — positive for income, negative for expenses.
- **Use transfers** (not two separate transactions) when moving money between your accounts, so reports stay accurate.
- **Categorise everything**, even as "Miscellaneous", to make charts meaningful.
- **Set budgets on the 1st** of each month.
- **Automate regular bills** with recurring rules.
- **Refresh Markets manually** unless you specifically want live updates.
- **Back up before big changes** (imports, bulk deletes), and keep an Excel export as an extra safety net.

---

## 15. Troubleshooting

**The "check for updates" says I'm up to date, but I expected a new version.**
The update check compares your installed version to the **latest published GitHub Release**. If a new version's release hasn't finished publishing yet, you'll be told you're current — wait a few minutes and check again.

**I ran `--seed` and it said "Demo data already present".**
That's expected — seeding is idempotent and won't duplicate data. To start fresh:
```
python main.py --reset    (deletes the database)
python main.py --seed     (re-seeds clean demo data)
```

**Charts aren't showing on the Dashboard (running from source).**
Ensure dependencies are installed: `pip install -r requirements.txt`.

**Market prices won't load.**
Markets needs an internet connection and reaches public price sources. If a symbol shows no price, double-check the ticker, then click **Refresh**. Occasional source hiccups resolve on the next refresh.

**My account balance looks wrong.**
Edit the account and correct the balance. For a **Savings** account, untick the interest checkbox if the change isn't real interest. Reviewing an Excel/CSV export helps spot inconsistent entries.

**I forgot my password.**
There's no automated recovery. Back up `%APPDATA%\BudgetManager\data\budget.db`, then register a new account (or run `--reset` from source for a clean start).

**The app feels slow with lots of data.**
Version 1.1.0+ added database indexes that keep the transaction list fast at personal-finance scale. If you still notice lag, filter the Transactions view to a narrower date range.

---
---

# 🇫🇷 Guide de l'utilisateur (Français)

> **Version 1.2.0** · Suivez vos dépenses, planifiez vos budgets, surveillez vos placements et atteignez vos objectifs financiers — le tout au même endroit.

## Table des matières

1. [Premiers pas](#1-premiers-pas)
2. [Naviguer dans l'application](#2-naviguer-dans-lapplication)
3. [Tableau de bord](#3-tableau-de-bord)
4. [Comptes](#4-comptes)
5. [Transactions](#5-transactions-fr)
6. [Budgets](#6-budgets-fr)
7. [Objectifs](#7-objectifs)
8. [Transactions récurrentes](#8-transactions-récurrentes)
9. [Rapports](#9-rapports)
10. [Épargne et intérêts](#10-épargne-et-intérêts)
11. [Marchés](#11-marchés)
12. [Paramètres](#12-paramètres)
13. [Raccourcis clavier](#13-raccourcis-clavier)
14. [Conseils et bonnes pratiques](#14-conseils-et-bonnes-pratiques)
15. [Dépannage](#15-dépannage)

---

## 1. Premiers pas

### Installer l'application

Deux façons d'utiliser Budget Manager sous Windows :

**Option A — Programme d'installation (recommandé)**
1. Téléchargez `BudgetManagerSetup.exe` depuis la [page des versions](https://github.com/LoloAbdo/budget_app/releases/latest).
2. Lancez-le et suivez les instructions. L'application s'installe comme un logiciel Windows classique et ajoute un raccourci au menu Démarrer.

**Option B — Version portable**
1. Téléchargez `BudgetManager.exe` depuis la [page des versions](https://github.com/LoloAbdo/budget_app/releases/latest).
2. Double-cliquez dessus — aucune installation requise.

> **Où sont vos données :** l'application (installée ou portable) conserve sa base de données et ses sauvegardes dans `%APPDATA%\BudgetManager`. (L'exécution depuis le code source utilise plutôt un dossier local `./data` — voir la documentation technique.)

**Option C — Exécuter depuis le code source (développeurs)**
```
pip install -r requirements.txt
python main.py
```

### Essayer la démo d'abord

Pour explorer l'application avec des données d'exemple réalistes, exécutez depuis le code source :
```
python main.py --seed
```
Puis connectez-vous avec :
- **Courriel :** `demo@budget.app`
- **Mot de passe :** `demo1234`

### Créer votre compte

1. Sur l'écran de connexion, passez au panneau **Inscription**.
2. Saisissez votre nom, votre courriel et un mot de passe (au moins 6 caractères).
3. Choisissez votre devise (CAD par défaut). Cette devise est utilisée partout, y compris pour la conversion dans Marchés.
4. Cliquez sur **S'inscrire**, puis connectez-vous.

> Votre mot de passe est chiffré avec bcrypt et n'est jamais stocké en clair.

---

## 2. Naviguer dans l'application

Après connexion, une **barre latérale à gauche** et le **panneau de contenu à droite** s'affichent :

```
💰 Budget
  [Votre nom]

  🏠  Tableau de bord
  💳  Transactions
  📊  Budgets
  🎯  Objectifs
  🏦  Comptes
  📈  Rapports
  🔄  Récurrent
  🐷  Épargne
  💹  Marchés
  ⚙️  Paramètres
```

Cliquez sur un élément pour changer de vue, ou utilisez les [raccourcis clavier](#13-raccourcis-clavier).

---

## 3. Tableau de bord

Le tableau de bord est votre aperçu financier en temps réel pour le mois en cours.

**Cartes de synthèse** en haut :

| Carte | Ce qu'elle affiche |
|---|---|
| Solde total | Somme de tous vos soldes de comptes actuels |
| Revenus du mois | Tous les revenus du mois |
| Dépenses du mois | Toutes les dépenses du mois |
| Épargne nette | Revenus moins dépenses du mois |
| Taux d'épargne | Pourcentage des revenus du mois épargné |

**Graphiques :**
- **Dépenses par catégorie** — un graphique en anneau de la répartition du mois.
- **Revenus vs Dépenses — Mensuel** — des barres pour chaque mois de l'année.
- **Valeur nette — 12 derniers mois** *(nouveau dans la 1.2.0)* — une courbe de votre valeur nette totale sur l'année écoulée, pour voir d'un coup d'œil la tendance.

**Transactions récentes** — vos 10 dernières entrées.

Le tableau de bord se met à jour automatiquement à chaque modification d'une transaction, d'un budget ou d'un compte.

---

## 4. Comptes

Les comptes représentent où vous gardez ou devez de l'argent — chèque, épargne, cartes de crédit, espèces.

### Ajouter un compte
1. **Comptes** → **+ Ajouter un compte**.
2. Saisissez le **nom**, le **type** (Chèque, Épargne, Carte de crédit, Espèces) et le **solde actuel** (un nombre négatif pour une dette de carte de crédit).
3. Cliquez sur **Enregistrer**.

### Modifier / supprimer
Double-cliquez une ligne (ou sélectionnez-la puis **Modifier**) pour changer les détails. Supprimer un compte supprime aussi toutes ses transactions.

> **Astuce :** les soldes se mettent à jour automatiquement avec vos transactions. Ne modifiez un solde directement que pour corriger un écart — et pour les comptes **Épargne**, cela déclenche le suivi des intérêts (voir [Section 10](#10-épargne-et-intérêts)).

> **Attention :** la suppression est définitive. Créez une sauvegarde en cas de doute.

---

## 5. Transactions {#5-transactions-fr}

Chaque mouvement d'argent se note ici.

### Ajouter une transaction
1. **Transactions** → **+ Ajouter une transaction**.
2. Remplissez **Date**, **Description**, **Montant** (positif = revenu, négatif = dépense, ex. `-42,50`), **Catégorie**, **Compte** et **Notes** facultatives.
3. Cliquez sur **Enregistrer**. Le solde du compte se met à jour automatiquement.

### Virements entre comptes
Utilisez un virement lorsque vous déplacez de l'argent entre vos propres comptes (ex. chèque → épargne). Un virement crée deux entrées liées — une sortie d'un compte et une entrée dans l'autre — et est exclu des totaux de revenus/dépenses pour ne pas fausser vos rapports.

### Modifier / supprimer
La modification corrige automatiquement le solde ; la suppression l'annule.

### Filtrer
La barre d'outils permet de filtrer par **plage de dates**, **catégorie**, **compte** et **mot-clé** (recherche dans la description et les notes). Cliquez sur **Effacer** pour réinitialiser.

---

## 6. Budgets {#6-budgets-fr}

Fixez une limite de dépense mensuelle par catégorie et suivez-la.

1. **Budgets**, puis choisissez le **mois/année**.
2. Pour une catégorie de dépense, cliquez sur **Définir le budget** et saisissez un montant.

**Lire les barres :**

| Couleur | Signification |
|---|---|
| 🟢 Vert | Moins de 70 % dépensé — sur la bonne voie |
| 🟡 Jaune | 70–90 % dépensé — proche de la limite |
| 🔴 Rouge | Plus de 90 % — à la limite ou dépassé |

Chaque barre affiche aussi le montant dépensé vs budgété (ex. `320 $ / 400 $`). Les budgets sont mensuels ; redéfinir la même catégorie/le même mois remplace le montant.

---

## 7. Objectifs

Les objectifs vous aident à épargner pour un but — fonds d'urgence, vacances, nouvel ordinateur.

1. **Objectifs** → **+ Ajouter un objectif** : saisissez **nom**, **montant cible**, **montant actuel** et **date cible**.
2. Utilisez **Dépôt** pour faire progresser un objectif.

> La progression des objectifs est suivie séparément de vos comptes — elle mesure l'avancement, sans déplacer d'argent réel.

---

## 8. Transactions récurrentes

Les règles récurrentes sont des factures ou revenus planifiés — loyer, salaire, abonnements.

1. **Récurrent** → **+ Ajouter** : saisissez **nom**, **montant** (signé), **fréquence** (Hebdomadaire, Aux deux semaines, Mensuel, Trimestriel, Annuel), **prochaine échéance**, et éventuellement une **catégorie** et un **compte**.
2. Les **virements** récurrents entre comptes sont aussi pris en charge.
3. Pour qu'une règle s'arrête d'elle-même, cochez **Se termine le** et choisissez une **date de fin**. Dès que la prochaine occurrence dépasserait cette date, la règle cesse de publier. Laissez la case décochée pour qu'elle continue indéfiniment. La colonne **Fin** affiche la date de fin de chaque règle.

**Fonctionnement :** à chaque ouverture de l'application, toute règle dont l'échéance est aujourd'hui ou passée est publiée automatiquement, et sa prochaine échéance avance. Les périodes manquées sont toutes rattrapées d'un coup. Les règles en retard apparaissent en rouge. Une règle avec une date de fin s'arrête dès que son échéancier dépasse cette date.

Supprimer une règle ne supprime pas les transactions déjà publiées.

---

## 9. Rapports

Analyse approfondie dans le temps. Choisissez un **mois/année** en haut.

- **Synthèse** — totaux du mois (revenus, dépenses, net, taux d'épargne) avec un graphique en camembert par catégorie.
- **Catégories** — dépenses par catégorie, leur part du total et comparaison au budget.
- **Flux de trésorerie** — revenus vs dépenses pour chaque mois de l'année.

**Exports :**

| Bouton | Résultat |
|---|---|
| Exporter PDF | Rapport mensuel mis en forme |
| Exporter CSV | Toutes les transactions, compatible tableur |
| Exporter Excel | Classeur avec feuilles Transactions, Budgets et Comptes |

---

## 10. Épargne et intérêts

L'onglet **Épargne** regroupe tous vos comptes de type **Épargne** et suit les intérêts/gains qu'ils génèrent.

**Détection des intérêts :** lorsque vous modifiez le solde d'un compte d'épargne, l'application compare le nouveau solde à ce que vos transactions enregistrées prévoient. Toute différence inexpliquée est enregistrée comme une entrée **Intérêt** signée (un gain est positif, une perte négative). Une case à cocher permet de désactiver ce comportement pour une modification donnée (par exemple, une simple correction).

L'onglet affiche :
- Des cartes pour l'**épargne totale** et les intérêts gagnés **ce mois / cette année / depuis toujours**.
- Un graphique des **intérêts gagnés dans le temps**.
- Un historique des activités d'intérêt récentes par compte.

---

## 11. Marchés

Suivez une liste d'**actions et de cryptomonnaies**, converties dans la devise de votre compte.

1. **Marchés** → **+ Ajouter un symbole** : choisissez **Action** ou **Crypto** et saisissez un symbole (ex. `AAPL`, `BTC`).
2. Les cours proviennent de sources publiques **sans clé** (CoinGecko pour la crypto ; Stooq/Yahoo pour les actions) — aucune clé API ni inscription nécessaire.

**Actualisation :**
- L'**actualisation automatique est désactivée par défaut (manuelle)** pour éviter les appels réseau inutiles — cliquez sur **Actualiser** au besoin.
- Vous pouvez activer un intervalle fixe (ex. toutes les quelques minutes) dans le menu déroulant.

Les cours et la variation quotidienne sont convertis dans votre devise. Les requêtes d'actions sont regroupées en un seul appel pour plus de rapidité.

---

## 12. Paramètres

Les paramètres comportent cinq onglets :

**Apparence**
- **Thème** — basculez instantanément entre sombre et clair.
- **Langue** — anglais ou français. Choisissez une langue puis cliquez sur **Appliquer la langue** ; toute l'interface est traduite.

**Catégories**
- Ajoutez, modifiez ou supprimez des catégories de revenus/dépenses (nom + couleur). Les valeurs par défaut couvrent l'essentiel ; supprimer une catégorie la dissocie des transactions existantes.

**Sauvegarde et restauration**
- L'application enregistre automatiquement une sauvegarde toutes les 24 heures pendant son exécution (en conservant les 30 plus récentes).
- **Créer une sauvegarde** enregistre une copie horodatée ; **Restaurer** remplace vos données actuelles par une sauvegarde choisie.

**Importer des données**
- Importez des transactions depuis CSV ou Excel. Votre fichier doit comporter les colonnes : `date`, `amount`, `description`, `category`, `account`. Les lignes valides sont importées et un résumé indique combien ont été importées vs ignorées.

**À propos**
- Affiche la version de l'application et permet de vérifier les mises à jour. La vérification est **informative seulement** : elle compare votre version à la dernière version GitHub et propose le téléchargement — elle n'installe jamais rien automatiquement.

---

## 13. Raccourcis clavier

| Touches | Action | Touches | Action |
|---|---|---|---|
| `Ctrl + 1` | Tableau de bord | `Ctrl + 6` | Rapports |
| `Ctrl + 2` | Transactions | `Ctrl + 7` | Récurrent |
| `Ctrl + 3` | Budgets | `Ctrl + 8` | Épargne |
| `Ctrl + 4` | Objectifs | `Ctrl + 9` | Marchés |
| `Ctrl + 5` | Comptes | `Ctrl + 0` | Paramètres |

---

## 14. Conseils et bonnes pratiques

- **Configurez d'abord vos comptes** avec des soldes de départ exacts avant d'enregistrer des transactions.
- **Utilisez des montants signés** — positif pour les revenus, négatif pour les dépenses.
- **Utilisez les virements** (et non deux transactions séparées) pour déplacer de l'argent entre vos comptes, afin que les rapports restent exacts.
- **Catégorisez tout**, même en « Divers », pour des graphiques utiles.
- **Définissez vos budgets le 1er** de chaque mois.
- **Automatisez les factures régulières** avec des règles récurrentes.
- **Actualisez Marchés manuellement** sauf si vous voulez des mises à jour en direct.
- **Sauvegardez avant les grands changements** (imports, suppressions en masse), et gardez un export Excel comme filet de sécurité.

---

## 15. Dépannage

**La vérification des mises à jour dit que je suis à jour, mais j'attendais une nouvelle version.**
La vérification compare votre version installée à la **dernière version GitHub publiée**. Si la publication d'une nouvelle version n'est pas terminée, vous serez informé que vous êtes à jour — attendez quelques minutes et réessayez.

**J'ai lancé `--seed` et il a indiqué « Demo data already present ».**
C'est normal — le seeding est idempotent et ne duplique pas les données. Pour repartir à neuf :
```
python main.py --reset    (supprime la base de données)
python main.py --seed     (recrée des données démo propres)
```

**Les graphiques ne s'affichent pas sur le tableau de bord (exécution depuis le source).**
Assurez-vous que les dépendances sont installées : `pip install -r requirements.txt`.

**Les cours des marchés ne se chargent pas.**
Marchés nécessite une connexion Internet et interroge des sources publiques. Si un symbole n'affiche aucun cours, vérifiez le symbole puis cliquez sur **Actualiser**. Les ratés occasionnels se règlent à l'actualisation suivante.

**Mon solde de compte semble incorrect.**
Modifiez le compte et corrigez le solde. Pour un compte **Épargne**, décochez la case d'intérêt si le changement n'est pas un intérêt réel. Examiner un export Excel/CSV aide à repérer les entrées incohérentes.

**J'ai oublié mon mot de passe.**
Aucune récupération automatique n'existe. Sauvegardez `%APPDATA%\BudgetManager\data\budget.db`, puis créez un nouveau compte (ou exécutez `--reset` depuis le source pour repartir à neuf).

**L'application est lente avec beaucoup de données.**
La version 1.1.0+ a ajouté des index de base de données qui maintiennent la liste des transactions rapide à l'échelle des finances personnelles. Si vous constatez encore des ralentissements, filtrez la vue Transactions sur une plage de dates plus étroite.
