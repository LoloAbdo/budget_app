"""
views/login_view.py
Login / Registration dialog shown before the main window.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QMessageBox, QStackedWidget,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter

from services.auth_service import AuthService
from views.fonts import ui_font
from views.i18n import tr


def _emoji_icon(emoji: str, size: int = 18) -> QIcon:
    """Render an emoji glyph into a QIcon (avoids shipping image assets)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    font = QFont()
    font.setPointSize(int(size * 0.7))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
    painter.end()
    return QIcon(pixmap)


class LoginView(QDialog):
    """Modal dialog for login / registration."""

    login_success = pyqtSignal(dict)  # emits the user dict on success

    def __init__(self, auth: AuthService, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth
        self.setWindowTitle(tr("Budget Manager — Sign In"))
        self.setFixedSize(440, 520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        # Logo / Title area
        title = QLabel(tr("💰 Budget Manager"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(ui_font(20, QFont.Weight.Bold))
        root.addWidget(title)

        subtitle = QLabel(tr("Personal Finance, Simplified"))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("muted")
        root.addWidget(subtitle)

        # ── Stacked widget: Login ↔ Register ─────────────────────────────────
        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_login_page())   # index 0
        self._stack.addWidget(self._build_register_page()) # index 1
        self._stack.addWidget(self._build_reset_page())    # index 2

        # Toggle link (login ↔ register; "back" from the reset page)
        self._toggle_btn = QPushButton(tr("Don't have an account? Register"))
        self._toggle_btn.setObjectName("secondary")
        self._toggle_btn.setAutoDefault(False)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle_page)
        root.addWidget(self._toggle_btn)

    def _build_login_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        layout.addWidget(QLabel(tr("Email")))
        self._login_email = QLineEdit()
        self._login_email.setPlaceholderText("you@example.com")
        layout.addWidget(self._login_email)

        layout.addWidget(QLabel(tr("Password")))
        self._login_pw = QLineEdit()
        self._login_pw.setPlaceholderText("••••••••")
        self._login_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._add_password_eye(self._login_pw)
        layout.addWidget(self._login_pw)

        btn = QPushButton(tr("Sign In"))
        btn.setAutoDefault(False)   # prevent Enter from double-firing with returnPressed
        btn.clicked.connect(self._do_login)
        self._login_email.returnPressed.connect(self._do_login)
        self._login_pw.returnPressed.connect(self._do_login)
        layout.addWidget(btn)

        forgot = QPushButton(tr("Forgot password?"))
        forgot.setObjectName("secondary")
        forgot.setAutoDefault(False)
        forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot.clicked.connect(lambda: self._show_page(2))
        layout.addWidget(forgot)

        layout.addStretch()
        return page

    def _build_reset_page(self) -> QWidget:
        """Reset a forgotten password with a one-time recovery code."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(QLabel(tr("Email")))
        self._reset_email = QLineEdit()
        self._reset_email.setPlaceholderText("you@example.com")
        layout.addWidget(self._reset_email)

        layout.addWidget(QLabel(tr("Recovery code")))
        self._reset_code = QLineEdit()
        self._reset_code.setPlaceholderText("XXXX-XXXX-XXXX")
        layout.addWidget(self._reset_code)

        layout.addWidget(QLabel(tr("New Password")))
        self._reset_pw = QLineEdit()
        self._reset_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._add_password_eye(self._reset_pw)
        layout.addWidget(self._reset_pw)

        layout.addWidget(QLabel(tr("Confirm New Password")))
        self._reset_pw2 = QLineEdit()
        self._reset_pw2.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self._reset_pw2)

        btn = QPushButton(tr("Reset Password"))
        btn.setAutoDefault(False)
        btn.clicked.connect(self._do_reset)
        for field in (self._reset_email, self._reset_code, self._reset_pw, self._reset_pw2):
            field.returnPressed.connect(self._do_reset)
        layout.addWidget(btn)
        layout.addStretch()
        return page

    def _build_register_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(QLabel(tr("Full Name")))
        self._reg_name = QLineEdit()
        self._reg_name.setPlaceholderText("Jane Doe")
        layout.addWidget(self._reg_name)

        layout.addWidget(QLabel(tr("Email")))
        self._reg_email = QLineEdit()
        self._reg_email.setPlaceholderText("you@example.com")
        layout.addWidget(self._reg_email)

        layout.addWidget(QLabel(tr("Password")))
        self._reg_pw = QLineEdit()
        self._reg_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._add_password_eye(self._reg_pw)
        layout.addWidget(self._reg_pw)

        layout.addWidget(QLabel(tr("Currency")))
        self._reg_currency = QComboBox()
        from services.fx_service import CURRENCIES
        self._reg_currency.addItems(CURRENCIES)
        layout.addWidget(self._reg_currency)

        btn = QPushButton(tr("Create Account"))
        btn.setObjectName("success")
        btn.setAutoDefault(False)
        btn.clicked.connect(self._do_register)
        for field in (self._reg_name, self._reg_email, self._reg_pw):
            field.returnPressed.connect(self._do_register)
        layout.addWidget(btn)
        layout.addStretch()
        return page

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _add_password_eye(self, line_edit: QLineEdit) -> None:
        """Add a clickable eye icon inside *line_edit* to toggle password visibility."""
        show_icon = _emoji_icon("👁")
        hide_icon = _emoji_icon("🙈")
        action = line_edit.addAction(show_icon, QLineEdit.ActionPosition.TrailingPosition)
        action.setCheckable(True)
        action.setToolTip(tr("Show password"))

        def on_toggled(checked: bool) -> None:
            line_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
            action.setIcon(hide_icon if checked else show_icon)
            action.setToolTip(tr("Hide password") if checked else tr("Show password"))

        action.toggled.connect(on_toggled)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _show_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        if index == 0:
            self._toggle_btn.setText(tr("Don't have an account? Register"))
        elif index == 1:
            self._toggle_btn.setText(tr("Already have an account? Sign In"))
        else:
            self._toggle_btn.setText(tr("Back to sign in"))

    def _toggle_page(self) -> None:
        # From login → register; from register or reset → back to login.
        self._show_page(1 if self._stack.currentIndex() == 0 else 0)

    def _do_login(self) -> None:
        ok, user, msg = self._auth.login(
            self._login_email.text().strip(),
            self._login_pw.text(),
        )
        if ok and user:
            self.login_success.emit(user)
            self.accept()
        else:
            QMessageBox.warning(self, tr("Login Failed"), msg)

    def _do_register(self) -> None:
        ok, msg = self._auth.register(
            self._reg_name.text().strip(),
            self._reg_email.text().strip(),
            self._reg_pw.text(),
            self._reg_currency.currentText(),
        )
        if ok:
            QMessageBox.information(self, tr("Success"), msg + "\n" + tr("You can now sign in."))
            self._toggle_page()
        else:
            QMessageBox.warning(self, tr("Registration Failed"), msg)

    def _do_reset(self) -> None:
        email = self._reset_email.text().strip()
        code = self._reset_code.text()
        new, confirm = self._reset_pw.text(), self._reset_pw2.text()

        if not email or not code or not new or not confirm:
            QMessageBox.warning(self, tr("Reset Password"), tr("All fields are required."))
            return
        if new != confirm:
            QMessageBox.warning(self, tr("Reset Password"), tr("New passwords do not match."))
            return

        ok, msg = self._auth.reset_password_with_code(email, code, new)
        if ok:
            QMessageBox.information(
                self, tr("Success"), tr(msg) + "\n" + tr("You can now sign in.")
            )
            for field in (self._reset_code, self._reset_pw, self._reset_pw2):
                field.clear()
            self._login_email.setText(email)
            self._show_page(0)
        else:
            QMessageBox.warning(self, tr("Reset Password"), tr(msg))
