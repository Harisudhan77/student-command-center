# Student Command Center

A PySide6 desktop app for tracking exams, tasks and study progress.

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

Click **🤖 Study Buddy AI** in the sidebar to open the tutor chat.

You can also run the chat on its own:

```powershell
python study_buddy.py
```

## Web version (`web/`)

The same Study Buddy runs in a browser, deployed on **Vercel**:

- `web/ai_core.py` — the shared AI brain (also imported by the desktop app)
- `web/app.py` — FastAPI app (Vercel auto-detects it from this entrypoint)
- `web/index.html` — the chat page

Deploy settings: Vercel project with **Root Directory = `web`**, and
`GROQ_API_KEY` set in the project's environment variables. Optionally set
`STUDY_BUDDY_WEB_CODE` to require an access code with every request, so
strangers cannot burn the Groq quota.

Run the web app locally:

```powershell
pip install uvicorn
python -m uvicorn web.app:app
```

## Study Buddy AI

- Model: `openai/gpt-oss-120b` on Groq (falls back to `openai/gpt-oss-20b` automatically
  if the big model is unavailable).
- Replies stream in live and keep conversation context.
- **New chat** clears the conversation.
- Enter sends, Shift+Enter adds a new line.

Optional `.env` tuning:

```
STUDY_BUDDY_MODEL=openai/gpt-oss-20b   # smaller + faster
STUDY_BUDDY_REASONING=medium           # low | medium | high
```

## Notes

- The `.venv` folder in the parent directory was created on Linux and will not work on
  Windows. Delete it and run `python -m venv .venv` here if you want a local environment.
- Never commit `.env` - it is already listed in the repo's `.gitignore`.
