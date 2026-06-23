"""
views/i18n.py
Lightweight in-app translation layer for Budget Manager.

Usage:
    from views.i18n import tr, set_language, get_language

    label = QLabel(tr("Settings"))
    msg   = tr("{n} transactions").format(n=count)

Design notes
------------
* English source text is used as the lookup key (gettext-style). This keeps the
  call sites readable and means English needs no translation table — any key
  that is missing from the active language's table falls back to the key itself.
* Only static UI chrome and the fixed enum values (Income/Expense, account
  types, frequencies, month names, …) are translated. User-entered data
  (custom category names, descriptions, notes) is never translated, and the
  values written to the database stay in English so the data is identical
  regardless of the selected language.
"""

from __future__ import annotations

# ── Supported languages ──────────────────────────────────────────────────────

LANGUAGES = {
    "en": "English",
    "fr": "Français",
}

DEFAULT_LANGUAGE = "en"

_current_language = DEFAULT_LANGUAGE


# ── French translation table ─────────────────────────────────────────────────
# Key   = exact English source string passed to tr()
# Value = French rendering
#
# Templates keep their {placeholders}; the caller interpolates after tr().

_FR: dict[str, str] = {
    # ── Navigation / shell ────────────────────────────────────────────────
    "Dashboard": "Tableau de bord",
    "Transactions": "Transactions",
    "Budgets": "Budgets",
    "Goals": "Objectifs",
    "Accounts": "Comptes",
    "Reports": "Rapports",
    "Forecast": "Prévisions",
    "Recurring": "Récurrents",
    "Settings": "Paramètres",
    "💰 Budget": "💰 Budget",
    "Sign Out": "Déconnexion",
    "Budget Manager": "Gestionnaire de budget",
    "Sign out of Budget Manager?": "Se déconnecter du Gestionnaire de budget ?",
    "✓ Posted {n} recurring transaction(s)": "✓ {n} transaction(s) récurrente(s) enregistrée(s)",

    # ── Common buttons / words ────────────────────────────────────────────
    "Save": "Enregistrer",
    "Cancel": "Annuler",
    "Edit": "Modifier",
    "Delete": "Supprimer",
    "Clear": "Effacer",
    "Type": "Type",
    "Name": "Nom",
    "Color": "Couleur",
    "Amount": "Montant",
    "Date": "Date",
    "Description": "Description",
    "Category": "Catégorie",
    "Account": "Compte",
    "Notes": "Notes",
    "Validation": "Validation",
    "Error": "Erreur",
    "Success": "Succès",
    "Yes": "Oui",
    "No": "Non",

    # ── Enum / data display values (stored English, shown localized) ───────
    "Income": "Revenu",
    "Expense": "Dépense",
    "Checking": "Compte courant",
    "Savings": "Épargne",
    "Credit Card": "Carte de crédit",
    "Cash": "Espèces",
    "Weekly": "Hebdomadaire",
    "Bi-weekly": "Aux deux semaines",
    "Monthly": "Mensuel",
    "Quarterly": "Trimestriel",
    "Yearly": "Annuel",
    "Transfer": "Virement",
    "Transaction": "Transaction",
    "— None —": "— Aucune —",
    "[Transfer]": "[Virement]",

    # ── Month names ───────────────────────────────────────────────────────
    "January": "Janvier",
    "February": "Février",
    "March": "Mars",
    "April": "Avril",
    "May": "Mai",
    "June": "Juin",
    "July": "Juillet",
    "August": "Août",
    "September": "Septembre",
    "October": "Octobre",
    "November": "Novembre",
    "December": "Décembre",

    # ── Login / Register ──────────────────────────────────────────────────
    "Budget Manager — Sign In": "Gestionnaire de budget — Connexion",
    "💰 Budget Manager": "💰 Gestionnaire de budget",
    "Personal Finance, Simplified": "La finance personnelle, simplifiée",
    "Email": "Courriel",
    "Password": "Mot de passe",
    "Sign In": "Se connecter",
    "Show password": "Afficher le mot de passe",
    "Hide password": "Masquer le mot de passe",
    "Full Name": "Nom complet",
    "Currency": "Devise",
    "Create Account": "Créer un compte",
    "Don't have an account? Register": "Pas de compte ? S'inscrire",
    "Already have an account? Sign In": "Vous avez déjà un compte ? Se connecter",
    "Login Failed": "Échec de la connexion",
    "Registration Failed": "Échec de l'inscription",
    "You can now sign in.": "Vous pouvez maintenant vous connecter.",

    # ── Dashboard ─────────────────────────────────────────────────────────
    "Good morning": "Bonjour",
    "Good afternoon": "Bon après-midi",
    "Good evening": "Bonsoir",
    "{greeting}, {name}!": "{greeting}, {name} !",
    "{date}  •  {month} Overview": "{date}  •  Aperçu de {month}",
    "Total Balance": "Solde total",
    "Monthly Income": "Revenu mensuel",
    "Monthly Expenses": "Dépenses mensuelles",
    "Net Savings": "Épargne nette",
    "Savings Rate": "Taux d'épargne",
    "Spending by Category": "Dépenses par catégorie",
    "Income vs Expenses — Monthly": "Revenus vs Dépenses — Mensuel",
    "Net Worth — Last 12 Months": "Valeur nette — 12 derniers mois",
    "Budget Alerts": "Alertes de budget",
    "Over budget": "Dépassé",
    "Near limit": "Proche de la limite",
    "Recent Transactions": "Transactions récentes",
    "Expenses": "Dépenses",

    # ── Transactions ──────────────────────────────────────────────────────
    "⇄ Transfer": "⇄ Virement",
    "+ Add Transaction": "+ Ajouter une transaction",
    "🔍 Search…": "🔍 Rechercher…",
    "All Categories": "Toutes les catégories",
    "All Accounts": "Tous les comptes",
    "✏ Edit": "✏ Modifier",
    "🗑 Delete": "🗑 Supprimer",
    "{n} transactions": "{n} transactions",
    "No transactions match your filters.":
        "Aucune transaction ne correspond à vos filtres.",
    "No transactions yet. Click '+ Add Transaction' to start.":
        "Aucune transaction pour l'instant. Cliquez sur « + Ajouter une transaction » pour commencer.",
    "No accounts match your filters.":
        "Aucun compte ne correspond à vos filtres.",
    "No accounts yet. Click '+ Add Account' to start.":
        "Aucun compte pour l'instant. Cliquez sur « + Ajouter un compte » pour commencer.",
    "No recurring items match your filters.":
        "Aucun élément récurrent ne correspond à vos filtres.",
    "No recurring items yet. Click '+ Add Recurring' to start.":
        "Aucun élément récurrent pour l'instant. Cliquez sur « + Ajouter un récurrent » pour commencer.",
    "No transactions yet.": "Aucune transaction pour l'instant.",
    "No interest recorded yet.": "Aucun intérêt enregistré pour l'instant.",
    "Edit selected (Enter)": "Modifier la sélection (Entrée)",
    "Delete selected (Del)": "Supprimer la sélection (Suppr)",
    "Remove selected (Del)": "Retirer la sélection (Suppr)",
    "Horizon:": "Horizon :",
    "3 months": "3 mois",
    "6 months": "6 mois",
    "12 months": "12 mois",
    "Balance Today": "Solde aujourd'hui",
    "Projected ({n} mo)": "Projeté ({n} mois)",
    "Net Change": "Variation nette",
    "Projected balance over time": "Solde projeté dans le temps",
    "Upcoming recurring activity": "Activité récurrente à venir",
    "Projected Balance": "Solde projeté",
    "No recurring income or expenses to forecast.\nAdd recurring items to see where your balance is heading.":
        "Aucun revenu ou dépense récurrent à prévoir.\nAjoutez des éléments récurrents pour voir l'évolution de votre solde.",
    "⤓ Export": "⤓ Exporter",
    "Export": "Exporter",
    "Export Transactions": "Exporter les transactions",
    "Export the current filtered list to CSV or Excel":
        "Exporter la liste filtrée actuelle en CSV ou Excel",
    "There are no transactions to export.":
        "Il n'y a aucune transaction à exporter.",
    "Export Failed": "Échec de l'exportation",
    "Exported {n} transactions to:\n{path}":
        "{n} transactions exportées vers :\n{path}",
    "Add Transaction": "Ajouter une transaction",
    "Edit Transaction": "Modifier la transaction",
    "e.g. Grocery run": "ex. Épicerie",
    "Optional notes…": "Notes optionnelles…",
    "Description is required.": "La description est requise.",
    "Amount must be greater than zero.": "Le montant doit être supérieur à zéro.",
    "Please select an account.": "Veuillez sélectionner un compte.",
    "Could not save transaction:\n{err}": "Impossible d'enregistrer la transaction :\n{err}",
    "Transfer Between Accounts": "Virement entre comptes",
    "From Account": "Compte source",
    "To Account": "Compte destinataire",
    "Source and destination must be different accounts.":
        "Le compte source et le compte destinataire doivent être différents.",
    "Could not create transfer:\n{err}": "Impossible de créer le virement :\n{err}",
    "Transfers cannot be edited.\nDelete this transfer and create a new one if needed.":
        "Les virements ne peuvent pas être modifiés.\nSupprimez ce virement et créez-en un nouveau au besoin.",
    "Delete Transaction": "Supprimer la transaction",
    "Delete Transfer": "Supprimer le virement",
    "Delete '{desc}'?\nThis cannot be undone.":
        "Supprimer « {desc} » ?\nCette action est irréversible.",
    "Delete transfer '{desc}'?\nBoth legs of the transfer will be removed.":
        "Supprimer le virement « {desc} » ?\nLes deux écritures du virement seront supprimées.",
    "Could not delete:\n{err}": "Impossible de supprimer :\n{err}",

    # ── Budgets ───────────────────────────────────────────────────────────
    "+ Add Budget": "+ Ajouter un budget",
    "Add Budget": "Ajouter un budget",
    "Edit Budget": "Modifier le budget",
    "Delete Budget": "Supprimer le budget",
    "Budget Amount": "Montant du budget",
    "Budget amount must be greater than zero.": "Le montant du budget doit être supérieur à zéro.",
    "Could not save budget:\n{err}": "Impossible d'enregistrer le budget :\n{err}",
    "Delete the budget for '{name}'?": "Supprimer le budget pour « {name} » ?",
    "Could not delete budget:\n{err}": "Impossible de supprimer le budget :\n{err}",
    "No budgets set for this month.\nClick '+ Add Budget' to get started.":
        "Aucun budget défini pour ce mois.\nCliquez sur « + Ajouter un budget » pour commencer.",
    "Total Budgeted: {budgeted}  •  Spent: {spent}  •  Remaining: {remaining}":
        "Total budgété : {budgeted}  •  Dépensé : {spent}  •  Restant : {remaining}",
    "Over budget": "Dépassement",
    "Remaining": "Restant",
    "Edit budget": "Modifier le budget",
    "Delete budget": "Supprimer le budget",

    # ── Goals ─────────────────────────────────────────────────────────────
    "Financial Goals": "Objectifs financiers",
    "+ Add Goal": "+ Ajouter un objectif",
    "Add Goal": "Ajouter un objectif",
    "Edit Goal": "Modifier l'objectif",
    "Delete Goal": "Supprimer l'objectif",
    "Goal Name": "Nom de l'objectif",
    "e.g. Emergency Fund": "ex. Fonds d'urgence",
    "Target Amount": "Montant cible",
    "Current Saved": "Montant épargné",
    "Target Date": "Date cible",
    "Goal name is required.": "Le nom de l'objectif est requis.",
    "Could not save goal:\n{err}": "Impossible d'enregistrer l'objectif :\n{err}",
    "Delete goal '{name}'?": "Supprimer l'objectif « {name} » ?",
    "No goals yet.\nClick '+ Add Goal' to set your first financial target.":
        "Aucun objectif pour le moment.\nCliquez sur « + Ajouter un objectif » pour définir votre première cible.",
    "Target: {date}": "Cible : {date}",

    # ── Accounts ──────────────────────────────────────────────────────────
    "+ Add Account": "+ Ajouter un compte",
    "Add Account": "Ajouter un compte",
    "Edit Account": "Modifier le compte",
    "Delete Account": "Supprimer le compte",
    "Account Name": "Nom du compte",
    "Account Type": "Type de compte",
    "Current Balance": "Solde actuel",
    "e.g. Main Checking": "ex. Compte courant principal",
    "Balance": "Solde",
    "Account name required.": "Le nom du compte est requis.",
    "Database Error": "Erreur de base de données",
    "Could not save account:\n{err}": "Impossible d'enregistrer le compte :\n{err}",
    "Total across all accounts: {total}": "Total de tous les comptes : {total}",
    "Total (filtered): {total}": "Total (filtré) : {total}",
    "All Types": "Tous les types",
    "Record balance change as interest/gain": "Enregistrer la variation comme intérêt/gain",
    "Change of {amount} will be recorded as a {kind}.":
        "Une variation de {amount} sera enregistrée comme un {kind}.",
    "gain": "gain",
    "loss": "perte",
    "Delete account '{name}' and all its transactions?":
        "Supprimer le compte « {name} » et toutes ses transactions ?",

    # ── Reports ───────────────────────────────────────────────────────────
    "📄 Export PDF": "📄 Exporter en PDF",
    "📊 Export CSV": "📊 Exporter en CSV",
    "📗 Export Excel": "📗 Exporter en Excel",
    "Monthly Summary": "Résumé mensuel",
    "Category Analysis": "Analyse par catégorie",
    "Cash Flow": "Flux de trésorerie",
    "{month} {year} Summary": "Résumé de {month} {year}",
    "Total Income": "Revenu total",
    "Total Expenses": "Dépenses totales",
    "No expense data for this period.": "Aucune donnée de dépense pour cette période.",
    "Save PDF Report": "Enregistrer le rapport PDF",
    "Save CSV": "Enregistrer le CSV",
    "Save Excel": "Enregistrer le fichier Excel",
    "Exported": "Exporté",
    "Export Failed": "Échec de l'exportation",
    "PDF saved to:\n{path}": "PDF enregistré dans :\n{path}",
    "{n} transactions saved to:\n{path}": "{n} transactions enregistrées dans :\n{path}",

    # ── Recurring ─────────────────────────────────────────────────────────
    "Recurring Transactions": "Transactions récurrentes",
    "All Frequencies": "Toutes les fréquences",
    "+ Add Recurring": "+ Ajouter un récurrent",
    "Add Recurring": "Ajouter un récurrent",
    "Edit Recurring": "Modifier le récurrent",
    "Delete Recurring": "Supprimer le récurrent",
    "Frequency": "Fréquence",
    "Next Due": "Prochaine échéance",
    "Next Due Date": "Date de prochaine échéance",
    "To / Category": "Vers / Catégorie",
    "Direction": "Sens",
    "e.g. Weekly savings transfer": "ex. Virement d'épargne hebdomadaire",
    "Name is required.": "Le nom est requis.",
    "Both accounts are required for a transfer.": "Les deux comptes sont requis pour un virement.",
    "Could not save recurring:\n{err}": "Impossible d'enregistrer le récurrent :\n{err}",
    "Delete recurring '{name}'?\nThis will not delete transactions already posted.":
        "Supprimer le récurrent « {name} » ?\nLes transactions déjà enregistrées ne seront pas supprimées.",

    # ── Savings ───────────────────────────────────────────────────────────
    # (the bare "Savings" account-type label is defined in the enum section above)
    "Total Savings": "Épargne totale",
    "Interest This Month": "Intérêts ce mois-ci",
    "Interest This Year": "Intérêts cette année",
    "Interest All-Time": "Intérêts (total)",
    "This Month": "Ce mois-ci",
    "This Year": "Cette année",
    "All-Time": "Total",
    "Interest earned over time": "Intérêts gagnés au fil du temps",
    "Recent interest activity": "Activité d'intérêts récente",
    "No savings accounts.\nAdd a Savings account to start tracking interest.":
        "Aucun compte d'épargne.\nAjoutez un compte de type Épargne pour suivre les intérêts.",

    # ── Markets ───────────────────────────────────────────────────────────
    "Markets": "Marchés",
    "Stock": "Action",
    "Crypto": "Crypto",
    "Add Symbol": "Ajouter un symbole",
    "+ Add Symbol": "+ Ajouter un symbole",
    "Symbol": "Symbole",
    "Name (optional)": "Nom (optionnel)",
    "Optional": "Optionnel",
    "Symbol is required.": "Le symbole est requis.",
    "'{symbol}' looks like a cryptocurrency. Add it as Crypto instead?":
        "« {symbol} » ressemble à une cryptomonnaie. L'ajouter comme Crypto plutôt ?",
    "Stocks use tickers (AAPL). Crypto uses tickers too (BTC).\nFor non-US stocks add a suffix, e.g. SHOP.TO":
        "Les actions utilisent des symboles (AAPL). Les cryptos aussi (BTC).\n"
        "Pour les actions hors États-Unis, ajoutez un suffixe, ex. SHOP.TO",
    "Refresh": "Actualiser",
    "Auto-refresh:": "Actualisation auto :",
    "Off (manual)": "Désactivée (manuel)",
    "{n} min": "{n} min",
    "Updating…": "Mise à jour…",
    "Updated {time}": "Mis à jour {time}",
    "⚠ Couldn't update — showing last saved values":
        "⚠ Échec de la mise à jour — valeurs enregistrées affichées",
    "No symbols yet.\nClick '+ Add Symbol' to start tracking.":
        "Aucun symbole.\nCliquez sur « + Ajouter un symbole » pour commencer le suivi.",
    "🗑 Remove": "🗑 Retirer",
    "Remove '{symbol}' from your watchlist?": "Retirer « {symbol} » de votre liste de suivi ?",
    "Price": "Prix",
    "Change %": "Variation %",
    "Updated": "Mis à jour",

    # ── Settings ──────────────────────────────────────────────────────────
    "Appearance": "Apparence",
    "Categories": "Catégories",
    # ── Security / password ───────────────────────────────────────────────
    "Security": "Sécurité",
    "Change Password": "Changer le mot de passe",
    "Current Password": "Mot de passe actuel",
    "New Password": "Nouveau mot de passe",
    "Confirm New Password": "Confirmer le nouveau mot de passe",
    "Update Password": "Mettre à jour le mot de passe",
    "Password": "Mot de passe",
    "All fields are required.": "Tous les champs sont obligatoires.",
    "New passwords do not match.": "Les nouveaux mots de passe ne correspondent pas.",
    "Current password is incorrect.": "Le mot de passe actuel est incorrect.",
    "New password must be at least 6 characters.":
        "Le nouveau mot de passe doit comporter au moins 6 caractères.",
    "New password must be different from the current one.":
        "Le nouveau mot de passe doit être différent de l'actuel.",
    "Password updated successfully.": "Mot de passe mis à jour avec succès.",
    "Account not found.": "Compte introuvable.",
    "About": "À propos",
    "Version {v}": "Version {v}",
    "Check for updates": "Vérifier les mises à jour",
    "Checking…": "Vérification…",
    "You're on the latest version.": "Vous avez la dernière version.",
    "Update available: {v}": "Mise à jour disponible : {v}",
    "Download": "Télécharger",
    "Could not check for updates.": "Impossible de vérifier les mises à jour.",
    "Update available: {v} — see Settings ▸ About":
        "Mise à jour disponible : {v} — voir Paramètres ▸ À propos",
    "Backup & Restore": "Sauvegarde et restauration",
    "Import Data": "Importer des données",
    "Theme:": "Thème :",
    "Dark": "Sombre",
    "Light": "Clair",
    "Apply Theme": "Appliquer le thème",
    "Language:": "Langue :",
    "Apply Language": "Appliquer la langue",
    "+ Add Category": "+ Ajouter une catégorie",
    "Add Category": "Ajouter une catégorie",
    "Edit Category": "Modifier la catégorie",
    "Delete Category": "Supprimer la catégorie",
    "🗑 Delete Selected": "🗑 Supprimer la sélection",
    "Name is required.": "Le nom est requis.",
    "Could not save category:\n{err}": "Impossible d'enregistrer la catégorie :\n{err}",
    "Delete category '{name}'?": "Supprimer la catégorie « {name} » ?",
    "💾 Create Backup Now": "💾 Créer une sauvegarde",
    "Existing Backups (double-click to restore):":
        "Sauvegardes existantes (double-cliquez pour restaurer) :",
    "Backup Created": "Sauvegarde créée",
    "Saved to:\n{path}": "Enregistré dans :\n{path}",
    "Restore Backup": "Restaurer la sauvegarde",
    "Restoring will overwrite your current data.\nProceed?":
        "La restauration écrasera vos données actuelles.\nContinuer ?",
    "Restored": "Restauré",
    "Backup restored. Please restart the application.":
        "Sauvegarde restaurée. Veuillez redémarrer l'application.",
    "Failed": "Échec",
    "Could not restore backup.": "Impossible de restaurer la sauvegarde.",
    "Import transactions from a CSV or Excel file.":
        "Importez des transactions depuis un fichier CSV ou Excel.",
    "Required columns: date, description, amount\nOptional: category, account, notes":
        "Colonnes requises : date, description, montant\nOptionnelles : catégorie, compte, notes",
    "📥 Import CSV": "📥 Importer un CSV",
    "📥 Import Excel": "📥 Importer un Excel",
    "Import CSV": "Importer un CSV",
    "Import Excel": "Importer un Excel",
    "Import Errors": "Erreurs d'importation",
    "Imported {n} transactions.": "{n} transactions importées.",
    " {n} errors.": " {n} erreurs.",
}


_TABLES: dict[str, dict[str, str]] = {
    "en": {},   # English uses the keys verbatim
    "fr": _FR,
}

# Localized 3-letter month abbreviations for chart axes (Jan…Dec order).
_MONTH_ABBR: dict[str, list[str]] = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "fr": ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin",
           "Juil", "Août", "Sept", "Oct", "Nov", "Déc"],
}


# ── Public API ───────────────────────────────────────────────────────────────

def set_language(code: str) -> None:
    """Set the active language. Unknown codes fall back to the default."""
    global _current_language
    _current_language = code if code in LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    """Return the active language code (e.g. 'en' or 'fr')."""
    return _current_language


def tr(key: str) -> str:
    """
    Translate an English source string into the active language.

    Missing keys (or any string while English is active) fall back to the key
    itself, so partially-translated UIs degrade gracefully to English.
    """
    table = _TABLES.get(_current_language, {})
    return table.get(key, key)


def month_abbr() -> list[str]:
    """Return the 12 chart-axis month abbreviations for the active language."""
    return _MONTH_ABBR.get(_current_language, _MONTH_ABBR["en"])

