"""AI output parsing tests (mock model replies, no API). Run:  python tests/test_ai_parsing.py"""
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import store  # noqa: E402
from planner import _parse_plan, _valid_blocks  # noqa: E402
from timetable import validate_exams  # noqa: E402

store.DB_PATH = Path(tempfile.gettempdir()) / "scc_test_planner.db"
store.reset_all()

# ---- planner: fenced JSON, clamping, junk blocks
sample = (
    '```json\n{"plan_title": "Physics sprint", "days": ['
    '{"day_offset": 0, "blocks": [{"title": "Optics theory", "start_time": "18:00", "minutes": 45}]}, '
    '{"day_offset": 9, "blocks": [{"title": "x", "start_time": "5:5", "minutes": 10}, '
    '{"title": "Revision", "start_time": "19:00", "minutes": "60"}]}]}\n```'
)
plan = _parse_plan(sample)
assert plan["plan_title"] == "Physics sprint"
valid = _valid_blocks(plan, days_available=7, daily_minutes=120)
assert len(valid) == 2, "offset 9 must clamp to 6, junk block dropped"
assert valid[0]["blocks"][0]["minutes"] == 45
assert valid[1]["blocks"][0]["minutes"] == 60, "string minutes converted"
assert valid[1]["blocks"][0]["start_time"] == "19:00"

# ---- timetable: junk rows dropped, duplicates filtered, year-less handled
fake_reply = (
    '{"exams": ['
    '{"subject": "Physics", "date": "%s", "time": "09:30"},'
    '{"subject": "Chemistry", "date": "%s", "time": "14:00"},'
    '{"subject": "Mathematics", "date": "not-a-date", "time": "09:00"},'
    '{"subject": "History", "date": "2001-01-01", "time": "09:00"},'
    '{"subject": "", "date": "%s", "time": "10:00"}'
    ']}' % ((date.today() + timedelta(days=9)).isoformat(),
            (date.today() + timedelta(days=16)).isoformat(),
            (date.today() + timedelta(days=25)).isoformat())
)
rows = validate_exams(fake_reply)
assert len(rows) == 2, f"expected 2 valid rows, got {rows}"
assert rows[0]["occurs_at"].endswith("09:30")

store.add_exam("Physics", rows[0]["occurs_at"])
rows_again = validate_exams(fake_reply)
assert len(rows_again) == 1 and rows_again[0]["subject"] == "Chemistry", "duplicate not filtered"

store.reset_all()
store.DB_PATH.unlink(missing_ok=True)
print("test_ai_parsing PASSED")