"""SQLite storage for the Student Command Center.

Pure Python (no Qt), so the desktop app, background workers and future web
API can all use it. Every function opens its own short-lived connection,
which makes it safe to call from any thread.

Dates are stored as plain "YYYY-MM-DD HH:MM" strings (local time).
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from app_paths import data_dir

DB_PATH = data_dir() / "data" / "planner.db"
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (
    id    INTEGER PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS exams (
    id         INTEGER PRIMARY KEY,
    subject    TEXT NOT NULL,
    occurs_at  TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'user',
    done       INTEGER NOT NULL DEFAULT 0,
    result     TEXT,
    marks      INTEGER
);

CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY,
    title        TEXT NOT NULL,
    due_at       TEXT,
    minutes      INTEGER,
    subject      TEXT,
    done         INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    plan_id      INTEGER,
    created_by   TEXT NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS plans (
    id            INTEGER PRIMARY KEY,
    title         TEXT NOT NULL,
    exam_subject  TEXT,
    created_at    TEXT NOT NULL,
    total_minutes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS notification_log (
    id      INTEGER PRIMARY KEY,
    kind    TEXT NOT NULL,
    ref_id  INTEGER NOT NULL DEFAULT 0,
    day     TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE (kind, ref_id, day)
);
"""


# ----------------------------------------------------------------- internals
def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Create tables and add columns that older databases are missing."""
    conn.executescript(SCHEMA)
    for statement in (
        "ALTER TABLE exams ADD COLUMN done INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE exams ADD COLUMN result TEXT",
        "ALTER TABLE exams ADD COLUMN marks INTEGER",
    ):
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass  # column already exists


def _query(sql: str, params: tuple = ()) -> list[dict]:
    with _lock:
        with closing(_connect()) as conn:
            conn.executescript(SCHEMA)
            return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _execute(sql: str, params: tuple = ()) -> int:
    with _lock:
        with closing(_connect()) as conn:
            conn.executescript(SCHEMA)
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid


# ------------------------------------------------------------------- helpers
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today() -> date:
    return date.today()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


# --------------------------------------------------------------------- tasks
def add_task(title: str, due_at: str | None = None, minutes: int | None = None,
             subject: str | None = None, plan_id: int | None = None,
             created_by: str = "user") -> int:
    return _execute(
        "INSERT INTO tasks (title, due_at, minutes, subject, plan_id, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (title.strip(), due_at, minutes, subject, plan_id, created_by),
    )


def list_tasks(include_done: bool = True, subject: str | None = None,
               plan_id: int | None = None) -> list[dict]:
    sql = "SELECT * FROM tasks WHERE 1=1"
    params: list = []
    if not include_done:
        sql += " AND done = 0"
    if subject:
        sql += " AND subject = ?"
        params.append(subject)
    if plan_id is not None:
        sql += " AND plan_id = ?"
        params.append(plan_id)
    sql += " ORDER BY done, (due_at IS NULL), due_at, id"
    return _query(sql, tuple(params))


def set_task_done(task_id: int, done: bool) -> None:
    _execute(
        "UPDATE tasks SET done = ?, completed_at = ? WHERE id = ?",
        (1 if done else 0, now_str() if done else None, task_id),
    )


def delete_task(task_id: int) -> None:
    _execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def count_tasks(done: bool | None = None) -> int:
    if done is None:
        rows = _query("SELECT COUNT(*) AS n FROM tasks")
    else:
        rows = _query("SELECT COUNT(*) AS n FROM tasks WHERE done = ?", (1 if done else 0,))
    return rows[0]["n"] if rows else 0


# --------------------------------------------------------------------- exams
def add_exam(subject: str, occurs_at: str, created_by: str = "user") -> int:
    return _execute(
        "INSERT INTO exams (subject, occurs_at, created_by) VALUES (?, ?, ?)",
        (subject.strip(), occurs_at, created_by),
    )


def list_exams(only_upcoming: bool = False) -> list[dict]:
    if only_upcoming:
        return _query("SELECT * FROM exams WHERE occurs_at >= ? ORDER BY occurs_at", (now_str(),))
    return _query("SELECT * FROM exams ORDER BY occurs_at")


def next_exam() -> dict | None:
    rows = _query("SELECT * FROM exams WHERE occurs_at >= ? ORDER BY occurs_at LIMIT 1", (now_str(),))
    return rows[0] if rows else None


def delete_exam(exam_id: int) -> None:
    _execute("DELETE FROM exams WHERE id = ?", (exam_id,))


def set_exam_result(exam_id: int, result: str, marks: int | None) -> None:
    _execute(
        "UPDATE exams SET done = 1, result = ?, marks = ? WHERE id = ?",
        (result, marks, exam_id),
    )


def completed_exam_count() -> int:
    rows = _query("SELECT COUNT(*) AS n FROM exams WHERE done = 1")
    return rows[0]["n"] if rows else 0


# -------------------------------------------------------------------- rewards
def add_xp(amount: int) -> tuple[int, bool]:
    """Add XP and return (total, leveled_up). One level per 100 XP."""
    current = int(get_setting("xp", "0") or 0)
    new_total = current + amount
    set_setting("xp", str(new_total))
    leveled = level_for(new_total) > level_for(current)
    return new_total, leveled


def level_for(xp: int) -> int:
    return xp // 100 + 1


def level_progress() -> dict:
    xp = int(get_setting("xp", "0") or 0)
    level = level_for(xp)
    return {
        "xp": xp,
        "level": level,
        "into_level": xp % 100,
        "next_level_in": 100 - (xp % 100),
    }


# ---------------------------------------------------------- notification log
def mark_notification(kind: str, ref_id: int, day: str) -> bool:
    """Record a notification for (kind, ref, day). True if it was new."""
    with _lock:
        with closing(_connect()) as conn:
            conn.executescript(SCHEMA)
            cursor = conn.execute(
                "INSERT OR IGNORE INTO notification_log (kind, ref_id, day, sent_at) "
                "VALUES (?, ?, ?, ?)",
                (kind, ref_id, day, now_str()),
            )
            conn.commit()
            return cursor.rowcount > 0


# ------------------------------------------------------------------ subjects
def add_subject(name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    existing = _query("SELECT id FROM subjects WHERE lower(name) = lower(?)", (name,))
    if existing:
        return False
    _execute("INSERT INTO subjects (name) VALUES (?)", (name,))
    return True


def list_subjects() -> list[dict]:
    return _query("SELECT * FROM subjects ORDER BY name")


def delete_subject(name: str) -> None:
    _execute("DELETE FROM subjects WHERE lower(name) = lower(?)", (name.strip(),))


# --------------------------------------------------------------------- plans
def add_plan(title: str, exam_subject: str | None, total_minutes: int) -> int:
    return _execute(
        "INSERT INTO plans (title, exam_subject, created_at, total_minutes) VALUES (?, ?, ?, ?)",
        (title.strip(), exam_subject, now_str(), total_minutes),
    )


def list_plans(limit: int = 5) -> list[dict]:
    return _query("SELECT * FROM plans ORDER BY id DESC LIMIT ?", (limit,))


# ------------------------------------------------------------------ settings
DEFAULT_SETTINGS = {
    "student_name": "Student",
    "daily_goal_minutes": "120",
}


def get_setting(key: str, default: str | None = None) -> str | None:
    rows = _query("SELECT value FROM settings WHERE key = ?", (key,))
    if rows and rows[0]["value"] is not None:
        return rows[0]["value"]
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(key: str, value: str) -> None:
    _execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# ----------------------------------------------------------------- analytics
def completed_counts_by_day(start: date, end: date) -> dict[str, int]:
    rows = _query(
        "SELECT substr(completed_at, 1, 10) AS day, COUNT(*) AS n "
        "FROM tasks WHERE done = 1 AND completed_at IS NOT NULL "
        "AND substr(completed_at, 1, 10) BETWEEN ? AND ? GROUP BY day",
        (start.isoformat(), end.isoformat()),
    )
    return {row["day"]: row["n"] for row in rows}


def weekly_completed_counts() -> list[int]:
    """Completed tasks per weekday, Monday first. Mon..Sun."""
    today_ = today()
    monday = today_ - timedelta(days=today_.weekday())
    counts = completed_counts_by_day(monday, monday + timedelta(days=6))
    return [counts.get((monday + timedelta(days=i)).isoformat(), 0) for i in range(7)]


def minutes_completed_on(day: date) -> int:
    rows = _query(
        "SELECT COALESCE(SUM(minutes), 0) AS total FROM tasks "
        "WHERE done = 1 AND completed_at IS NOT NULL AND substr(completed_at, 1, 10) = ?",
        (day.isoformat(),),
    )
    return rows[0]["total"] if rows else 0


def subject_progress() -> list[dict]:
    """Per subject: pending and completed task counts (tasks with a subject set)."""
    rows = _query(
        "SELECT subject, "
        "SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) AS pending, "
        "SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done "
        "FROM tasks WHERE subject IS NOT NULL AND subject != '' GROUP BY subject ORDER BY subject"
    )
    return rows


def study_streak() -> int:
    """Consecutive days (ending today) with at least one completed task."""
    rows = _query("SELECT DISTINCT substr(completed_at, 1, 10) AS day FROM tasks "
                  "WHERE done = 1 AND completed_at IS NOT NULL")
    days = {row["day"] for row in rows}
    if not days:
        return 0
    streak = 0
    cursor = today()
    if cursor.isoformat() not in days:
        cursor -= timedelta(days=1)  # a streak survives until the day is over
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


# -------------------------------------------------------------------- danger
def reset_all() -> None:
    with _lock:
        with closing(_connect()) as conn:
            conn.executescript(
                "DROP TABLE IF EXISTS tasks; DROP TABLE IF EXISTS exams; "
                "DROP TABLE IF EXISTS plans; DROP TABLE IF EXISTS subjects; "
                "DROP TABLE IF EXISTS settings; DROP TABLE IF EXISTS notification_log;"
            )
            conn.executescript(SCHEMA)
            conn.commit()