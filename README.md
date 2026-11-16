# Student Command Center

A PySide6 desktop app for tracking exams, tasks and study progress — with an
AI tutor and an AI study planner powered by **GPT-OSS on Groq**.

## Setup

```powershell
pip install -r requirements.txt
```

Create a file named `.env` in this folder (next to `main.py`) with your Groq key:

```
GROQ_API_KEY=gsk_your_key_here
```

Get a free key at https://console.groq.com/keys

## Run

```powershell
python main.py
```

## The menus (all inside the one main window)

| Menu | What it does |
|---|---|
| 📊 Dashboard | Upcoming exams, tasks completed, pending tasks, exam countdown, weekly activity |
| 📋 Tasks | Add / complete / delete tasks, filter all-pending-done |
| 📚 Subjects | Manage subjects, see done/pending counts and next exam per subject |
| 🎯 Exams | Add exams with date & time, live countdowns |
| 📈 Progress | Streak, minutes today, weekly chart, per-subject progress bars |
| 🤖 Study Buddy AI | Chat tutor (GPT-OSS via Groq), streaming replies |
| 📆 Study Planner | AI builds a day-by-day study plan → you approve → it becomes real tasks |
| ⚙️ Settings | Your name, daily study goal, reset-all-data |

Everything is stored in **SQLite** (`data/planner.db`) via `store.py`, so your
tasks and exams survive restarts. Delete the file to start fresh.

## Study Planner

1. Pick the exam subject, plan length (days) and study minutes per day.
2. Click **Generate plan** — the AI returns a day-by-day plan (JSON, validated by the app).
3. Review the preview, then **Add this plan to my tasks** — the blocks become real
   tasks on your dashboard, tagged with the subject.

Nothing is saved until you approve. The model's output is clamped and validated
(day offsets in range, sane times, minutes 15–180) before it touches your data.

## Web version (`web/`)

The same Study Buddy brain runs in a browser, deployed on **Vercel**:
`web/ai_core.py` is shared by the desktop app and `web/app.py` (FastAPI).

Deploy settings: Vercel project with **Root Directory = `web`** and
`GROQ_API_KEY` in the project's environment variables. Optionally set
`STUDY_BUDDY_WEB_CODE` to require an access code with every request.

## Project layout

```
main.py            window shell: sidebar + page stack
store.py           SQLite storage (tasks, exams, subjects, plans, settings)
ui_theme.py        shared colors/styles
dashboard.py       📊   tasks.py        📋   subjects.py   📚
exams.py           🎯   progress.py     📈   settings.py   ⚙️
planner.py         📆 AI study plan generator
study_buddy.py     🤖 chat page (embeddable widget)
web/               FastAPI web version (Vercel)
```

## Notes

- The `.venv` folder in the parent directory was created on Linux and will not
  work on Windows. Delete it and run `python -m venv .venv` if you want a local env.
- Never commit `.env` — it is already listed in the repo's `.gitignore`.
