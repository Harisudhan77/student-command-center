"""Reward system - XP, levels, praise toasts when things get completed."""

from __future__ import annotations

import random

import store

XP_PER_TASK = 15
XP_PER_EXAM = 50

PRAISE = [
    "Nice work — that's momentum!",
    "One less thing to worry about. 💪",
    "Great job, keep the streak alive!",
    "That's how it's done!",
    "Your future self says thanks. 🙌",
    "Small steps, big results.",
    "Productive machine activated. 🚀",
]

STREAK_MILESTONES = (3, 7, 14, 30)


def on_task_completed(task: dict | None = None) -> None:
    """Call right after a task is ticked off. Sends praise + XP toast."""
    notifier = _notifier()
    xp, leveled = store.add_xp(XP_PER_TASK)

    lines = [random.choice(PRAISE), f"+{XP_PER_TASK} XP  ·  Level {store.level_for(xp)}"]

    done_today = store.minutes_completed_on(store.today())
    tasks_done_today = _tasks_completed_today()
    if tasks_done_today in (3, 5, 10):
        lines.append(f"🎯 {tasks_done_today} tasks completed today!")

    streak = store.study_streak()
    if streak in STREAK_MILESTONES and store.mark_notification("streak", streak, store.today().isoformat()):
        lines.append(f"🔥 {streak}-day study streak!")

    if notifier is not None:
        notifier.notify("Task completed 🎉", "\n".join(lines))
    if leveled and notifier is not None:
        notifier.notify("LEVEL UP! 🚀", f"You reached Level {store.level_for(xp)}. Keep going!")


def on_exam_completed(exam: dict, result: str) -> None:
    """Call after the student records how an exam went."""
    notifier = _notifier()
    xp, leveled = store.add_xp(XP_PER_EXAM)
    total_exams = store.completed_exam_count()

    lines = [f"{exam['subject']} — logged as “{result}”.",
             f"+{XP_PER_EXAM} XP  ·  Level {store.level_for(xp)}"]
    if total_exams in (1, 5, 10):
        lines.append(f"🏅 That's {total_exams} exam(s) behind you!")

    if notifier is not None:
        notifier.notify("Exam logged 🎓", "\n".join(lines))
        if leveled:
            notifier.notify("LEVEL UP! 🚀", f"You reached Level {store.level_for(xp)}. Keep going!")


def _tasks_completed_today() -> int:
    rows = store.completed_counts_by_day(store.today(), store.today())
    return rows.get(store.today().isoformat(), 0)


def _notifier():
    from notify import get_notifier

    return get_notifier()