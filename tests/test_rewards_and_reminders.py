"""Reminder + reward logic tests. Run:  python tests/test_rewards_and_reminders.py"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import store  # noqa: E402
import rewards  # noqa: E402
from reminders import ReminderChecker  # noqa: E402

store.DB_PATH = Path(tempfile.gettempdir()) / "scc_test_planner.db"
store.reset_all()

checker = ReminderChecker()

e_future = store.add_exam("Physics", "2026-11-19 09:00")
e_today = store.add_exam("Chemistry", "2026-11-16 14:00")
e_past = store.add_exam("Maths", "2026-11-15 09:00")
store.add_task("Essay draft", due_at="2026-11-16 18:00")
store.add_task("Old homework", due_at="2026-11-10 18:00")

# morning of exam day: every reminder type fires exactly once
toasts = checker.run_once(datetime(2026, 11, 16, 10, 0))
titles = [t for t, _ in toasts]
assert any("Physics" in t for t in titles)
assert any("TODAY" in t for t in titles)
assert any("How did Maths go" in t for t in titles)
assert any("Tasks due today" in t for t in titles)
assert any("Overdue" in t for t in titles)
assert len(toasts) == 5

# same day again: fully deduplicated
assert checker.run_once(datetime(2026, 11, 16, 12, 0)) == []

# evening of exam day: check-in fires
evening = checker.run_once(datetime(2026, 11, 16, 18, 30))
assert any("How did Chemistry go" in t for t, _ in evening)

# next morning: chemistry follow-up, maths not repeated
titles4 = [t for t, _ in checker.run_once(datetime(2026, 11, 17, 9, 0))]
assert any("How did Chemistry go" in t for t in titles4)
assert not any("Maths" in t for t in titles4)

# logging the result stops all nudges for that exam
store.set_exam_result(e_today, "great", 88)
assert not any("Chemistry" in t for t, _ in checker.run_once(datetime(2026, 11, 18, 9, 0)))

# --- rewards
store.reset_all()
rewards.on_task_completed({"id": 1, "title": "x"})  # no notifier in tests -> silent
assert store.level_progress()["xp"] == 15
rewards.on_exam_completed({"id": 2, "subject": "Physics"}, "great")
assert store.level_progress()["xp"] == 65

# level-up boundary
store.set_setting("xp", "95")
xp, leveled = store.add_xp(10)
assert leveled is True and store.level_for(xp) == 2

# dedupe is per (kind, ref, day)
assert store.mark_notification("test", 1, "2026-11-16") is True
assert store.mark_notification("test", 1, "2026-11-16") is False

store.reset_all()
store.DB_PATH.unlink(missing_ok=True)
print("test_rewards_and_reminders PASSED")