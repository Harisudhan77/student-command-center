"""📊 Dashboard page - overview cards fed by store.py (was inline in main.py)."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QFormLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import store
from ui_theme import (ACCENT, ACCENT_HOVER, BG, BODY, BORDER, CARD, DEEP, MUTED,
                      TEXT, WEEKDAYS, card, empty_note, label, page_header, page_style,
                      small_label, title_label, v_bar)


class _AddDialog(QDialog):
    """Small modal for adding an exam or a task (kept from the original app)."""

    def __init__(self, parent, kind: str):
        super().__init__(parent)
        self.kind = kind
        self.setWindowTitle(f"Add new {kind}")
        self.setFixedSize(360, 260)

        layout = QVBoxLayout(self)
        layout.setStyleSheet(f"background-color: {CARD};")
        form = QFormLayout()

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText(f"Enter the {kind} name")

        self.datetime_input = QDateTimeEdit()
        self.datetime_input.setCalendarPopup(True)
        self.datetime_input.setDateTime(QDateTime.currentDateTime())

        form.addRow("Subject:" if kind == "exam" else "Task:", self.text_input)
        form.addRow("Deadline:" if kind == "task" else "Exam date & time:", self.datetime_input)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        for b in (save_btn, cancel_btn):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton {{ color: {'white' if b is save_btn else BODY}; "
                f"background-color: {'#6D5AE6' if b is save_btn else 'transparent'}; "
                f"border: {'none' if b is save_btn else f'1px solid {BORDER}'}; "
                f"border-radius: 8px; padding: 6px 14px; }}"
            )
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)

    def _save(self) -> None:
        text = self.text_input.text().strip()
        if not text:
            return
        iso = self.datetime_input.dateTime().toString("yyyy-MM-dd HH:mm")
        if self.kind == "exam":
            store.add_exam(text, iso)
        else:
            store.add_task(text, due_at=iso)
        self.accept()


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardPage")
        self.setStyleSheet(page_style("dashboardPage"))
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(16)

        root.addWidget(label("STUDENT COMMAND CENTRE", 10, "#DDA0DD"))
        self.welcome = label("Welcome Back ! 👋", 28, TEXT, bold=True)
        root.addWidget(self.welcome)
        root.addWidget(label("Let's make today productive !", 15, MUTED))

        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)

        # --- upcoming exams card
        exam_frame, exam_layout = card("examCard")
        exam_frame.setMinimumHeight(170)
        header = QHBoxLayout()
        header.addWidget(label("UPCOMING EXAMS !", 12, MUTED, bold=True))
        header.addStretch()
        exam_layout.addLayout(header)

        self.exam_no = label("0", 40, TEXT, bold=True)
        self.exam_subtitle = small_label("No pending exams")
        exam_layout.addWidget(self.exam_no)
        exam_layout.addWidget(self.exam_subtitle)
        cards_row.addWidget(exam_frame)

        # --- tasks completed card
        tasks_frame, tasks_layout = card("tasksCard")
        tasks_frame.setMinimumHeight(170)
        tasks_header = QHBoxLayout()
        tasks_header.addWidget(label("TASKS COMPLETED", 12, MUTED, bold=True))
        tasks_header.addStretch()
        tasks_layout.addLayout(tasks_header)

        self.tasks_count = label("0", 40, TEXT, bold=True)
        self.tasks_subtitle = small_label("No tasks completed")
        tasks_layout.addWidget(self.tasks_count)
        tasks_layout.addWidget(self.tasks_subtitle)
        cards_row.addWidget(tasks_frame)
        root.addLayout(cards_row)

        # --- pending tasks card
        pending_frame, pending_layout = card()
        pending_frame.setFixedHeight(230)
        pending_layout.addWidget(title_label("PENDING TASKS"))
        self.pending_list = QVBoxLayout()
        self.pending_list.setSpacing(10)
        pending_layout.addLayout(self.pending_list)
        pending_layout.addStretch()
        root.addWidget(pending_frame)

        # --- exam reminder card
        reminder_frame, reminder_layout = card()
        reminder_frame.setFixedHeight(170)
        reminder_layout.addWidget(title_label("EXAM REMINDER"))
        self.reminder_subject = label("No upcoming exams", 22, TEXT, bold=True)
        self.reminder_date = small_label("Add an exam to see its date here")
        self.reminder_countdown = label("Your next exam will appear here", 14, "#A78BFA", bold=True)
        reminder_layout.addWidget(self.reminder_subject)
        reminder_layout.addWidget(self.reminder_date)
        reminder_layout.addWidget(self.reminder_countdown)
        root.addWidget(reminder_frame)

        # --- weekly progress card
        weekly_frame, weekly_layout = card()
        weekly_frame.setFixedHeight(210)
        weekly_layout.addWidget(title_label("WEEKLY PROGRESS"))
        self.chart_layout = QHBoxLayout()
        self.chart_layout.setSpacing(14)
        self.bars: list[QProgressBar] = []
        self.day_labels: list[QLabel] = []
        for day in WEEKDAYS:
            column = QVBoxLayout()
            bar = v_bar(0)
            day_label = small_label(day, MUTED)
            day_label.setAlignment(Qt.AlignHCenter)
            column.addWidget(bar, alignment=Qt.AlignHCenter)
            column.addWidget(day_label, alignment=Qt.AlignHCenter)
            self.chart_layout.addLayout(column)
            self.bars.append(bar)
            self.day_labels.append(day_label)
        self.chart_layout.addStretch()
        weekly_layout.addLayout(self.chart_layout)
        root.addWidget(weekly_frame)
        root.addStretch()

    def _open_add(self, kind: str) -> None:
        dialog = _AddDialog(self, kind)
        if dialog.exec():
            self.refresh()

    # -------------------------------------------------------------- refresh
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        name = store.get_setting("student_name", "Student")
        self.welcome.setText(f"Welcome Back, {name}! 👋")

        exams = store.list_exams(only_upcoming=True)
        self.exam_no.setText(str(len(exams)))
        self.exam_subtitle.setText(f"Next: {exams[0]['subject']}" if exams else "No pending exams")

        self.tasks_count.setText(str(store.count_tasks(done=True)))
        pending_count = store.count_tasks(done=False)
        self.tasks_subtitle.setText(f"{pending_count} pending" if pending_count else "You're all caught up!")

        # pending tasks (top 3 by due date)
        while self.pending_list.count():
            item = self.pending_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pending = store.list_tasks(include_done=False)[:3]
        if not pending:
            self.pending_list.addWidget(empty_note("No pending tasks. You're all caught up!"))
        for task in pending:
            checkbox = QCheckBox(self._task_label(task))
            checkbox.setCursor(Qt.PointingHandCursor)
            checkbox.setStyleSheet(
                f"QCheckBox {{ color: {BODY}; font-size: 14px; spacing: 10px; background: transparent; }}"
                "QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #94A3B8; "
                "border-radius: 9px; background: transparent; }"
                f"QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT}; }}"
            )
            checkbox.toggled.connect(lambda checked, t=task: self._complete(t, checked))
            self.pending_list.addWidget(checkbox)

        # exam reminder
        nxt = store.next_exam()
        if nxt:
            when = store.parse_dt(nxt["occurs_at"])
            self.reminder_subject.setText(nxt["subject"])
            self.reminder_date.setText(when.strftime("%d %m %Y | %I:%M %p") if when else nxt["occurs_at"])
            days_left = (when.date() - datetime.now().date()).days if when else 0
            if days_left <= 0:
                self.reminder_countdown.setText("Your exam is today !")
            elif days_left == 1:
                self.reminder_countdown.setText("Your exam is tomorrow !")
            else:
                self.reminder_countdown.setText(f"{days_left} days remaining")
        else:
            self.reminder_subject.setText("No upcoming exams")
            self.reminder_date.setText("Add an exam to see its date here")
            self.reminder_countdown.setText("Your next exam will appear here")

        # weekly bars
        counts = store.weekly_completed_counts()
        peak = max(counts) or 1
        today_index = datetime.now().weekday()
        for i, bar in enumerate(self.bars):
            bar.setValue(int(counts[i] / peak * 100))
            self.day_labels[i].setText("• " + WEEKDAYS[i] if i == today_index else WEEKDAYS[i])

    def _task_label(self, task: dict) -> str:
        text = task["title"]
        if task["due_at"]:
            text += f"   ·  {task['due_at']}"
        return text

    def _complete(self, task: dict, checked: bool) -> None:
        if checked:
            store.set_task_done(task["id"], True)
            self.refresh()