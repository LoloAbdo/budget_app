"""
views/goals_view.py
Financial goals panel with progress cards.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit,
    QScrollArea, QFrame, QMessageBox, QGridLayout,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from database import DatabaseManager
from views.widgets import GoalProgressCard
from views.i18n import tr


class GoalDialog(QDialog):
    """Add / edit a financial goal."""

    def __init__(
        self,
        db: DatabaseManager,
        user_id: int,
        goal: Optional[dict] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._user_id = user_id
        self._goal = goal
        self.setWindowTitle(tr("Edit Goal") if goal else tr("Add Goal"))
        self.setMinimumWidth(400)
        self._build_ui()
        if goal:
            self._populate(goal)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(tr("e.g. Emergency Fund"))
        form.addRow(tr("Goal Name"), self._name_edit)

        self._target_spin = QDoubleSpinBox()
        self._target_spin.setRange(0, 10_000_000)
        self._target_spin.setDecimals(2)
        self._target_spin.setPrefix("$ ")
        form.addRow(tr("Target Amount"), self._target_spin)

        self._current_spin = QDoubleSpinBox()
        self._current_spin.setRange(0, 10_000_000)
        self._current_spin.setDecimals(2)
        self._current_spin.setPrefix("$ ")
        form.addRow(tr("Current Saved"), self._current_spin)

        self._date_edit = QDateEdit(QDate.currentDate().addYears(1))
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow(tr("Target Date"), self._date_edit)

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

    def _populate(self, goal: dict) -> None:
        self._name_edit.setText(goal["goal_name"])
        self._target_spin.setValue(goal["target_amount"])
        self._current_spin.setValue(goal["current_amount"])
        self._date_edit.setDate(QDate.fromString(goal["target_date"], "yyyy-MM-dd"))

    def _save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("Validation"), tr("Goal name is required."))
            return
        try:
            target  = self._target_spin.value()
            current = self._current_spin.value()
            date_s  = self._date_edit.date().toString("yyyy-MM-dd")

            if self._goal:
                self._db.update_goal(self._goal["id"], name, target, current, date_s)
            else:
                self._db.create_goal(self._user_id, name, target, current, date_s)
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, tr("Error"), tr("Could not save goal:\n{err}").format(err=exc))
            return
        self.accept()


class GoalsView(QWidget):
    """Goals management panel."""

    def __init__(self, db: DatabaseManager, user: dict, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._user = user
        self._currency = user.get("currency", "CAD")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        head_row = QHBoxLayout()
        title = QLabel(tr("Financial Goals"))
        title.setObjectName("heading")
        head_row.addWidget(title)
        head_row.addStretch()

        add_btn = QPushButton(tr("+ Add Goal"))
        add_btn.clicked.connect(self._add_goal)
        head_row.addWidget(add_btn)
        layout.addLayout(head_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._grid = QGridLayout(self._content)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(14)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

    def refresh(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        goals = self._db.get_goals(self._user["id"])
        if not goals:
            no_lbl = QLabel(tr("No goals yet.\nClick '+ Add Goal' to set your first financial target."))
            no_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_lbl.setObjectName("muted")
            self._grid.addWidget(no_lbl, 0, 0)
            return

        for i, g in enumerate(goals):
            card = GoalProgressCard(g, self._currency)
            # Buttons
            btn_row = QHBoxLayout()
            edit_btn = QPushButton(tr("Edit"))
            edit_btn.setObjectName("secondary")
            edit_btn.clicked.connect(lambda _, goal=g: self._edit_goal(goal))
            del_btn = QPushButton(tr("Delete"))
            del_btn.setObjectName("danger")
            del_btn.clicked.connect(lambda _, goal=g: self._delete_goal(goal))
            btn_layout = QVBoxLayout()
            btn_layout.addWidget(card)
            row_w = QWidget()
            row_w.setLayout(btn_layout)
            # Inline edit / delete inside the card
            inner_row = QHBoxLayout()
            inner_row.addWidget(edit_btn)
            inner_row.addWidget(del_btn)
            inner_row.addStretch()
            btn_layout.addLayout(inner_row)

            self._grid.addWidget(row_w, i // 2, i % 2)

        # fill remaining column if odd
        if len(goals) % 2 == 1:
            self._grid.setColumnStretch(1, 1)

    def _add_goal(self) -> None:
        dlg = GoalDialog(self._db, self._user["id"], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_goal(self, goal: dict) -> None:
        dlg = GoalDialog(self._db, self._user["id"], goal=goal, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _delete_goal(self, goal: dict) -> None:
        reply = QMessageBox.question(
            self, tr("Delete Goal"),
            tr("Delete goal '{name}'?").format(name=goal['goal_name']),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_goal(goal["id"])
            self.refresh()