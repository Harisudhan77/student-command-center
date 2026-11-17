"""Student Command Center - web API (FastAPI on Vercel).

The desktop app (PySide6) and this web app share the same brain:
  - web/ai_core.py       -> AI tutor / planner (Groq)
  - web/planner_core.py  -> plan parsing & validation
  - web/db.py            -> same storage API as store.py, backed by Supabase

This file only handles HTTP. All endpoints are mobile-friendly JSON.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

WEB_DIR = Path(__file__).resolve().parent
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

import db  # noqa: E402  (Supabase-backed twin of store.py)
from ai_core import (PRIMARY_MODEL, SYSTEM_PROMPT, AINotReady, ensure_ready,
                     friendly_error, stream_reply)  # noqa: E402
from planner_core import MAX_DAYS, PLANNER_INSTRUCTIONS, _parse_plan, _valid_blocks  # noqa: E402

app = FastAPI(title="Student Command Center")

INDEX_FILE = WEB_DIR / "index.html"
MAX_WEB_HISTORY = 12
MAX_MESSAGE_CHARS = 2000

XP_PER_TASK = 15      # matches rewards.py on the desktop
XP_PER_EXAM = 50


class ChatRequest(BaseModel):
    message: str = ""
    history: list[dict] = Field(default_factory=list)
    access_code: str = ""


class TaskIn(BaseModel):
    title: str = ""
    due_at: str | None = None
    minutes: int | None = None
    subject: str | None = None


class TaskPatch(BaseModel):
    done: bool


class ExamIn(BaseModel):
    subject: str = ""
    occurs_at: str


class ExamResult(BaseModel):
    result: str = "done"
    marks: int | None = None


class SubjectIn(BaseModel):
    name: str = ""


class PlannerGenerate(BaseModel):
    subject: str = ""
    days: int = 7
    daily_minutes: int = 120
    focus: str = ""


class PlannerApply(BaseModel):
    subject: str = ""
    plan_title: str = ""
    days: list[dict] = Field(default_factory=list)


class SettingsIn(BaseModel):
    student_name: str | None = None
    daily_goal_minutes: int | None = None


def _check_access_code(provided: str = "", header_value: str = "") -> None:
    """Optional shared-secret gate so strangers cannot burn the Groq quota."""
    expected = os.getenv("STUDY_BUDDY_WEB_CODE", "").strip()
    if not expected:
        return
    if provided.strip() != expected and header_value.strip() != expected:
        raise HTTPException(status_code=401, detail="Wrong access code.")


def _gate(access_code: str = "", header_value: str = Header(default="")) -> None:
    _check_access_code(access_code, header_value)


# ------------------------------------------------------------------- helpers
def countdown(occurs_at: str) -> str:
    """Human countdown like the desktop Exams page: TODAY!, tomorrow, N days."""
    when = db.parse_dt(occurs_at)
    if when is None:
        return "?"
    now = datetime.now(db.IST)
    delta = (when.date() - now.date()).days
    if delta == 0:
        return "TODAY!"
    if delta == 1:
        return "tomorrow"
    if delta < 0:
        return f"{-delta}d ago"
    return f"in {delta} days"


def _exam_row(exam: dict) -> dict:
    row = dict(exam)
    row["countdown"] = countdown(exam["occurs_at"])
    return row


def _subject_rows() -> list[dict]:
    tasks = db.list_tasks()
    exams = db.list_exams(only_upcoming=True)
    rows = []
    for subject in db.list_subjects():
        name = subject["name"]
        next_exam = next((e for e in exams if e["subject"].lower() == name.lower()), None)
        rows.append({
            "name": name,
            "pending": sum(1 for t in tasks if t["subject"] == name and not t["done"]),
            "done": sum(1 for t in tasks if t["subject"] == name and t["done"]),
            "next_exam": next_exam["occurs_at"] if next_exam else None,
        })
    return rows


def _require_db() -> None:
    try:
        db.ensure_ready()
    except db.DBNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# --------------------------------------------------------------------- pages
@app.get("/favicon.ico")
@app.get("/favicon.png")
def favicon():
    return FileResponse(WEB_DIR / "favicon.png", media_type="image/png")


@app.get("/")
def home():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return JSONResponse({"detail": "index.html is missing from the deployment."}, status_code=500)


# ---------------------------------------------------------------------- info
@app.get("/api/health")
def health():
    data: dict = {"model": PRIMARY_MODEL}
    try:
        db.ensure_ready()
        data["db"] = "ok"
    except db.DBNotReady as exc:
        data["db"] = f"not_ready: {exc}"
    try:
        ensure_ready()
        data["ai"] = "ok"
    except AINotReady as exc:
        data["ai"] = f"not_ready: {exc}"
    data["status"] = "ok" if data.get("db") == "ok" and data.get("ai") == "ok" else "degraded"
    return data


# ----------------------------------------------------------------- dashboard
@app.get("/api/dashboard")
def dashboard(x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    tasks = db.list_tasks()
    today_str = db.today().isoformat()
    pending = [t for t in tasks if not t["done"]]
    done_today = [t for t in tasks if t["done"] and (t.get("completed_at") or "")[:10] == today_str]
    today_tasks = [t for t in tasks if (t.get("due_at") or "")[:10] == today_str]
    return {
        "student_name": db.get_setting("student_name", "Student"),
        "daily_goal_minutes": int(db.get_setting("daily_goal_minutes", "120") or 120),
        "level": db.level_progress(),
        "streak": db.study_streak(),
        "minutes_today": db.minutes_completed_on(db.today()),
        "pending_count": len(pending),
        "done_today_count": len(done_today),
        "next_exam": _exam_row(db.next_exam()) if db.next_exam() else None,
        "upcoming_exams": [_exam_row(e) for e in db.list_exams(only_upcoming=True)[:5]],
        "today_tasks": today_tasks,
        "pending_preview": pending[:5],
        "weekly": db.weekly_completed_counts(),
    }


# --------------------------------------------------------------------- tasks
@app.get("/api/tasks")
def tasks(filter: str = "all", x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    rows = db.list_tasks(include_done=filter != "pending")
    if filter == "done":
        rows = [r for r in rows if r["done"]]
    return rows


@app.post("/api/tasks")
def add_task(body: TaskIn, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Task title is empty.")
    task_id = db.add_task(body.title, due_at=body.due_at, minutes=body.minutes,
                          subject=body.subject or None)
    if body.subject:
        db.add_subject(body.subject)
    return {"id": task_id, "ok": True}


@app.patch("/api/tasks/{task_id}")
def patch_task(task_id: int, body: TaskPatch, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    db.set_task_done(task_id, body.done)
    xp, leveled_up, level = None, False, None
    if body.done:
        xp, leveled_up = db.add_xp(XP_PER_TASK)
        level = db.level_progress()
    return {"ok": True, "xp_gained": XP_PER_TASK if body.done else 0,
            "leveled_up": leveled_up, "level": level}


@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    db.delete_task(task_id)
    return {"ok": True}


# ------------------------------------------------------------------ subjects
@app.get("/api/subjects")
def subjects(x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    return _subject_rows()


@app.post("/api/subjects")
def add_subject(body: SubjectIn, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    if not db.add_subject(body.name):
        raise HTTPException(status_code=409, detail="Subject already exists (or is empty).")
    return {"ok": True}


@app.delete("/api/subjects/{name}")
def remove_subject(name: str, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    db.delete_subject(name)
    return {"ok": True}


# --------------------------------------------------------------------- exams
@app.get("/api/exams")
def exams(x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    return [_exam_row(e) for e in db.list_exams()]


@app.post("/api/exams")
def add_exam(body: ExamIn, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    if not body.subject.strip():
        raise HTTPException(status_code=400, detail="Exam subject is empty.")
    if db.parse_dt(body.occurs_at) is None:
        raise HTTPException(status_code=400, detail="Date must look like 2026-12-01 09:30.")
    exam_id = db.add_exam(body.subject, body.occurs_at)
    db.add_subject(body.subject)
    return {"id": exam_id, "ok": True}


@app.delete("/api/exams/{exam_id}")
def remove_exam(exam_id: int, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    db.delete_exam(exam_id)
    return {"ok": True}


@app.post("/api/exams/{exam_id}/result")
def exam_result(exam_id: int, body: ExamResult, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    db.set_exam_result(exam_id, body.result or "done", body.marks)
    xp, leveled_up = db.add_xp(XP_PER_EXAM)
    return {"ok": True, "xp_gained": XP_PER_EXAM, "leveled_up": leveled_up,
            "level": db.level_progress()}


# ------------------------------------------------------------------- planner
@app.post("/api/planner/generate")
def planner_generate(body: PlannerGenerate, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    subject = body.subject.strip()
    if not subject:
        raise HTTPException(status_code=400, detail="Pick or type an exam subject first.")
    days = max(1, min(body.days, MAX_DAYS))
    daily = max(30, min(body.daily_minutes, 480))
    focus = body.focus.strip() or "none mentioned"

    exam = db.next_exam()
    exam_line = (f"{exam['subject']} on {exam['occurs_at']}"
                 if exam and exam["subject"].lower() == subject.lower()
                 else f"{subject} (no date saved - plan for it being after the {days} days)")
    prompt = (
        f"Exam subject: {exam_line}\n"
        f"Days available: {days} (day 0 = today, {db.today().isoformat()})\n"
        f"Daily study minutes: {daily}\n"
        f"Focus topics from the student: {focus}\n"
        "Create the plan now as the JSON object."
    )

    messages = [
        {"role": "system", "content": PLANNER_INSTRUCTIONS},
        {"role": "user", "content": prompt},
    ]
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            ensure_ready()
            reply = "".join(stream_reply(messages))
        except AINotReady as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=friendly_error(exc))
        try:
            plan = _parse_plan(reply)
            valid = _valid_blocks(plan, days_available=days, daily_minutes=daily,
                                  today=db.today())
            if not valid:
                raise ValueError("plan empty after validation")
            return {
                "plan_title": plan.get("plan_title", f"{subject} plan"),
                "subject": subject,
                "days": valid,
                "block_count": sum(len(d["blocks"]) for d in valid),
                "total_minutes": sum(b["minutes"] for d in valid for b in d["blocks"]),
            }
        except Exception as exc:  # noqa: BLE001 - bad JSON from the model, retry once
            last_error = exc
            messages = messages + [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": "That was not valid JSON for the schema. "
                 "Reply again with ONLY the JSON object, nothing else."},
            ]
    raise HTTPException(status_code=502, detail="The model could not produce a valid plan. "
                         f"Try again. (Last error: {last_error})")


@app.post("/api/planner/apply")
def planner_apply(body: PlannerApply, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    subject = body.subject.strip()
    if not subject or not body.days:
        raise HTTPException(status_code=400, detail="Nothing to save - generate a plan first.")
    total_minutes = sum(b["minutes"] for d in body.days for b in d.get("blocks", []))
    plan_id = db.add_plan(body.plan_title.strip() or f"{subject} plan", subject, total_minutes)
    for day in body.days:
        for block in day.get("blocks", []):
            db.add_task(block["title"], due_at=block.get("due_at"),
                        minutes=block.get("minutes"), subject=subject,
                        plan_id=plan_id, created_by="ai")
    db.add_subject(subject)
    count = sum(len(d.get("blocks", [])) for d in body.days)
    return {"ok": True, "plan_id": plan_id, "tasks_added": count}


@app.get("/api/planner/latest")
def planner_latest(x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    plans = db.list_plans(limit=1)
    if not plans:
        return None
    plan = plans[0]
    all_plan_tasks = db.list_tasks(plan_id=plan["id"])
    pending = sum(1 for t in all_plan_tasks if not t["done"])
    return {**plan, "tasks_total": len(all_plan_tasks), "tasks_pending": pending}


# ------------------------------------------------------------------ progress
@app.get("/api/progress")
def progress(x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    goal = int(db.get_setting("daily_goal_minutes", "120") or 120)
    minutes_today = db.minutes_completed_on(db.today())
    return {
        "level": db.level_progress(),
        "streak": db.study_streak(),
        "minutes_today": minutes_today,
        "daily_goal_minutes": goal,
        "goal_percent": min(100, round(minutes_today / goal * 100)) if goal else 0,
        "weekly": db.weekly_completed_counts(),
        "subjects": db.subject_progress(),
        "exams_completed": db.completed_exam_count(),
    }


# ------------------------------------------------------------------ settings
@app.get("/api/settings")
def get_settings(x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    return {
        "student_name": db.get_setting("student_name", "Student"),
        "daily_goal_minutes": int(db.get_setting("daily_goal_minutes", "120") or 120),
        "level": db.level_progress(),
    }


@app.post("/api/settings")
def update_settings(body: SettingsIn, x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    if body.student_name is not None and body.student_name.strip():
        db.set_setting("student_name", body.student_name.strip())
    if body.daily_goal_minutes is not None:
        db.set_setting("daily_goal_minutes", str(max(15, min(body.daily_goal_minutes, 720))))
    return {"ok": True}


@app.post("/api/reset")
def reset(x_access_code: str = Header(default="")):
    _gate(header_value=x_access_code)
    _require_db()
    db.reset_all()
    return {"ok": True}


# ----------------------------------------------------------------------- AI
@app.post("/api/chat")
def chat(body: ChatRequest):
    _gate(body.access_code)

    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise HTTPException(status_code=400, detail=f"Message too long (max {MAX_MESSAGE_CHARS} characters).")

    history: list[dict] = []
    for item in body.history[-MAX_WEB_HISTORY:]:
        role = item.get("role")
        content = str(item.get("content", ""))[:6000]
        if role in ("user", "assistant") and content.strip():
            history.append({"role": role, "content": content})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": message},
    ]

    try:
        ensure_ready()
        reply = "".join(stream_reply(messages))
    except AINotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - mapped for the client
        raise HTTPException(status_code=502, detail=friendly_error(exc))

    if not reply:
        raise HTTPException(status_code=502, detail="The model returned an empty answer. Try again.")

    return {"reply": reply, "model": PRIMARY_MODEL}