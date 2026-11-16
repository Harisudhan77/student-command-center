"""Store layer tests. Run:  python tests/test_store.py"""
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import store  # noqa: E402

store.DB_PATH = Path(tempfile.gettempdir()) / "scc_test_planner.db"
store.reset_all()

# --- tasks
t1 = store.add_task("Kinematics practice", due_at="2026-11-20 18:00", minutes=45, subject="Physics")
t2 = store.add_task("Read biology chapter", due_at="2026-11-18 20:00", subject="Biology")
t3 = store.add_task("No date task")
assert store.count_tasks() == 3 and store.count_tasks(done=False) == 3

tasks = store.list_tasks()
assert [t["title"] for t in tasks][:2] == ["Read biology chapter", "Kinematics practice"]

store.set_task_done(t1, True)
assert store.count_tasks(done=True) == 1
assert [t for t in store.list_tasks() if t["id"] == t1][0]["completed_at"] is not None

store.delete_task(t3)
assert store.count_tasks() == 2

# --- exams
store.add_exam("Physics", "2026-12-01 09:00")
e2 = store.add_exam("Biology", "2026-11-30 09:00")
assert store.next_exam()["subject"] == "Biology"
store.delete_exam(e2)
assert store.next_exam()["subject"] == "Physics"

# --- subjects
assert store.add_subject("Physics") is True
assert store.add_subject("physics") is False  # duplicate (case-insensitive)
store.add_subject("Biology")
assert [s["name"] for s in store.list_subjects()] == ["Biology", "Physics"]

# --- settings
store.set_setting("student_name", "Tester")
assert store.get_setting("student_name") == "Tester"
assert store.get_setting("daily_goal_minutes") == "120"  # default

# --- plans
pid = store.add_plan("Physics plan", "Physics", 90)
store.add_task("Optics revision", minutes=45, plan_id=pid, created_by="ai", subject="Physics")
assert len(store.list_tasks(plan_id=pid)) == 1

# --- analytics
counts = store.completed_counts_by_day(date.today() - timedelta(days=6), date.today())
assert sum(counts.values()) >= 1
assert len(store.weekly_completed_counts()) == 7
assert store.study_streak() >= 1

store.reset_all()
store.DB_PATH.unlink(missing_ok=True)
print("test_store PASSED")