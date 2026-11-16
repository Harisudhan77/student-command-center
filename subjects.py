"""📚 Subjects page - manage subjects and see how each one is going."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

import store
from ui_theme import (ACCENT, BG, BODY, BORDER, DEEP, FAINT, MUTED, TEXT,
                      button, empty_note, label, line_edit, page_header,
                      page_style, small_label, title_label)


class SubjectsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("subjectsPage")
        self.setStyleSheet(page_style("subjectsPage"))
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(14)

        root.addWidget(page_header("Subjects", "Your subjects, and how much work each one has left."))

        add_row = QHBoxLayout()
        self.name_input = line_edit("New subject…  e.g. Physics")
        add_btn = button("Add subject", "primary")
        add_btn.clicked.connect(self._add_subject)
        add_row.addWidget(self.name_input, 1)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)

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

    def _add_subject(self) -> None:
        if store.add_subject(self.name_input.text()):
            self.name_input.clear()
        self.refresh()

    def _delete(self, name: str) -> None:
        store.delete_subject(name)
        self.refresh()

    # -------------------------------------------------------------- refresh
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        subjects = [s["name"] for s in store.list_subjects()]
        progress = {row["subject"]: row for row in store.subject_progress()}
        exams = store.list_exams(only_upcoming=True)
        next_exam_by_subject: dict[str, str] = {}
        for exam in exams:
            next_exam_by_subject.setdefault(exam["subject"], exam["occurs_at"])

        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # subjects that only exist via tasks/exams still show up
        for subject in sorted(set(subjects) | set(progress) | set(next_exam_by_subject)):
            stats = progress.get(subject, {"pending": 0, "done": 0})
            pending, done = stats["pending"] or 0, stats["done"] or 0
            total = pending + done

            card_ = QWidget()
            card_.setStyleSheet(
                f"background-color: {DEEP}; border: 1px solid {BORDER}; border-radius: 12px;"
            )
            row = QHBoxLayout(card_)
            row.setContentsMargins(16, 12, 16, 12)
            row.setSpacing(14)

            info = QVBoxLayout()
            info.setSpacing(3)
            name_row = QHBoxLayout()
            name_row.addWidget(label(subject or "(no subject)", 16, TEXT, bold=True))
            if subject in next_exam_by_subject:
                exam_date = next_exam_by_subject[subject][:10]
                name_row.addWidget(small_label(f"exam {exam_date}", "#A78BFA"))
            name_row.addStretch()
            info.addLayout(name_row)

            bar_text = f"{done} done · {pending} pending" if total else "No tasks yet"
            info.addWidget(small_label(bar_text, FAINT if not total else MUTED))
            row.addLayout(info, 1)

            delete_btn = QPushButton("✕")
            delete_btn.setFixedSize(26, 26)
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet(
                f"QPushButton {{ color: {MUTED}; background: transparent; border: none; }}"
                "QPushButton:hover { color: #FCA5A5; }"
            )
            delete_btn.clicked.connect(lambda _=False, n=subject: self._delete(n))
            row.addWidget(delete_btn)

            self.list_layout.insertWidget(self.list_layout.count() - 1, card_)

        if not (subjects or progress or next_exam_by_subject):
            self.list_layout.insertWidget(0, empty_note(
                "No subjects yet. Add one above — tasks and exams will group themselves under it."))