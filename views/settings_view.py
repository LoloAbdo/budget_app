"""
views/settings_view.py
Settings panel: theme toggle, categories, backup/restore, import.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QComboBox, QFileDialog, QMessageBox,
    QFrame, QTabWidget, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThreadPool
from PyQt6.QtGui import QColor, QFont

from database import DatabaseManager
from services.auth_service import AuthService
from services.backup_service import BackupService
from services.import_export_service import ImportExportService
from views.i18n import tr, set_language, get_language, LANGUAGES
from views.sortable import SortableItem, enable_sorting
from views.update_check import UpdateCheckWorker
from version import __version__


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
    theme_changed    = pyqtSignal(str)  # "dark" or "light"
    data_changed     = pyqtSignal()
    language_changed = pyqtSignal(str)  # "en" or "fr"

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
        # Display localized label, store the English value ("dark"/"light")
        self._theme_combo.addItem(tr("Dark"), "dark")
        self._theme_combo.addItem(tr("Light"), "light")
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

        layout.addStretch()
        return w

    def _apply_theme(self) -> None:
        t = self._theme_combo.currentData()
        self._theme = t
        self.theme_changed.emit(t)

    def _apply_language(self) -> None:
        code = self._lang_combo.currentData()
        if code != get_language():
            self.language_changed.emit(code)

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

        layout.addStretch()
        return w

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
        row.addStretch()
        layout.addLayout(row)

        self._update_status = QLabel("")
        self._update_status.setObjectName("muted")
        self._update_status.setTextFormat(Qt.TextFormat.RichText)
        self._update_status.setOpenExternalLinks(True)
        self._update_status.setWordWrap(True)
        layout.addWidget(self._update_status)

        layout.addStretch()
        return w

    def _check_for_updates(self) -> None:
        self._update_btn.setEnabled(False)
        self._update_status.setText(tr("Checking…"))
        worker = UpdateCheckWorker(__version__)
        worker.signals.done.connect(self._on_update_checked)
        QThreadPool.globalInstance().start(worker)

    def _on_update_checked(self, info) -> None:
        self._update_btn.setEnabled(True)
        if getattr(info, "available", False) and info.latest:
            self._update_status.setText(
                tr("Update available: {v}").format(v=info.latest)
                + f'&nbsp;&nbsp;<a href="{info.url}">' + tr("Download") + "</a>"
            )
        elif getattr(info, "error", ""):
            self._update_status.setText(tr("Could not check for updates."))
        else:
            self._update_status.setText(tr("You're on the latest version."))