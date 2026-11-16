"""🎯 Exams page - add, see countdowns and delete exams."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import store
from ui_theme import (ACCENT, BG, BODY, BORDER, DEEP, FAINT, MUTED, TEXT,
                      button, empty_note, label, page_header, page_style,
                      small_label, title_label)


class ExamsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("examsPage")
        self.setStyleSheet(page_style("examsPage"))
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(14)

        root.addWidget(page_header("Exams", "Every exam, with a live countdown."))

        add_card = QWidget()
        add_card.setStyleSheet(f"background-color: {DEEP}; border: 1px solid {BORDER}; border-radius: 12px;")
        add_row = QHBoxLayout(add_card)
        add_row.setContentsMargins(14, 12, 14, 12)
        add_row.setSpacing(10)

        self.subject_input = QComboBox()
        self.subject_input.setEditable(True)
        self.subject_input.setFixedHeight(34)
        self.subject_input.setStyleSheet(
            f"QComboBox {{ background-color: #1D2130; color: {BODY}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 0 10px; font-size: 13px; }}"
            f"QComboBox QAbstractItemView {{ background-color: {DEEP}; color: {BODY}; }}"
        )
        self.subject_input.lineEdit().setPlaceholderText("Subject…  e.g. Physics")

        self.when_input = QDateTimeEdit()
        self.when_input.setCalendarPopup(True)
        self.when_input.setDisplayFormat("dd MMM yyyy  hh:mm AP")
        self.when_input.setDateTime(QDateTime.currentDateTime())
        self.when_input.setFixedHeight(34)
        self.when_input.setStyleSheet(
            f"QDateTimeEdit {{ background-color: #1D2130; color: {BODY}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 0 10px; font-size: 13px; }}"
        )

        add_btn = button("Add exam", "primary")
        add_btn.clicked.connect(self._add_exam)
        add_row.addWidget(self.subject_input, 1)
        add_row.addWidget(self.when_input)
        add_row.addWidget(add_btn)
        root.addWidget(add_card)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_holder = QWidget()
        self.list_holder.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_holder)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_holder)
        root.addWidget(self.scroll, 1)

    def _add_exam(self) -> None:
        subject = self.subject_input.currentText().strip()
        if not subject:
            return
        iso = self.when_input.dateTime().toString("yyyy-MM-dd HH:mm")
        store.add_exam(subject, iso)
        store.add_subject(subject)
        self.subject_input.setCurrentText("")
        self.refresh()

    def _delete(self, exam: dict) -> None:
        store.delete_exam(exam["id"])
        self.refresh()

    # -------------------------------------------------------------- refresh
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        self.subject_input.clear()
        self.subject_input.lineEdit().clear()
        self.subject_input.addItems([s["name"] for s in store.list_subjects()])

        exams = store.list_exams()
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not exams:
            self.list_layout.insertWidget(0, empty_note("No exams yet — add your first one above."))
            return

        now = datetime.now()
        for exam in exams:
            when = store.parse_dt(exam["occurs_at"])
            days_left = (when.date() - now.date()).days if when else 0
            if days_left < 0:
                countdown, color = "over", FAINT
            elif days_left == 0:
                countdown, color = "TODAY !", "#FCA5A5"
            elif days_left == 1:
                countdown, color = "tomorrow", "#FBBF24"
            else:
                countdown, color = f"{days_left} days", "#A78BFA"

            row = QWidget()
            row.setStyleSheet(
                f"background-color: {DEEP}; border: 1px solid {BORDER}; border-radius: 12px;"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 12, 16, 12)
            row_layout.setSpacing(14)

            left = QVBoxLayout()
            left.setSpacing(3)
            left.addWidget(label(exam["subject"], 16, TEXT, bold=True))
            left.addWidget(small_label(
                when.strftime("%a · %d %b %Y · %I:%M %p") if when else exam["occurs_at"], MUTED))
            row_layout.addLayout(left, 1)

            countdown_label = label(countdown, 15, color, bold=True)
            row_layout.addWidget(countdown_label)

            delete_btn = QPushButton("✕")
            delete_btn.setFixedSize(26, 26)
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet(
                f"QPushButton {{ color: {MUTED}; background: transparent; border: none; }}"
                "QPushButton:hover { color: #FCA5A5; }"
            )
            delete_btn.clicked.connect(lambda _=False, e=exam: self._delete(e))
            row_layout.addWidget(delete_btn)

            self.list_layout.insertWidget(self.list_layout.count() - 1, row)