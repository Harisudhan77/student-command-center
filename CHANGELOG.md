# Changelog

All notable changes to Student Command Centre are documented here.

## v1.0.0 — 2026-11-16

First public release.

### Added
- **Dashboard** — upcoming exams, tasks completed, pending tasks, exam countdown,
  weekly activity chart
- **Tasks** — add/complete/delete tasks with due dates and filters
- **Subjects** — manage subjects with per-subject task counts and next exam
- **Exams** — add exams with live countdowns, log results after they pass
- **Progress** — streak, minutes today, weekly chart, per-subject progress bars
- **Study Buddy AI** — GPT-OSS tutor chat (Groq) with streaming replies
- **Study Planner** — AI-generated day-by-day study plans, previewed and
  approved before becoming tasks
- **Timetable import** — read exam timetable PDFs and import exams automatically
- **Notifications & rewards** — XP, levels, streak celebrations, praise toasts,
  exam check-ins, due/overdue task digests (system tray)
- **Web version** — Study Buddy chat in the browser (FastAPI, deployed on Vercel)
- **Settings** — profile name, daily study goal, background-running toggle,
  full data reset
- **Persistence** — SQLite storage that survives restarts
