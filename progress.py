"""📈 Progress page - streaks, weekly activity and per-subject progress."""

from __future__ import annotations

from datetime import timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import store
from ui_theme import (ACCENT, BG, DEEP, FAINT, MUTED, TEXT, WEEKDAYS, card,
                      empty_note, label, page_header, page_style,
                      small_label, title_label, v_bar)


class ProgressPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("progressPage")
        self.setStyleSheet(page_style("progressPage"))
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(16)

        root.addWidget(page_header("Progress", "Small steps, counted."))

        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)
        self.done_card, self.done_value = self._stat_card(stats_row, "TASKS COMPLETED")
        self.pending_card, self.pending_value = self._stat_card(stats_row, "PENDING")
        self.streak_card, self.streak_value = self._stat_card(stats_row, "STREAK")
        self.minutes_card, self.minutes_value = self._stat_card(stats_row, "MINUTES TODAY")
        self.level_card, self.level_value = self._stat_card(stats_row, "LEVEL")
        self.level_xp = small_label("", FAINT)
        self.level_card.layout().addWidget(self.level_xp)
        self.level_card.layout().addStretch()
        root.addLayout(stats_row)

        # weekly chart
        weekly_frame, weekly_layout = card()
        weekly_frame.setFixedHeight(220)
        weekly_layout.addWidget(title_label("THIS WEEK"))
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

        # per-subject progress
        subject_frame, subject_layout = card()
        subject_layout.addWidget(title_label("BY SUBJECT"))
        self.subject_list = QVBoxLayout()
        self.subject_list.setSpacing(10)
        subject_layout.addLayout(self.subject_list)
        subject_layout.addStretch()
        root.addWidget(subject_frame, 1)

    def _stat_card(self, parent_layout: QHBoxLayout, title: str):
        frame, layout = card()
        frame.setFixedHeight(140)
        layout.addWidget(label(title, 11, MUTED, bold=True))
        value = label("0", 34, TEXT, bold=True)
        layout.addWidget(value)
        layout.addStretch()
        parent_layout.addWidget(frame)
        return frame, value

    # -------------------------------------------------------------- refresh
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        self.done_value.setText(str(store.count_tasks(done=True)))
        self.pending_value.setText(str(store.count_tasks(done=False)))
        self.streak_value.setText(f"{store.study_streak()} 🔥")
        self.minutes_value.setText(str(store.minutes_completed_on(store.today())))
        level_info = store.level_progress()
        self.level_value.setText(str(level_info["level"]))
        self.level_xp.setText(f"{level_info['xp']} XP · {level_info['next_level_in']} to next")

        counts = store.weekly_completed_counts()
        peak = max(counts) or 1
        today_index = store.today().weekday()
        for i, bar in enumerate(self.bars):
            bar.setValue(int(counts[i] / peak * 100))
            self.day_labels[i].setText("• " + WEEKDAYS[i] if i == today_index else WEEKDAYS[i])

        while self.subject_list.count():
            item = self.subject_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        progress = store.subject_progress()
        if not progress:
            self.subject_list.addWidget(empty_note(
                "Tag tasks with a subject (when adding tasks/exams) to see progress here."))
            return

        for row_data in progress:
            done, pending = row_data["done"] or 0, row_data["pending"] or 0
            total = done + pending
            pct = int(done / total * 100) if total else 0

            holder = QWidget()
            holder.setStyleSheet("background: transparent;")
            holder_layout = QVBoxLayout(holder)
            holder_layout.setSpacing(4)
            header = QHBoxLayout()
            header.addWidget(label(row_data["subject"] or "(no subject)", 14, TEXT, bold=True))
            header.addStretch()
            header.addWidget(small_label(f"{done}/{total} done · {pct}%", MUTED))
            holder_layout.addLayout(header)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(pct)
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            bar.setStyleSheet(
                f"QProgressBar {{ background-color: {DEEP}; border: none; border-radius: 5px; }}"
                f"QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 5px; }}"
            )
            holder_layout.addWidget(bar)
            self.subject_list.addWidget(holder)