"""
views/settings_view.py
Settings panel: theme toggle, categories, backup/restore, import.
"""

from typing import Optional
from datetime import datetime

import os
import tempfile

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QComboBox, QFileDialog, QMessageBox,
    QFrame, QTabWidget, QListWidget, QListWidgetItem, QProgressBar,
    QApplication, QPlainTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThreadPool
from PyQt6.QtGui import QColor, QFont

from database import DatabaseManager
from services.auth_service import AuthService
from services.backup_service import BackupService
from services.import_export_service import ImportExportService
from services.update_service import can_auto_update, launch_installer
from views.i18n import tr, set_language, get_language, LANGUAGES
from views.sortable import SortableItem, enable_sorting
from views.update_check import UpdateCheckWorker, UpdateDownloadWorker
from version import __version__


# ── Recovery codes dialog ──────────────────────────────────────────────────────

class RecoveryCodesDialog(QDialog):
    """Shows freshly generated recovery codes — the only time they're visible."""

    def __init__(self, codes: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Your recovery codes"))
        self.setMinimumWidth(380)
        self._codes_text = "\n".join(codes)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        warn = QLabel(tr(
            "Store these codes somewhere safe — they are shown only once. "
            "Each code can be used once to reset your password."
        ))
        warn.setWordWrap(True)
        layout.addWidget(warn)

        box = QPlainTextEdit(self._codes_text)
        box.setReadOnly(True)
        box.setMinimumHeight(170)
        layout.addWidget(box)

        btns = QHBoxLayout()
        copy_btn = QPushButton(tr("Copy"))
        copy_btn.clicked.connect(self._copy)
        btns.addWidget(copy_btn)

        save_btn = QPushButton(tr("Save to file…"))
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)

        btns.addStretch()
        close_btn = QPushButton(tr("Close"))
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        self._status = QLabel("")
        self._status.setObjectName("muted")
        layout.addWidget(self._status)

    def _copy(self) -> None:
        QApplication.clipboard().setText(self._codes_text)
        self._status.setText(tr("Copied to clipboard."))

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save to file…"),
            "budget-manager-recovery-codes.txt", "Text files (*.txt)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._codes_text + "\n")
            self._status.setText(tr("Saved."))
        except OSError as exc:
            QMessageBox.warning(self, tr("Recovery Codes"), str(exc))


# ── Category dialog ────────────────────────────────────────────────────────────

PRESET_COLORS = [
    "#F44336","#E91E63","#9C27B0","#3F51B5","#2196F3",
    "#00BCD4","#009688","#4CAF50","#8BC34A","#FFC107",
    "#FF9800","#FF5722","#795548","#607D8B","#00D4AA",
]


class CategoryDialog(QDialog):
    def __init__(self, db: DatabaseManager, category: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._category = category
        self.setWindowTitle(tr("Edit Category") if category else tr("Add Category"))
        self.setMinimumWidth(360)
        self._build_ui()
        if category:
            self._populate(category)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        form.addRow(tr("Name"), self._name_edit)

        self._type_combo = QComboBox()
        # Display localized label, store the English value used in the DB
        self._type_combo.addItem(tr("Income"), "Income")
        self._type_combo.addItem(tr("Expense"), "Expense")
        form.addRow(tr("Type"), self._type_combo)

        self._color_combo = QComboBox()
        for c in PRESET_COLORS:
            self._color_combo.addItem(c, c)
            self._color_combo.setItemData(
                self._color_combo.count() - 1, QColor(c), Qt.ItemDataRole.BackgroundRole
            )
        form.addRow(tr("Color"), self._color_combo)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(tr("Save"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _populate(self, c: dict) -> None:
        self._name_edit.setText(c["name"])
        idx = self._type_combo.findData(c["type"])
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        for i in range(self._color_combo.count()):
            if self._color_combo.itemData(i) == c["color"]:
                self._color_combo.setCurrentIndex(i)
                break

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("Validation"), tr("Name is required."))
            return
        try:
            cat_type = self._type_combo.currentData()
            color    = self._color_combo.currentData()
            if self._category:
                self._db.update_category(self._category["id"], name, cat_type, color)
            else:
                self._db.create_category(name, cat_type, color)
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, tr("Error"), tr("Could not save category:\n{err}").format(err=exc))
            return
        self.accept()


# ── Settings view ──────────────────────────────────────────────────────────────

class SettingsView(QWidget):
    theme_changed      = pyqtSignal(str)    # a theme key from views.theme.THEMES
    data_changed       = pyqtSignal()
    language_changed   = pyqtSignal(str)    # "en" or "fr"
    font_scale_changed = pyqtSignal(float)  # 0.9–1.25
    accent_changed     = pyqtSignal(str)    # "#RRGGBB", or "" = theme default

    def __init__(
        self,
        db: DatabaseManager,
        user: dict,
        backup_service: BackupService,
        current_theme: str = "dark",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db      = db
        self._user    = user
        self._backup  = backup_service
        self._ie      = ImportExportService(db)
        self._theme   = current_theme
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel(tr("Settings"))
        title.setObjectName("heading")
        layout.addWidget(title)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_appearance_tab(), tr("Appearance"))
        tabs.addTab(self._build_currency_tab(),   tr("Currency"))
        tabs.addTab(self._build_security_tab(),   tr("Security"))
        tabs.addTab(self._build_categories_tab(), tr("Categories"))
        tabs.addTab(self._build_backup_tab(),     tr("Backup & Restore"))
        tabs.addTab(self._build_import_tab(),     tr("Import Data"))
        tabs.addTab(self._build_about_tab(),      tr("About"))

    # ── Appearance ─────────────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # ── Theme row ─────────────────────────────────────────────────────────
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Theme:")))
        self._theme_combo = QComboBox()
        # Display localized label, store the theme key used in the DB
        from views.theme import available_themes
        for key, label in available_themes():
            self._theme_combo.addItem(tr(label), key)
        theme_idx = self._theme_combo.findData(self._theme)
        if theme_idx >= 0:
            self._theme_combo.setCurrentIndex(theme_idx)
        row.addWidget(self._theme_combo)
        row.addStretch()
        layout.addLayout(row)

        apply_btn = QPushButton(tr("Apply Theme"))
        apply_btn.setMaximumWidth(150)
        apply_btn.clicked.connect(self._apply_theme)
        layout.addWidget(apply_btn)

        # ── Language row ──────────────────────────────────────────────────────
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(tr("Language:")))
        self._lang_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self._lang_combo.addItem(label, code)   # native name, store code
        lang_idx = self._lang_combo.findData(get_language())
        if lang_idx >= 0:
            self._lang_combo.setCurrentIndex(lang_idx)
        lang_row.addWidget(self._lang_combo)
        lang_row.addStretch()
        layout.addLayout(lang_row)

        apply_lang_btn = QPushButton(tr("Apply Language"))
        apply_lang_btn.setMaximumWidth(180)
        apply_lang_btn.clicked.connect(self._apply_language)
        layout.addWidget(apply_lang_btn)

        # ── Font size row ─────────────────────────────────────────────────────
        from views.fonts import FONT_SCALES
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel(tr("Font size:")))
        self._scale_combo = QComboBox()
        for value, label in FONT_SCALES:
            self._scale_combo.addItem(label, value)
        current_scale = float(self._user.get("font_scale") or 1.0)
        idx = self._scale_combo.findData(current_scale)
        if idx >= 0:
            self._scale_combo.setCurrentIndex(idx)
        self._scale_combo.activated.connect(self._apply_font_scale)
        size_row.addWidget(self._scale_combo)
        size_hint = QLabel(tr("Applies immediately to the whole app."))
        size_hint.setObjectName("muted")
        size_row.addWidget(size_hint)
        size_row.addStretch()
        layout.addLayout(size_row)

        # ── Accent color row ──────────────────────────────────────────────────
        accent_row = QHBoxLayout()
        accent_row.addWidget(QLabel(tr("Accent color:")))
        self._accent_btn = QPushButton()
        self._accent_btn.setObjectName("secondary")
        self._accent_btn.setMaximumWidth(160)
        self._accent_btn.clicked.connect(self._pick_accent)
        accent_row.addWidget(self._accent_btn)
        reset_btn = QPushButton(tr("Reset"))
        reset_btn.setObjectName("secondary")
        reset_btn.setMaximumWidth(90)
        reset_btn.clicked.connect(lambda: self.accent_changed.emit(""))
        accent_row.addWidget(reset_btn)
        accent_hint = QLabel(tr("Recolors buttons, highlights and charts in every theme."))
        accent_hint.setObjectName("muted")
        accent_row.addWidget(accent_hint)
        accent_row.addStretch()
        layout.addLayout(accent_row)
        self._refresh_accent_button()

        layout.addStretch()
        return w

    def _apply_font_scale(self) -> None:
        scale = self._scale_combo.currentData()
        if scale != float(self._user.get("font_scale") or 1.0):
            self.font_scale_changed.emit(scale)

    def _refresh_accent_button(self) -> None:
        """Show the current accent as a swatch on the picker button."""
        accent = self._user.get("accent")
        if accent:
            self._accent_btn.setText(accent)
            self._accent_btn.setStyleSheet(
                f"background: {accent}; color: #FFFFFF; border: none;"
            )
        else:
            self._accent_btn.setText(tr("Theme default"))
            self._accent_btn.setStyleSheet("")

    def _pick_accent(self) -> None:
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor
        initial = QColor(self._user.get("accent") or "#7C5CFF")
        color = QColorDialog.getColor(initial, self, tr("Pick an accent color"))
        if color.isValid():
            self.accent_changed.emit(color.name().upper())

    def _apply_theme(self) -> None:
        t = self._theme_combo.currentData()
        self._theme = t
        self.theme_changed.emit(t)

    def _apply_language(self) -> None:
        code = self._lang_combo.currentData()
        if code != get_language():
            self.language_changed.emit(code)

    # ── Currency ───────────────────────────────────────────────────────────────

    def _build_currency_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        home = self._db.get_home_currency(self._user["id"])
        home_lbl = QLabel(tr("Home currency: {cur}").format(cur=home))
        home_lbl.setObjectName("subheading")
        layout.addWidget(home_lbl)

        hint = QLabel(tr(
            "Each account holds money in its own currency; dashboards, reports "
            "and budgets convert everything into your home currency using the "
            "rates below. Rates come from free public sources and are cached, "
            "so the app keeps working offline with the last known rate."
        ))
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._fx_table = QTableWidget()
        self._fx_table.setColumnCount(3)
        self._fx_table.setHorizontalHeaderLabels([tr("Pair"), tr("Rate"), tr("Updated")])
        self._fx_table.setAlternatingRowColors(True)
        self._fx_table.verticalHeader().setVisible(False)
        self._fx_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self._fx_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._fx_table)

        btn_row = QHBoxLayout()
        self._fx_refresh_btn = QPushButton(tr("⟳ Refresh Rates"))
        self._fx_refresh_btn.setMaximumWidth(180)
        self._fx_refresh_btn.clicked.connect(self._refresh_fx_rates)
        btn_row.addWidget(self._fx_refresh_btn)
        self._fx_status = QLabel("")
        self._fx_status.setObjectName("muted")
        btn_row.addWidget(self._fx_status)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._reload_fx_table()
        return w

    def _reload_fx_table(self) -> None:
        rates = self._db.get_fx_rates()
        self._fx_table.setRowCount(len(rates))
        for r, row in enumerate(rates):
            self._fx_table.setItem(r, 0, QTableWidgetItem(f"1 {row['base']} → {row['quote']}"))
            rate_item = QTableWidgetItem(f"{row['rate']:,.4f}")
            rate_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._fx_table.setItem(r, 1, rate_item)
            self._fx_table.setItem(r, 2, QTableWidgetItem(row["updated"] or ""))
        if not rates:
            self._fx_status.setText(tr("No rates cached yet — add an account in another currency, then refresh."))

    def _refresh_fx_rates(self) -> None:
        from views.fx_refresh import FxRefreshWorker
        self._fx_refresh_btn.setEnabled(False)
        self._fx_status.setText(tr("Fetching latest rates…"))
        worker = FxRefreshWorker(self._db, self._user["id"])
        worker.signals.done.connect(self._on_fx_refreshed)
        QThreadPool.globalInstance().start(worker)

    @pyqtSlot(dict)
    def _on_fx_refreshed(self, results: dict) -> None:
        self._fx_refresh_btn.setEnabled(True)
        self._reload_fx_table()
        if not results:
            self._fx_status.setText(tr("All accounts use your home currency — nothing to fetch."))
        elif all(v is None for v in results.values()):
            self._fx_status.setText(tr("Could not fetch rates (offline?). Using last cached values."))
        else:
            ok = sum(1 for v in results.values() if v)
            self._fx_status.setText(tr("Updated {n} rate(s).").format(n=ok))
            self.data_changed.emit()   # totals may shift — refresh the panels

    # ── Security ───────────────────────────────────────────────────────────────

    def _build_security_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel(tr("Change Password"))
        title.setObjectName("subheading")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self._current_pw = QLineEdit()
        self._current_pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("Current Password"), self._current_pw)

        self._new_pw = QLineEdit()
        self._new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("New Password"), self._new_pw)

        self._confirm_pw = QLineEdit()
        self._confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("Confirm New Password"), self._confirm_pw)

        layout.addLayout(form)

        update_btn = QPushButton(tr("Update Password"))
        update_btn.setMaximumWidth(200)
        update_btn.clicked.connect(self._change_password)
        layout.addWidget(update_btn)

        self._pw_status = QLabel("")
        self._pw_status.setObjectName("muted")
        self._pw_status.setWordWrap(True)
        layout.addWidget(self._pw_status)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)

        rc_title = QLabel(tr("Recovery Codes"))
        rc_title.setObjectName("subheading")
        layout.addWidget(rc_title)

        rc_help = QLabel(tr(
            "Recovery codes let you reset your password if you forget it. "
            "Each code works once — store them somewhere safe."
        ))
        rc_help.setObjectName("muted")
        rc_help.setWordWrap(True)
        layout.addWidget(rc_help)

        self._rc_status = QLabel("")
        self._rc_status.setWordWrap(True)
        layout.addWidget(self._rc_status)

        rc_btn = QPushButton(tr("Generate Recovery Codes"))
        rc_btn.setMaximumWidth(240)
        rc_btn.clicked.connect(self._generate_recovery_codes)
        layout.addWidget(rc_btn)

        self._refresh_recovery_status()

        layout.addStretch()
        return w

    def _refresh_recovery_status(self) -> None:
        n = AuthService(self._db).recovery_codes_remaining(self._user["id"])
        if n:
            self._rc_status.setText(tr("You have {n} unused recovery code(s).").format(n=n))
        else:
            self._rc_status.setText(
                tr("No recovery codes yet — generate some and store them somewhere safe.")
            )

    def _generate_recovery_codes(self) -> None:
        auth = AuthService(self._db)
        if auth.recovery_codes_remaining(self._user["id"]) > 0:
            answer = QMessageBox.question(
                self, tr("Recovery Codes"),
                tr("Generating new codes replaces your existing ones — "
                   "old codes will stop working. Continue?"),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        codes = auth.generate_recovery_codes(self._user["id"])
        self._refresh_recovery_status()
        RecoveryCodesDialog(codes, self).exec()

    def _change_password(self) -> None:
        current = self._current_pw.text()
        new     = self._new_pw.text()
        confirm = self._confirm_pw.text()

        if not current or not new or not confirm:
            self._pw_status.setText(tr("All fields are required."))
            return
        if new != confirm:
            self._pw_status.setText(tr("New passwords do not match."))
            return

        ok, msg = AuthService(self._db).change_password(self._user["id"], current, new)
        if ok:
            self._current_pw.clear()
            self._new_pw.clear()
            self._confirm_pw.clear()
            self._pw_status.setText("")
            QMessageBox.information(self, tr("Password"), tr(msg))
        else:
            self._pw_status.setText(tr(msg))

    # ── Categories ─────────────────────────────────────────────────────────────

    def _build_categories_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(tr("+ Add Category"))
        add_btn.clicked.connect(self._add_category)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._cat_table = QTableWidget()
        self._cat_table.setColumnCount(3)
        self._cat_table.setHorizontalHeaderLabels([tr("Name"), tr("Type"), tr("Color")])
        self._cat_table.setAlternatingRowColors(True)
        self._cat_table.verticalHeader().setVisible(False)
        self._cat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hdr = self._cat_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setMinimumSectionSize(60)
        self._cat_table.doubleClicked.connect(self._edit_category)
        enable_sorting(self._cat_table, 0, Qt.SortOrder.AscendingOrder)
        layout.addWidget(self._cat_table)

        del_btn = QPushButton(tr("🗑 Delete Selected"))
        del_btn.setObjectName("danger")
        del_btn.setMaximumWidth(180)
        del_btn.clicked.connect(self._delete_category)
        layout.addWidget(del_btn)

        self._refresh_categories()
        return w

    def _refresh_categories(self) -> None:
        cats = self._db.get_categories()
        self._cat_table.setSortingEnabled(False)
        self._cat_table.setRowCount(len(cats))
        for r, c in enumerate(cats):
            items = [c["name"], tr(c["type"]), c["color"]]
            for col, text in enumerate(items):
                item = SortableItem(text)
                item.setData(Qt.ItemDataRole.UserRole, c["id"])
                if col == 2:
                    item.setBackground(QColor(c["color"]))
                self._cat_table.setItem(r, col, item)

        self._cat_table.resizeColumnsToContents()
        self._cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._cat_table.setSortingEnabled(True)

    def _add_category(self) -> None:
        dlg = CategoryDialog(self._db, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_categories()
            self.data_changed.emit()

    def _edit_category(self) -> None:
        row = self._cat_table.currentRow()
        if row < 0:
            return
        cat_id = self._cat_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        cat = self._db.get_category(cat_id)
        if cat:
            dlg = CategoryDialog(self._db, category=cat, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._refresh_categories()
                self._cat_table.selectRow(row)
                self.data_changed.emit()

    def _delete_category(self) -> None:
        row = self._cat_table.currentRow()
        if row < 0:
            return
        cat_id = self._cat_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        name   = self._cat_table.item(row, 0).text()
        reply  = QMessageBox.question(
            self, tr("Delete Category"), tr("Delete category '{name}'?").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_category(cat_id)
            self._refresh_categories()
            new_row = min(row, self._cat_table.rowCount() - 1)
            if new_row >= 0:
                self._cat_table.selectRow(new_row)
            self.data_changed.emit()

    # ── Backup ─────────────────────────────────────────────────────────────────

    def _build_backup_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        btn_row = QHBoxLayout()
        bk_btn = QPushButton(tr("💾 Create Backup Now"))
        bk_btn.clicked.connect(self._create_backup)
        btn_row.addWidget(bk_btn)

        log_btn = QPushButton(tr("📝 Export Activity Log"))
        log_btn.setObjectName("secondary")
        log_btn.setToolTip(tr("Export a CSV of every change made in the app"))
        log_btn.clicked.connect(self._export_audit_log)
        btn_row.addWidget(log_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addWidget(QLabel(tr("Existing Backups (double-click to restore):")))

        self._backup_list = QListWidget()
        self._backup_list.doubleClicked.connect(self._restore_backup)
        layout.addWidget(self._backup_list)

        self._refresh_backup_list()
        return w

    def _refresh_backup_list(self) -> None:
        self._backup_list.clear()
        for b in self._backup.list_backups():
            item = QListWidgetItem(f"{b['name']}  ({b['size_kb']} KB)  —  {b['created']}")
            item.setData(Qt.ItemDataRole.UserRole, b["path"])
            self._backup_list.addItem(item)

    def _create_backup(self) -> None:
        path = self._backup.create_backup("manual")
        QMessageBox.information(self, tr("Backup Created"), tr("Saved to:\n{path}").format(path=path))

    def _export_audit_log(self) -> None:
        default = f"activity_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export Activity Log"), default, "CSV Files (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            count = self._ie.export_audit_log_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, tr("Export Failed"), str(exc))
            return
        QMessageBox.information(
            self, tr("Export"),
            tr("Exported {n} log entries to:\n{path}").format(n=count, path=path),
        )
        self._refresh_backup_list()

    def _restore_backup(self) -> None:
        item = self._backup_list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, tr("Restore Backup"),
            tr("Restoring will overwrite your current data.\nProceed?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = self._backup.restore_backup(path)
            if ok:
                QMessageBox.information(self, tr("Restored"), tr("Backup restored. Please restart the application."))
            else:
                QMessageBox.critical(self, tr("Failed"), tr("Could not restore backup."))

    # ── Import ─────────────────────────────────────────────────────────────────

    def _build_import_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        layout.addWidget(QLabel(tr("Import transactions from a CSV or Excel file.")))
        layout.addWidget(QLabel(tr("Required columns: date, description, amount\nOptional: category, account, notes")))

        btn_row = QHBoxLayout()
        csv_btn = QPushButton(tr("📥 Import CSV"))
        csv_btn.clicked.connect(self._import_csv)
        btn_row.addWidget(csv_btn)

        xlsx_btn = QPushButton(tr("📥 Import Excel"))
        xlsx_btn.setObjectName("secondary")
        xlsx_btn.clicked.connect(self._import_xlsx)
        btn_row.addWidget(xlsx_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._import_result = QLabel()
        self._import_result.setObjectName("muted")
        layout.addWidget(self._import_result)
        layout.addStretch()
        return w

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Import CSV"), "", "CSV Files (*.csv)")
        if path:
            count, errors = self._ie.import_csv(self._user["id"], path)
            self._import_result.setText(
                tr("Imported {n} transactions.").format(n=count) +
                (tr(" {n} errors.").format(n=len(errors)) if errors else "")
            )
            if errors:
                QMessageBox.warning(self, tr("Import Errors"), "\n".join(errors[:10]))
            self.data_changed.emit()

    def _import_xlsx(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Import Excel"), "", "Excel Files (*.xlsx)")
        if path:
            count, errors = self._ie.import_excel(self._user["id"], path)
            self._import_result.setText(
                tr("Imported {n} transactions.").format(n=count) +
                (tr(" {n} errors.").format(n=len(errors)) if errors else "")
            )
            self.data_changed.emit()

    # ── About / Updates ──────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("💰 Budget Manager")
        title.setObjectName("subheading")
        layout.addWidget(title)

        ver = QLabel(tr("Version {v}").format(v=__version__))
        ver.setObjectName("muted")
        layout.addWidget(ver)

        row = QHBoxLayout()
        self._update_btn = QPushButton(tr("Check for updates"))
        self._update_btn.setObjectName("secondary")
        self._update_btn.setMaximumWidth(220)
        self._update_btn.clicked.connect(self._check_for_updates)
        row.addWidget(self._update_btn)

        # Hidden until a check finds an installable update on a packaged build.
        self._update_now_btn = QPushButton(tr("⤓ Update now"))
        self._update_now_btn.setMaximumWidth(220)
        self._update_now_btn.setVisible(False)
        self._update_now_btn.clicked.connect(self._update_now)
        row.addWidget(self._update_now_btn)
        row.addStretch()
        layout.addLayout(row)

        self._update_status = QLabel("")
        self._update_status.setObjectName("muted")
        self._update_status.setTextFormat(Qt.TextFormat.RichText)
        self._update_status.setOpenExternalLinks(True)
        self._update_status.setWordWrap(True)
        layout.addWidget(self._update_status)

        self._update_progress = QProgressBar()
        self._update_progress.setVisible(False)
        self._update_progress.setMaximumWidth(320)
        layout.addWidget(self._update_progress)

        # Latest UpdateInfo from the most recent check (installer URL/size, etc.).
        self._update_info = None

        layout.addStretch()
        return w

    def _check_for_updates(self) -> None:
        self._update_btn.setEnabled(False)
        self._update_now_btn.setVisible(False)
        self._update_progress.setVisible(False)
        self._update_status.setText(tr("Checking…"))
        worker = UpdateCheckWorker(__version__)
        worker.signals.done.connect(self._on_update_checked)
        QThreadPool.globalInstance().start(worker)

    def _on_update_checked(self, info) -> None:
        self._update_btn.setEnabled(True)
        self._update_now_btn.setVisible(False)   # re-shown below only if installable
        self._update_info = info
        if getattr(info, "available", False) and info.latest:
            # One-click update only for the installed build with a real asset;
            # everything else falls back to the plain download link.
            if can_auto_update() and getattr(info, "installer_url", None):
                self._update_status.setText(
                    tr("Update available: {v}").format(v=info.latest)
                )
                self._update_now_btn.setVisible(True)
            else:
                self._update_status.setText(
                    tr("Update available: {v}").format(v=info.latest)
                    + f'&nbsp;&nbsp;<a href="{info.url}">' + tr("Download") + "</a>"
                )
        elif getattr(info, "error", ""):
            self._update_status.setText(tr("Could not check for updates."))
        else:
            self._update_status.setText(tr("You're on the latest version."))

    # ── One-click update (download → silent install → relaunch) ──────────────

    def _update_now(self) -> None:
        info = self._update_info
        if not info or not getattr(info, "installer_url", None):
            return
        size_mb = (info.installer_size / 1_048_576) if info.installer_size else 0
        size_hint = tr(" (~{mb:.0f} MB)").format(mb=size_mb) if size_mb else ""
        reply = QMessageBox.question(
            self, tr("Update now"),
            tr("This will download version {v}{size}, then close and reinstall "
               "Budget Manager automatically. Your data is not affected.\n\n"
               "Continue?").format(v=info.latest, size=size_hint),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._update_now_btn.setEnabled(False)
        self._update_btn.setEnabled(False)
        self._update_progress.setRange(0, 100)
        self._update_progress.setValue(0)
        self._update_progress.setVisible(True)
        self._update_status.setText(tr("Downloading update…"))

        dest = os.path.join(
            tempfile.gettempdir(), f"BudgetManagerSetup_{info.latest}.exe"
        )
        worker = UpdateDownloadWorker(info.installer_url, dest)
        worker.signals.progress.connect(self._on_download_progress)
        worker.signals.done.connect(self._on_download_done)
        worker.signals.error.connect(self._on_download_error)
        QThreadPool.globalInstance().start(worker)

    def _on_download_progress(self, done: int, total: int) -> None:
        if total > 0:
            self._update_progress.setRange(0, 100)
            self._update_progress.setValue(int(done / total * 100))
        else:
            # Unknown length — show an indeterminate/busy bar.
            self._update_progress.setRange(0, 0)

    def _on_download_error(self, message: str) -> None:
        self._update_progress.setVisible(False)
        self._update_now_btn.setEnabled(True)
        self._update_btn.setEnabled(True)
        self._update_status.setText(tr("Download failed. Please try again."))
        QMessageBox.critical(self, tr("Update failed"), message)

    def _on_download_done(self, installer_path: str) -> None:
        self._update_progress.setRange(0, 100)
        self._update_progress.setValue(100)
        self._update_status.setText(tr("Installing update…"))
        try:
            launch_installer(installer_path)
        except Exception as exc:
            self._on_download_error(str(exc))
            return
        # Close every window (persisting state via closeEvent), then quit so the
        # installer can replace the files and relaunch the new version.
        app = QApplication.instance()
        if app is not None:
            for w in app.topLevelWidgets():
                w.close()
            app.quit()