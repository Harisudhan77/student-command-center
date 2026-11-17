"""Supabase (Postgres) implementation of store.py's API for the web app.

The desktop app keeps its local SQLite file via store.py. The web app needs a
database that survives across Vercel's serverless containers, so this module
implements the SAME function names against Supabase's REST API (PostgREST).

Tables live in the public schema and were created by the migration
`create_command_center_tables`. Row Level Security is ON; the server talks
with the secret (service) key only - it is never sent to the browser.

Dates are stored as plain "YYYY-MM-DD HH:MM" strings, exactly like store.py.
"Today" is computed in IST (UTC+5:30) so countdowns match the student's day.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import httpx

IST = timezone(timedelta(hours=5, minutes=30), name="IST")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
# New-style secret keys look like "sb_secret_..."; legacy ones are JWTs.
SECRET_KEY = (os.getenv("SUPABASE_SECRET_KEY")
              or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_client: httpx.Client | None = None


class DBNotReady(Exception):
    """Raised when the database cannot be used yet, with a user-facing message."""


def _http() -> httpx.Client:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.Client(base_url=SUPABASE_URL, timeout=_TIMEOUT)
    return _client


def ensure_ready() -> None:
    """Raise DBNotReady with a clear message if Supabase is not configured."""
    if not SUPABASE_URL or not SECRET_KEY:
        raise DBNotReady(
            "Database is not configured. Set SUPABASE_URL and "
            "SUPABASE_SECRET_KEY in the Vercel project environment variables."
        )


def _headers(prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SECRET_KEY,
        "Authorization": f"Bearer {SECRET_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request(method: str, path: str, *, params: dict | None = None,
             json_body: list | dict | None = None,
             prefer: str | None = None) -> list[dict]:
    ensure_ready()
    response = _http().request(method, path, params=params, json=json_body,
                               headers=_headers(prefer))
    if response.status_code >= 400:
        detail = response.text[:300]
        raise RuntimeError(f"Supabase {response.status_code} on {method} {path}: {detail}")
    if not response.content:
        return []
    return response.json()


def _select(table: str, params: dict | None = None) -> list[dict]:
    return _request("GET", f"/rest/v1/{table}", params={"select": "*", **(params or {})})


def _insert(table: str, row: dict, *, on_conflict: str | None = None,
            ignore: bool = False, return_rows: bool = True) -> list[dict]:
    prefer = "return=representation" if return_rows else "return=minimal"
    params: dict = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
        prefer += ",resolution=ignore-duplicates" if ignore else ",resolution=merge-duplicates"
    return _request("POST", f"/rest/v1/{table}", params=params,
                    json_body=row, prefer=prefer)


def _update(table: str, filters: dict, patch: dict) -> None:
    _request("PATCH", f"/rest/v1/{table}", params=filters, json_body=patch,
             prefer="return=minimal")


def _delete(table: str, filters: dict) -> None:
    _request("DELETE", f"/rest/v1/{table}", params=filters, prefer="return=minimal")


# ------------------------------------------------------------------- helpers
def now_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M")


def today() -> date:
    return datetime.now(IST).date()


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
    rows = _insert("tasks", {
        "title": title.strip(), "due_at": due_at, "minutes": minutes,
        "subject": subject, "plan_id": plan_id, "created_by": created_by,
    })
    return int(rows[0]["id"])


def list_tasks(include_done: bool = True, subject: str | None = None,
               plan_id: int | None = None) -> list[dict]:
    rows = _select("tasks")
    if not include_done:
        rows = [row for row in rows if not row["done"]]
    if subject:
        rows = [row for row in rows if row["subject"] == subject]
    if plan_id is not None:
        rows = [row for row in rows if row["plan_id"] == plan_id]
    # Same order as store.py: pending first, dated before undated, then by id.
    rows.sort(key=lambda r: (r["done"], r["due_at"] is None, r["due_at"] or "", r["id"]))
    return rows


def set_task_done(task_id: int, done: bool) -> None:
    _update("tasks", {"id": f"eq.{task_id}"},
            {"done": 1 if done else 0, "completed_at": now_str() if done else None})


def delete_task(task_id: int) -> None:
    _delete("tasks", {"id": f"eq.{task_id}"})


def count_tasks(done: bool | None = None) -> int:
    rows = _select("tasks")
    if done is None:
        return len(rows)
    return sum(1 for row in rows if row["done"] == (1 if done else 0))


# --------------------------------------------------------------------- exams
def add_exam(subject: str, occurs_at: str, created_by: str = "user") -> int:
    rows = _insert("exams", {"subject": subject.strip(), "occurs_at": occurs_at,
                             "created_by": created_by})
    return int(rows[0]["id"])


def list_exams(only_upcoming: bool = False) -> list[dict]:
    rows = _select("exams")
    if only_upcoming:
        rows = [row for row in rows if row["occurs_at"] >= now_str()]
    rows.sort(key=lambda r: r["occurs_at"])
    return rows


def next_exam() -> dict | None:
    upcoming = list_exams(only_upcoming=True)
    return upcoming[0] if upcoming else None


def delete_exam(exam_id: int) -> None:
    _delete("exams", {"id": f"eq.{exam_id}"})


def set_exam_result(exam_id: int, result: str, marks: int | None) -> None:
    _update("exams", {"id": f"eq.{exam_id}"},
            {"done": 1, "result": result, "marks": marks})


def completed_exam_count() -> int:
    return sum(1 for row in _select("exams") if row["done"] == 1)


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
    rows = _insert("notification_log",
                   {"kind": kind, "ref_id": ref_id, "day": day, "sent_at": now_str()},
                   on_conflict="kind,ref_id,day", ignore=True)
    return len(rows) > 0


# ------------------------------------------------------------------ subjects
def add_subject(name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    existing = [s for s in _select("subjects")
                if s["name"].lower() == name.lower()]
    if existing:
        return False
    _insert("subjects", {"name": name}, return_rows=False)
    return True


def list_subjects() -> list[dict]:
    rows = _select("subjects")
    rows.sort(key=lambda r: r["name"])
    return rows


def delete_subject(name: str) -> None:
    name = name.strip()
    _delete("subjects", {"name": f"ilike.{name}"})


# --------------------------------------------------------------------- plans
def add_plan(title: str, exam_subject: str | None, total_minutes: int) -> int:
    rows = _insert("plans", {"title": title.strip(), "exam_subject": exam_subject,
                             "created_at": now_str(), "total_minutes": total_minutes})
    return int(rows[0]["id"])


def list_plans(limit: int = 5) -> list[dict]:
    rows = _select("plans", params={"order": "id.desc", "limit": str(limit)})
    return rows


# ------------------------------------------------------------------ settings
DEFAULT_SETTINGS = {
    "student_name": "Student",
    "daily_goal_minutes": "120",
}


def get_setting(key: str, default: str | None = None) -> str | None:
    rows = _select("settings", params={"key": f"eq.{key}"})
    if rows and rows[0]["value"] is not None:
        return rows[0]["value"]
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(key: str, value: str) -> None:
    _insert("settings", {"key": key, "value": value}, on_conflict="key")


# ----------------------------------------------------------------- analytics
def completed_counts_by_day(start: date, end: date) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in _select("tasks", params={"done": "eq.1"}):
        day = (row.get("completed_at") or "")[:10]
        if day and start.isoformat() <= day <= end.isoformat():
            counts[day] = counts.get(day, 0) + 1
    return counts


def weekly_completed_counts() -> list[int]:
    """Completed tasks per weekday, Monday first. Mon..Sun."""
    today_ = today()
    monday = today_ - timedelta(days=today_.weekday())
    counts = completed_counts_by_day(monday, monday + timedelta(days=6))
    return [counts.get((monday + timedelta(days=i)).isoformat(), 0) for i in range(7)]


def minutes_completed_on(day: date) -> int:
    total = 0
    for row in _select("tasks", params={"done": "eq.1"}):
        if (row.get("completed_at") or "")[:10] == day.isoformat() and row.get("minutes"):
            total += row["minutes"]
    return total


def subject_progress() -> list[dict]:
    """Per subject: pending and completed task counts (tasks with a subject set)."""
    stats: dict[str, dict] = {}
    for row in _select("tasks"):
        subject = row.get("subject")
        if not subject:
            continue
        bucket = stats.setdefault(subject, {"subject": subject, "pending": 0, "done": 0})
        bucket["done" if row["done"] else "pending"] += 1
    return [stats[key] for key in sorted(stats)]


def study_streak() -> int:
    """Consecutive days (ending today) with at least one completed task."""
    days = {(row.get("completed_at") or "")[:10]
            for row in _select("tasks", params={"done": "eq.1"})}
    days.discard("")
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
    for table, key in (("tasks", "id"), ("exams", "id"), ("plans", "id"),
                       ("subjects", "id"), ("settings", "key"),
                       ("notification_log", "id")):
        _delete(table, {key: "not.is.null"})