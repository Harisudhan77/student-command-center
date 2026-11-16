"""⚙️ Settings page - your name, daily goal, and the danger zone."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QSpinBox, QVBoxLayout, QWidget

import store
from web.ai_core import PRIMARY_MODEL
from ui_theme import (BG, MUTED, TEXT, button, label, line_edit, page_header,
                      page_style, small_label, title_label)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.setStyleSheet(page_style("settingsPage"))
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(16)

        root.addWidget(page_header("Settings", "Make the app yours."))

        # profile card
        profile, profile_layout = _plain_card()
        profile_layout.addWidget(title_label("Profile"))
        self.name_input = line_edit("Your name")
        profile_layout.addWidget(self.name_input)
        save_row = QHBoxLayout()
        self.saved_note = small_label("")
        save_btn = button("Save", "primary")
        save_btn.clicked.connect(self._save)
        save_row.addStretch()
        save_row.addWidget(self.saved_note)
        save_row.addWidget(save_btn)
        profile_layout.addLayout(save_row)
        root.addWidget(profile)

        # study habits card
        habits, habits_layout = _plain_card()
        habits_layout.addWidget(title_label("Study habits"))
        goal_row = QHBoxLayout()
        goal_row.addWidget(label("Daily study goal", 13))
        goal_row.addStretch()
        self.goal_input = QSpinBox()
        self.goal_input.setRange(15, 720)
        self.goal_input.setSingleStep(15)
        self.goal_input.setSuffix(" min/day")
        self.goal_input.setFixedHeight(32)
        self.goal_input.setStyleSheet(
            "QSpinBox { background-color: #0B1220; color: #CBD5E1; border: 1px solid #2B3A52; "
            "border-radius: 8px; padding: 0 10px; }"
        )
        goal_row.addWidget(self.goal_input)
        habits_layout.addLayout(goal_row)
        habits_layout.addWidget(small_label(
            "Used as the default 'study time per day' when the AI builds a plan."))
        root.addWidget(habits)

        # AI card
        ai_card, ai_layout = _plain_card()
        ai_layout.addWidget(title_label("AI"))
        ai_layout.addWidget(label(f"Model: {PRIMARY_MODEL} (via Groq)", 13))
        ai_layout.addWidget(small_label(
            "Falls back to gpt-oss-20b automatically if the big model is unavailable. "
            "Change it with STUDY_BUDDY_MODEL in .env."))
        root.addWidget(ai_card)

        # danger zone
        danger, danger_layout = _plain_card()
        danger_layout.addWidget(title_label("Danger zone"))
        danger_layout.addWidget(small_label(
            "Deletes every task, exam, subject, plan and setting. There is no undo."))
        reset_btn = button("Delete all data", "danger")
        reset_btn.clicked.connect(self._reset)
        danger_layout.addWidget(reset_btn)
        root.addWidget(danger)
        root.addStretch()

    def _save(self) -> None:
        name = self.name_input.text().strip() or "Student"
        store.set_setting("student_name", name)
        store.set_setting("daily_goal_minutes", str(self.goal_input.value()))
        self.saved_note.setText("Saved ✓")

    def _reset(self) -> None:
        answer = QMessageBox.warning(
            self, "Delete everything",
            "This permanently deletes all tasks, exams, subjects and plans.\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            store.reset_all()
            self.refresh()

    # -------------------------------------------------------------- refresh
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        self.name_input.setText(store.get_setting("student_name", "Student"))
        self.goal_input.setValue(int(store.get_setting("daily_goal_minutes", "120") or 120))
        self.saved_note.setText("")


def _plain_card():
    from ui_theme import CARD, BORDER
    from PySide6.QtWidgets import QFrame, QVBoxLayout
    frame = QFrame()
    frame.setStyleSheet(f"background-color: {CARD}; border: 1px solid {BORDER}; border-radius: 14px;")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(10)
    return frame, layout