"""
views/main_window.py
Main application window: sidebar navigation + content panel stack.
"""

import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QSizePolicy, QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QThreadPool, QSettings
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut

from database import DatabaseManager
from services.backup_service import BackupService
from services.recurring_service import RecurringService
from views.theme import theme_qss, set_active_theme, is_dark_theme
from views.fonts import ui_font
from views.winutil import apply_title_bar, set_dark_mode
from views.dashboard_view   import DashboardView
from views.transactions_view import TransactionsView
from views.budget_view      import BudgetView
from views.goals_view       import GoalsView
from views.debt_view        import DebtView
from views.accounts_view    import AccountsView
from views.reports_view     import ReportsView
from views.forecast_view    import ForecastView
from views.recurring_view   import RecurringView
from views.subscriptions_view import SubscriptionsView
from views.savings_view     import SavingsView
from views.markets_view     import MarketsView
from views.activity_view    import ActivityView
from views.settings_view    import SettingsView
from views.update_check     import UpdateCheckWorker
from views.i18n             import tr, set_language
from version               import __version__


# Labels here are English source strings; they are translated at build time
# via tr() so the sidebar re-localises whenever the language changes.
NAV_ITEMS = [
    ("🏠", "Dashboard",      0),
    ("💳", "Transactions",   1),
    ("📊", "Budgets",        2),
    ("🎯", "Goals",          3),
    ("💸", "Debts",          4),
    ("🏦", "Accounts",       5),
    ("📈", "Reports",        6),
    ("🔮", "Forecast",       7),
    ("🔄", "Recurring",      8),
    ("🧾", "Subscriptions",  9),
    ("🐷", "Savings",        10),
    ("💹", "Markets",        11),
    ("📝", "Activity",       12),
    ("⚙️",  "Settings",      13),
]


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(
        self,
        db: DatabaseManager,
        user: dict,
        backup_service: BackupService,
        current_theme: str = "dark",
    ) -> None:
        super().__init__()
        self._db      = db
        self._user    = user
        self._backup  = backup_service
        self._theme   = current_theme
        self._recurring_svc = RecurringService(db)

        self.setWindowTitle(tr("Budget Manager"))
        self.setMinimumSize(1100, 700)
        self.resize(1280, 780)

        # Restore the window size/position from the last session, if any.
        self._settings = QSettings()
        geo = self._settings.value("window/geometry")
        if geo is not None:
            self.restoreGeometry(geo)

        self._apply_theme(current_theme)
        self._build_ui()
        self._restore_last_panel()
        self._setup_shortcuts()
        self._process_recurring()
        self._start_backup_timer()
        # Follow the OS when the theme is "auto": Windows switching between
        # light and dark re-themes the app live.
        from PyQt6.QtGui import QGuiApplication
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            self._on_os_color_scheme_changed
        )
        # Quiet, one-shot update check shortly after launch (non-blocking).
        QTimer.singleShot(2500, self._check_updates_quietly)
        # Refresh FX rates in the background if any account uses a foreign
        # currency and the cached rates are stale (>24h) or missing.
        QTimer.singleShot(1500, self._refresh_fx_quietly)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _apply_theme(self, theme: str) -> None:
        self._theme = theme
        set_active_theme(theme)          # keep chart colours in sync with the UI
        # Native title bars (this window + future dialogs) follow the theme.
        dark = is_dark_theme(theme)
        set_dark_mode(dark)
        apply_title_bar(self, dark)
        self.setStyleSheet(theme_qss(theme))
        # Propagate to any already-created child widgets
        for child in self.findChildren(QWidget):
            child.setStyleSheet("")   # force re-paint from parent

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Initialise nav dict BEFORE building sidebar (sidebar populates it)
        self._views: dict[int, QWidget] = {}
        self._nav_buttons: dict[int, QPushButton] = {}

        # Sidebar
        root_layout.addWidget(self._build_sidebar())

        # Content stack
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, 1)

        # Lazy-create all views
        self._dashboard_view    = DashboardView(self._db, self._user)
        self._txn_view          = TransactionsView(self._db, self._user)
        self._budget_view       = BudgetView(self._db, self._user)
        self._goals_view        = GoalsView(self._db, self._user)
        self._debt_view         = DebtView(self._db, self._user)
        self._accounts_view     = AccountsView(self._db, self._user)
        self._reports_view      = ReportsView(self._db, self._user)
        self._forecast_view     = ForecastView(self._db, self._user)
        self._recurring_view    = RecurringView(self._db, self._user)
        self._subscriptions_view = SubscriptionsView(self._db, self._user)
        self._savings_view      = SavingsView(self._db, self._user)
        self._markets_view      = MarketsView(self._db, self._user)
        self._activity_view     = ActivityView(self._db, self._user)
        self._settings_view     = SettingsView(
            self._db, self._user, self._backup, self._theme
        )

        for view in [
            self._dashboard_view,
            self._txn_view,
            self._budget_view,
            self._goals_view,
            self._debt_view,
            self._accounts_view,
            self._reports_view,
            self._forecast_view,
            self._recurring_view,
            self._subscriptions_view,
            self._savings_view,
            self._markets_view,
            self._activity_view,
            self._settings_view,
        ]:
            self._stack.addWidget(view)

        # Wire signals
        self._txn_view.transaction_changed.connect(self._dashboard_view.refresh)
        self._txn_view.transaction_changed.connect(self._budget_view.refresh)
        self._txn_view.transaction_changed.connect(self._reports_view.refresh)
        self._txn_view.transaction_changed.connect(self._accounts_view.refresh)
        self._txn_view.transaction_changed.connect(self._savings_view.refresh)
        self._txn_view.transaction_changed.connect(self._forecast_view.refresh)
        self._txn_view.transaction_changed.connect(self._subscriptions_view.refresh)
        self._accounts_view.accounts_changed.connect(self._dashboard_view.refresh)
        self._accounts_view.accounts_changed.connect(self._savings_view.refresh)
        self._accounts_view.accounts_changed.connect(self._forecast_view.refresh)
        self._budget_view.budget_changed.connect(self._dashboard_view.refresh)
        self._settings_view.theme_changed.connect(self._on_theme_changed)
        self._settings_view.data_changed.connect(self._refresh_all)
        self._settings_view.language_changed.connect(self._on_language_changed)
        self._settings_view.font_scale_changed.connect(self._on_font_scale_changed)
        self._settings_view.accent_changed.connect(self._on_accent_changed)

        # Activate dashboard
        self._switch_to(0)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(4)

        # App logo
        logo = QLabel(tr("💰 Budget"))
        logo.setFont(ui_font(16, QFont.Weight.Bold))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setContentsMargins(0, 0, 0, 16)
        layout.addWidget(logo)

        # User greeting
        user_lbl = QLabel(self._user["name"])
        user_lbl.setObjectName("muted")
        user_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_lbl.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(user_lbl)

        # Nav buttons
        for icon, label, idx in NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {tr(label)}")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setMinimumHeight(42)
            btn.clicked.connect(lambda checked, i=idx: self._switch_to(i))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)
            self._nav_buttons[idx] = btn

        layout.addStretch()

        # Sign out
        signout_btn = QPushButton(f"  🚪  {tr('Sign Out')}")
        signout_btn.setObjectName("navBtn")
        signout_btn.clicked.connect(self._sign_out)
        layout.addWidget(signout_btn)

        return sidebar

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _switch_to(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, btn in self._nav_buttons.items():
            btn.setChecked(i == idx)
        widget = self._stack.widget(idx)
        # The forecast depends on recurring items, which emit no change signal,
        # so recompute it whenever the user opens the panel.
        if widget is self._forecast_view:
            self._forecast_view.refresh()
        # The activity log grows from every panel; reload it when opened so it's
        # always current without needing a signal from each view.
        elif widget is self._activity_view:
            self._activity_view.refresh()
        # A recurring item can come due while the app stays open (past its due
        # date). Post any now-due items when opening Transactions so the tab is
        # current without restarting the app.
        elif widget is self._txn_view:
            if self._process_recurring() > 0:
                self._txn_view.refresh()
                self._txn_view.transaction_changed.emit()

    def _restore_last_panel(self) -> None:
        """Reopen on the sidebar panel that was active when the app last closed."""
        idx = self._settings.value("window/panel", 0, type=int)
        if 0 <= idx < len(self._nav_buttons):
            self._switch_to(idx)

    def closeEvent(self, event) -> None:
        """Persist window geometry and the active panel for next launch."""
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/panel", self._stack.currentIndex())
        super().closeEvent(event)

    # ── Shortcuts ──────────────────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        for key, idx in [
            ("Ctrl+1", 0), ("Ctrl+2", 1), ("Ctrl+3", 2), ("Ctrl+4", 3),
            ("Ctrl+5", 4), ("Ctrl+6", 5), ("Ctrl+7", 6), ("Ctrl+8", 7),
            ("Ctrl+9", 8), ("Ctrl+0", 9),
        ]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda i=idx: self._switch_to(i))
        # Global transaction search
        search_sc = QShortcut(QKeySequence("Ctrl+F"), self)
        search_sc.activated.connect(self._open_search)

    def _open_search(self) -> None:
        from views.search_dialog import SearchDialog
        dlg = SearchDialog(self._db, self._user, parent=self)
        dlg.jump_requested.connect(self._on_search_jump)
        dlg.exec()

    def _on_search_jump(self, keyword: str) -> None:
        """Open the Transactions panel filtered to the search query."""
        self._txn_view.apply_global_search(keyword)
        self._switch_to(1)   # Transactions panel

    # ── Recurring ──────────────────────────────────────────────────────────────

    def _process_recurring(self) -> int:
        count = self._recurring_svc.process_due(self._user["id"])
        if count > 0:
            from views.toast import show_toast
            show_toast(self, tr("✓ Posted {n} recurring transaction(s)").format(n=count))
        return count

    # ── Auto-backup timer ──────────────────────────────────────────────────────

    def _check_updates_quietly(self) -> None:
        """Background check on launch; shows a status-bar notice only if newer."""
        worker = UpdateCheckWorker(__version__)
        worker.signals.done.connect(self._on_update_available)
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(object)
    def _on_update_available(self, info) -> None:
        if getattr(info, "available", False) and info.latest:
            self.statusBar().showMessage(
                tr("Update available: {v} — see Settings ▸ About").format(v=info.latest),
                10000,
            )

    def _refresh_fx_quietly(self) -> None:
        """Background FX refresh on launch — only when rates are actually needed."""
        from services.fx_service import FxService
        from views.fx_refresh import FxRefreshWorker
        if not FxService(self._db).needs_refresh(self._user["id"]):
            return
        worker = FxRefreshWorker(self._db, self._user["id"])
        worker.signals.done.connect(self._on_fx_refreshed)
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(dict)
    def _on_fx_refreshed(self, results: dict) -> None:
        # Converted totals may have moved — redraw the panels that show them,
        # and say so: silently shifting numbers erode trust.
        if any(v for v in results.values()):
            self._dashboard_view.refresh()
            self._accounts_view.refresh()
            self._forecast_view.refresh()
            self._savings_view.refresh()
            from views.toast import show_toast
            show_toast(self, tr("Exchange rates updated"), kind="info")

    def _start_backup_timer(self) -> None:
        """Auto-backup every 24 hours while the app is running."""
        timer = QTimer(self)
        timer.setInterval(24 * 60 * 60 * 1000)
        timer.timeout.connect(lambda: self._backup.create_backup("auto"))
        timer.start()

    # ── Slots ──────────────────────────────────────────────────────────────────

    @pyqtSlot(str)
    def _on_theme_changed(self, theme: str) -> None:
        self._apply_theme(theme)
        # Persist so the choice survives a restart (mirrors language).
        self._db.update_user_theme(self._user["id"], theme)
        self._user["theme"] = theme
        # Charts are matplotlib (not QSS) — redraw them so they pick up the palette
        for view in (self._dashboard_view, self._reports_view, self._savings_view):
            view.refresh()

    def _on_os_color_scheme_changed(self, _scheme) -> None:
        """Windows toggled light/dark — re-resolve if we're following the OS."""
        if self._theme == "auto":
            self._apply_theme("auto")
            for view in (self._dashboard_view, self._reports_view, self._savings_view):
                view.refresh()

    @pyqtSlot(str)
    def _on_language_changed(self, lang: str) -> None:
        """Persist the new language and rebuild the whole UI in place."""
        self._db.update_user_language(self._user["id"], lang)
        self._user["language"] = lang
        set_language(lang)

        # Preserve which panel the user was on across the rebuild
        current_idx = self._stack.currentIndex() if hasattr(self, "_stack") else 0

        self.setWindowTitle(tr("Budget Manager"))
        self._build_ui()              # recreates sidebar + all views in the new language
        self._apply_theme(self._theme)
        self._switch_to(current_idx)

    @pyqtSlot(float)
    def _on_font_scale_changed(self, scale: float) -> None:
        """Persist the new font scale and rebuild the UI at the new size."""
        from views import fonts, theme
        self._db.update_user_font_scale(self._user["id"], scale)
        self._user["font_scale"] = scale
        fonts.set_scale(scale)
        theme.set_font_scale(scale)
        # Same pattern as a language change: rebuild everything in place so
        # both QSS sizes and code-created QFonts pick up the scale.
        current_idx = self._stack.currentIndex() if hasattr(self, "_stack") else 0
        self._build_ui()
        self._apply_theme(self._theme)
        self._switch_to(current_idx)

    @pyqtSlot(str)
    def _on_accent_changed(self, accent: str) -> None:
        """Persist and apply a custom accent color ('' resets to the theme's)."""
        from views.theme import set_accent
        value = accent or None
        self._db.update_user_accent(self._user["id"], value)
        self._user["accent"] = value
        set_accent(value)
        self._apply_theme(self._theme)
        self._settings_view._refresh_accent_button()
        # Charts draw the accent (net-worth/forecast lines) — redraw them.
        for view in (self._dashboard_view, self._reports_view,
                     self._savings_view, self._forecast_view):
            view.refresh()

    def _refresh_all(self) -> None:
        self._dashboard_view.refresh()
        self._txn_view.refresh()
        self._budget_view.refresh()
        self._reports_view.refresh()
        self._recurring_view.refresh()
        self._subscriptions_view.refresh()
        self._savings_view.refresh()
        self._forecast_view.refresh()

    def _sign_out(self) -> None:
        reply = QMessageBox.question(
            self, tr("Sign Out"), tr("Sign out of Budget Manager?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            # Re-launch login window
            from views.login_view import LoginView
            from services.auth_service import AuthService
            auth = AuthService(self._db)
            login = LoginView(auth)
            login.login_success.connect(
                lambda u: _reopen_main(self._db, u, self._backup, self._theme)
            )
            login.exec()


def _reopen_main(db, user, backup, theme):
    """Re-create the main window after sign-out, with the new user's prefs."""
    from views import fonts, theme as theme_mod
    set_language(user.get("language", "en"))
    fonts.set_scale(user.get("font_scale") or 1.0)
    theme_mod.set_font_scale(user.get("font_scale") or 1.0)
    theme_mod.set_accent(user.get("accent"))
    win = MainWindow(db, user, backup, user.get("theme") or theme)
    win.show()
    # Keep reference alive
    QApplication.instance()._main_window = win  # type: ignore[attr-defined]
