"""Automatic reminders - checks the calendar periodically and fires toasts.

Pure logic + store: no Qt, so it is easy to test. main.py calls run_once()
every minute and turns the returned (title, message) pairs into toasts.
Every reminder is de-duplicated per (kind, ref, day) in store.notification_log.
"""

from __future__ import annotations

from datetime import datetime

import store

EVENING_HOUR = 17  # exam check-in starts at 5 PM on exam day
UPCOMING_WINDOW_DAYS = 3


class ReminderChecker:
    def run_once(self, now: datetime) -> list[tuple[str, str]]:
        toasts: list[tuple[str, str]] = []
        today = now.date().isoformat()

        exams = store.list_exams()
        for exam in exams:
            when = store.parse_dt(exam["occurs_at"])
            if when is None or exam.get("done"):
                continue

            days_left = (when.date() - now.date()).days
            subject = exam["subject"]

            if 1 <= days_left <= UPCOMING_WINDOW_DAYS:
                if store.mark_notification("exam_upcoming", exam["id"], today):
                    toasts.append((
                        f"📚 {subject} exam ahead",
                        f"Your {subject} exam is in {days_left} day{'s' if days_left > 1 else ''} "
                        f"({when.strftime('%a %d %b, %I:%M %p')}). Generate a plan?",
                    ))

            if days_left == 0 and store.mark_notification("exam_today", exam["id"], today):
                toasts.append((
                    f"🎯 {subject} exam is TODAY",
                    f"Stay calm — it's at {when.strftime('%I:%M %p')}. You've got this!",
                ))

            if (days_left == 0 and now.hour >= EVENING_HOUR
                    and store.mark_notification("exam_evening", exam["id"], today)):
                toasts.append((
                    f"How did {subject} go? 🎓",
                    "Open the Exams page and log how it went — it counts towards your XP.",
                ))

            if days_left < 0 and store.mark_notification("exam_followup", exam["id"], "once"):
                # "once" instead of the date: ask at most one time per exam
                toasts.append((
                    f"How did {subject} go? 🎓",
                    "Your exam date has passed. Log the result on the Exams page to earn +50 XP.",
                ))

        tasks = store.list_tasks(include_done=False)
        due_today = [t for t in tasks if t["due_at"] and t["due_at"][:10] == today]
        if due_today and store.mark_notification("task_due_today", 0, today):
            titles = ", ".join(t["title"] for t in due_today[:3])
            more = f" and {len(due_today) - 3} more" if len(due_today) > 3 else ""
            toasts.append(("📋 Tasks due today", f"{len(due_today)} task(s): {titles}{more}"))

        overdue = [t for t in tasks if t["due_at"] and t["due_at"][:10] < today]
        if overdue and store.mark_notification("task_overdue", 0, today):
            first = overdue[0]["title"]
            extra = f" and {len(overdue) - 1} more" if len(overdue) > 1 else ""
            toasts.append(("⏰ Overdue tasks", f"'{first}'{extra} — clear it or reschedule it."))

        return toasts