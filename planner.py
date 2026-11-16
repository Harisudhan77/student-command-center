"""📆 Study Planner page - AI generates a plan, you approve it, it becomes tasks."""

from __future__ import annotations

import json
import re
from datetime import timedelta

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QScrollArea,
    QSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

import store
from web.ai_core import PRIMARY_MODEL, friendly_error, stream_reply
from ui_theme import (BG, BODY, BORDER, DEEP, FAINT, MUTED, TEXT,
                      button, empty_note, label, page_header, page_style,
                      small_label, title_label)

MAX_DAYS = 14

PLANNER_INSTRUCTIONS = """You are a study planner. Reply with ONLY a JSON object - \
no markdown fences, no explanation before or after.

Schema:
{"plan_title": string, "days": [{"day_offset": integer, "blocks": \
[{"title": string, "start_time": "HH:MM", "minutes": integer}]}]}

Rules:
- day_offset counts from 0 = today, up to the number of days available minus 1.
- 1 to 4 blocks per day; every block: minutes between 15 and 180, total per day \
must not exceed the daily study minutes.
- Order topics from hardest/most unfamiliar to easiest across the whole plan.
- Mix explanation, practice problems and revision. The final day should be revision.
- Titles are short and specific (e.g. "Kinematics - numericals practice"), never "Study".
- start_time is 24-hour "HH:MM".


Student request:
"""


class PlannerWorker(QThread):
    """Runs the plan generation off the GUI thread and validates the JSON."""

    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, prompt: str, parent=None):
        super().__init__(parent)
        self.prompt = prompt

    def run(self) -> None:
        messages = [
            {"role": "system", "content": PLANNER_INSTRUCTIONS},
            {"role": "user", "content": self.prompt},
        ]
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                reply = "".join(stream_reply(messages))
            except Exception as exc:  # noqa: BLE001
                self.failed.emit(friendly_error(exc))
                return

            try:
                plan = _parse_plan(reply)
                self.done.emit(plan)
                return
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                messages = messages + [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": "That was not valid JSON for the schema. "
                     "Reply again with ONLY the JSON object, nothing else."},
                ]

        self.failed.emit("The model could not produce a valid plan JSON. Try again. "
                         f"(Last error: {last_error})")


def _parse_plan(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    data = json.loads(text[start:end + 1])
    if not isinstance(data.get("days"), list) or not data["days"]:
        raise ValueError("plan has no days")
    return data


def _valid_blocks(plan: dict, days_available: int, daily_minutes: int) -> list[dict]:
    """Clamp and validate the model's output into trustworthy rows."""
    today = store.today()
    valid_days = []
    for day in plan.get("days", []):
        if not isinstance(day, dict):
            continue
        offset = day.get("day_offset")
        if not isinstance(offset, int):
            try:
                offset = int(offset)
            except (TypeError, ValueError):
                continue
        offset = max(0, min(offset, days_available - 1, MAX_DAYS - 1))

        blocks = []
        total = 0
        for block in day.get("blocks", []) or []:
            if not isinstance(block, dict):
                continue
            title = str(block.get("title", "")).strip()
            minutes = block.get("minutes")
            start_time = str(block.get("start_time", "")).strip()
            if not title or not re.fullmatch(r"\d{1,2}:\d{2}", start_time):
                continue
            if not isinstance(minutes, int):
                try:
                    minutes = int(float(minutes))
                except (TypeError, ValueError):
                    continue
            minutes = max(15, min(minutes, 180))
            if total + minutes > daily_minutes * 2:  # hard sanity cap
                continue
            total += minutes
            when = today + timedelta(days=offset)
            start_time = start_time if len(start_time) == 5 else "0" + start_time
            blocks.append({
                "title": title,
                "start_time": start_time,
                "due_at": f"{when.isoformat()} {start_time}",
                "minutes": minutes,
            })
        if blocks:
            valid_days.append({"offset": offset, "blocks": blocks})
    return valid_days


class PlannerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("plannerPage")
        self.setStyleSheet(page_style("plannerPage"))
        self._worker = None
        self._preview_days: list[dict] = []
        self._preview_subject = ""
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(14)

        root.addWidget(page_header(
            "Study Planner",
            f"Tell the AI about an exam ({PRIMARY_MODEL}) - get a day-by-day plan you approve first."))

        # --- form
        form_card = QWidget()
        form_card.setStyleSheet(f"background-color: {DEEP}; border: 1px solid {BORDER}; border-radius: 12px;")
        form = QVBoxLayout(form_card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(10)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.subject_input = QComboBox()
        self.subject_input.setEditable(True)
        self.subject_input.setFixedHeight(34)
        self.subject_input.setStyleSheet(
            f"QComboBox {{ background-color: #1D2130; color: {BODY}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 0 10px; }}"
            f"QComboBox QAbstractItemView {{ background-color: {DEEP}; color: {BODY}; }}"
        )
        self.subject_input.lineEdit().setPlaceholderText("Exam subject…  e.g. Physics")
        self.days_input = QSpinBox()
        self.days_input.setRange(1, MAX_DAYS)
        self.days_input.setValue(7)
        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(30, 480)
        self.minutes_input.setSingleStep(15)
        for spin, suffix in ((self.days_input, " days"), (self.minutes_input, " min/day")):
            spin.setFixedHeight(34)
            spin.setSuffix(suffix)
            spin.setStyleSheet(
                f"QSpinBox {{ background-color: #1D2130; color: {BODY}; border: 1px solid {BORDER}; "
                f"border-radius: 8px; padding: 0 10px; }}"
            )
        row1.addWidget(self.subject_input, 1)
        row1.addWidget(QLabel("Plan length:"))
        row1.addWidget(self.days_input)
        row1.addWidget(QLabel("Study:"))
        row1.addWidget(self.minutes_input)
        for w in row1.findChildren(QLabel):
            w.setStyleSheet(f"color: {MUTED}; font-size: 12px; background: transparent;")
        form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.focus_input = QLineEdit()
        self.focus_input.setPlaceholderText("Optional: topics to focus on, e.g. 'weak in optics, strong in kinematics'")
        self.focus_input.setFixedHeight(34)
        self.focus_input.setStyleSheet(
            f"QLineEdit {{ background-color: #1D2130; color: {BODY}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 0 10px; }}"
        )
        self.generate_btn = button("✨ Generate plan", "primary", height=34)
        self.generate_btn.clicked.connect(self._generate)
        row2.addWidget(self.focus_input, 1)
        row2.addWidget(self.generate_btn)
        form.addLayout(row2)
        root.addWidget(form_card)

        self.status = label("", 12, MUTED)
        root.addWidget(self.status)

        # --- preview
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVisible(False)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.preview_holder = QWidget()
        self.preview_holder.setStyleSheet("background: transparent;")
        self.preview_layout = QVBoxLayout(self.preview_holder)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(10)
        self.scroll.setWidget(self.preview_holder)
        root.addWidget(self.scroll, 1)

        self.add_btn = button("➕ Add this plan to my tasks", "primary", height=40)
        self.add_btn.clicked.connect(self._confirm_plan)
        self.add_btn.setVisible(False)
        root.addWidget(self.add_btn)

        # --- latest plan
        self.latest = label("", 12, FAINT)
        self.latest.setWordWrap(True)
        root.addWidget(self.latest)

    # ---------------------------------------------------------------- flow
    def _generate(self) -> None:
        if self._worker is not None:
            return
        subject = self.subject_input.currentText().strip()
        if not subject:
            self.status.setText("Pick or type an exam subject first.")
            return

        days = self.days_input.value()
        daily = self.minutes_input.value()
        focus = self.focus_input.text().strip() or "none mentioned"
        exam = store.next_exam()
        exam_line = (f"{exam['subject']} on {exam['occurs_at']}"
                     if exam and exam["subject"].lower() == subject.lower()
                     else f"{subject} (no date saved - plan for it being after the {days} days)")

        prompt = (
            f"Exam subject: {exam_line}\n"
            f"Days available: {days} (day 0 = today, {store.today().isoformat()})\n"
            f"Daily study minutes: {daily}\n"
            f"Focus topics from the student: {focus}\n"
            "Create the plan now as the JSON object."
        )

        self.status.setText("Planning… this usually takes 10–20 seconds.")
        self.generate_btn.setEnabled(False)
        self._worker = PlannerWorker(prompt, parent=self)
        self._worker.done.connect(self._on_plan)
        self._worker.failed.connect(self._on_fail)
        self._worker.finished.connect(self._cleanup)
        self._worker.start()

    def _on_plan(self, plan: dict) -> None:
        self._preview_days = _valid_blocks(plan, self.days_input.value(), self.minutes_input.value())
        self._preview_subject = self.subject_input.currentText().strip()
        if not self._preview_days:
            self._on_fail("The plan came back empty after validation. Try adjusting the details.")
            return

        self.status.setText("Review your plan - nothing is saved until you approve it below.")
        self._render_preview(plan.get("plan_title", f"{self._preview_subject} plan"))
        self.add_btn.setVisible(True)

    def _on_fail(self, message: str) -> None:
        self.status.setText(f"⚠️  {message}")
        self._preview_days = []
        self._hide_preview()

    def _cleanup(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self.generate_btn.setEnabled(True)

    def _hide_preview(self) -> None:
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.scroll.setVisible(False)
        self.add_btn.setVisible(False)

    def _render_preview(self, plan_title: str) -> None:
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.preview_layout.addWidget(label(plan_title, 16, TEXT, bold=True))
        total_minutes = 0
        day_names = ["Today", "Tomorrow"]
        for day in self._preview_days:
            when = store.today() + timedelta(days=day["offset"])
            heading = (day_names[day["offset"]] if day["offset"] < 2
                       else when.strftime("%a %d %b"))
            heading += f"  ·  {when.isoformat()}"
            self.preview_layout.addWidget(label(heading, 12, "#A78BFA", bold=True))
            for block in day["blocks"]:
                total_minutes += block["minutes"]
                row = QWidget()
                row.setStyleSheet(
                    f"background-color: {DEEP}; border: 1px solid {BORDER}; border-radius: 10px;")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(14, 8, 14, 8)
                row_layout.addWidget(label(f"{block['start_time']}", 13, "#A78BFA", bold=True))
                row_layout.addWidget(label(block["title"], 13, BODY), 1)
                row_layout.addWidget(small_label(f"{block['minutes']} min", FAINT))
                self.preview_layout.addWidget(row)

        self.preview_layout.addWidget(
            small_label(f"{sum(len(d['blocks']) for d in self._preview_days)} study blocks · "
                        f"{total_minutes} minutes total", FAINT))
        self.scroll.setVisible(True)

    def _confirm_plan(self) -> None:
        if not self._preview_days:
            return
        total_minutes = sum(b["minutes"] for d in self._preview_days for b in d["blocks"])
        plan_id = store.add_plan(f"{self._preview_subject} plan", self._preview_subject, total_minutes)
        for day in self._preview_days:
            for block in day["blocks"]:
                store.add_task(block["title"], due_at=block["due_at"], minutes=block["minutes"],
                               subject=self._preview_subject, plan_id=plan_id, created_by="ai")
        store.add_subject(self._preview_subject)
        count = sum(len(d["blocks"]) for d in self._preview_days)
        self.status.setText(f"✅ Added {count} tasks from '{self._preview_subject} plan'. "
                            "See them on the Tasks page.")
        self._preview_days = []
        self._hide_preview()
        self._update_latest()

    # -------------------------------------------------------------- refresh
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        current = self.subject_input.currentText()
        self.subject_input.clear()
        self.subject_input.lineEdit().clear()
        self.subject_input.addItems([s["name"] for s in store.list_subjects()])
        self.subject_input.setCurrentText(current)
        self.minutes_input.setValue(int(store.get_setting("daily_goal_minutes", "120") or 120))
        self._update_latest()
        if self._worker is not None:
            self.status.setText("Planning…")

    def _update_latest(self) -> None:
        plans = store.list_plans(limit=1)
        if not plans:
            self.latest.setText("")
            return
        plan = plans[0]
        pending = len(store.list_tasks(include_done=False, plan_id=plan["id"]))
        total = len(store.list_tasks(plan_id=plan["id"]))
        self.latest.setText(f"Latest plan: {plan['title']} — {total} tasks "
                            f"({pending} still pending) · created {plan['created_at']}")