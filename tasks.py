"""📋 Tasks page - add, complete and delete tasks."""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import store
from ui_theme import (ACCENT, BG, BODY, BORDER, DEEP, FAINT, MUTED, TEXT,
                      button, empty_note, label, line_edit, page_header,
                      page_style)


class TasksPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tasksPage")
        self.setStyleSheet(page_style("tasksPage"))
        self.filter = "pending"
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(14)

        root.addWidget(page_header("Tasks", "Everything you need to get done, in one list."))

        # add-task row
        add_row = QHBoxLayout()
        self.title_input = line_edit("New task…  e.g. Finish physics chapter 4")
        self.due_input = QDateEdit()
        self.due_input.setCalendarPopup(True)
        self.due_input.setDisplayFormat("dd MMM yyyy")
        self.due_input.setDate(QDate.currentDate())
        self.due_input.setFixedHeight(34)
        self.due_input.setStyleSheet(
            f"QDateEdit {{ background-color: {DEEP}; color: {BODY}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 0 10px; font-size: 13px; }}"
        )
        add_btn = button("Add task", "primary")
        add_btn.clicked.connect(self._add_task)
        add_row.addWidget(self.title_input, 1)
        add_row.addWidget(self.due_input)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)

        # filter chips
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.filter_group = QButtonGroup(self)
        for key, text in (("all", "All"), ("pending", "Pending"), ("done", "Done")):
            chip = button(text, height=30)
            chip.setCheckable(True)
            chip.setChecked(key == self.filter)
            chip.clicked.connect(lambda _=False, k=key, c=chip: self._set_filter(k, c))
            self.filter_group.addButton(chip)
            filters.addWidget(chip)
        filters.addStretch()
        self.count_label = label("", 12, FAINT)
        filters.addWidget(self.count_label)
        root.addLayout(filters)

        # task list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_holder = QWidget()
        self.list_holder.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_holder)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_holder)
        root.addWidget(self.scroll, 1)

    def _set_filter(self, key: str, chip: QPushButton) -> None:
        self.filter = key
        self.refresh()

    def _add_task(self) -> None:
        title = self.title_input.text().strip()
        if not title:
            return
        due = self.due_input.date().toString("yyyy-MM-dd") + " 23:59"
        store.add_task(title, due_at=due)
        self.title_input.clear()
        self.refresh()

    def _toggle(self, task: dict, checked: bool) -> None:
        store.set_task_done(task["id"], checked)
        self.refresh()

    def _delete(self, task: dict) -> None:
        store.delete_task(task["id"])
        self.refresh()

    # -------------------------------------------------------------- refresh
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        tasks = store.list_tasks(include_done=True)
        if self.filter == "pending":
            shown = [t for t in tasks if not t["done"]]
        elif self.filter == "done":
            shown = [t for t in tasks if t["done"]]
        else:
            shown = tasks
        self.count_label.setText(f"{len(shown)} shown · {len(tasks)} total")

        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not shown:
            self.list_layout.insertWidget(0, empty_note("Nothing here yet — add a task above."))
            return

        today_iso = store.today().isoformat()
        for task in shown:
            row = QWidget()
            row.setStyleSheet(
                f"background-color: {DEEP}; border: 1px solid {BORDER}; border-radius: 10px;"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)

            checkbox = QCheckBox()
            checkbox.setChecked(bool(task["done"]))
            checkbox.setCursor(Qt.PointingHandCursor)
            checkbox.setStyleSheet(
                "QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #94A3B8; "
                "border-radius: 9px; background: transparent; }"
                f"QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT}; }}"
            )
            checkbox.toggled.connect(lambda checked, t=task: self._toggle(t, checked))
            row_layout.addWidget(checkbox)

            title_text = task["title"]
            title_label_ = label(title_text, 14, MUTED if task["done"] else TEXT)
            if task["done"]:
                font = title_label_.font()
                font.setStrikeOut(True)
                title_label_.setFont(font)
            title_label_.setWordWrap(True)
            row_layout.addWidget(title_label_, 1)

            tags = []
            if task["subject"]:
                tags.append(task["subject"])
            if task["due_at"]:
                day = task["due_at"][:10]
                tags.append("Today" if day == today_iso else day)
            if task["created_by"] == "ai":
                tags.append("🤖 plan")
            tag_label = label("  ·  ".join(tags), 11, FAINT)
            tag_label.setStyleSheet(f"color: {FAINT}; font-size: 11px; background: transparent;")
            row_layout.addWidget(tag_label)

            delete_btn = QPushButton("✕")
            delete_btn.setFixedSize(26, 26)
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet(
                f"QPushButton {{ color: {MUTED}; background: transparent; border: none; font-size: 12px; }}"
                "QPushButton:hover { color: #FCA5A5; }"
            )
            delete_btn.clicked.connect(lambda _=False, t=task: self._delete(t))
            row_layout.addWidget(delete_btn)

            self.list_layout.insertWidget(self.list_layout.count() - 1, row)