"""Study Buddy web app - FastAPI, deployed on Vercel.

The desktop app (study_buddy.py) and this web app share the same AI logic
in ai_core.py. This file only handles HTTP.

Deployed as the Vercel project root directory `web`, which auto-detects
FastAPI from requirements.txt and this entrypoint (top-level `app`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from ai_core import PRIMARY_MODEL, SYSTEM_PROMPT, AINotReady, ensure_ready, friendly_error, stream_reply

app = FastAPI(title="Study Buddy AI")

INDEX_FILE = WEB_DIR / "index.html"
MAX_WEB_HISTORY = 12
MAX_MESSAGE_CHARS = 2000


class ChatRequest(BaseModel):
    message: str = ""
    history: list[dict] = Field(default_factory=list)
    access_code: str = ""


def _check_access_code(provided: str) -> None:
    """Optional shared-secret gate so strangers cannot burn the Groq quota."""
    expected = os.getenv("STUDY_BUDDY_WEB_CODE", "").strip()
    if not expected:
        return
    if provided.strip() != expected:
        raise HTTPException(status_code=401, detail="Wrong access code.")


@app.get("/favicon.ico")
@app.get("/favicon.png")
def favicon():
    return FileResponse(WEB_DIR / "favicon.png", media_type="image/png")


@app.get("/")
def home():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return JSONResponse({"detail": "index.html is missing from the deployment."}, status_code=500)


@app.get("/api/health")
def health():
    try:
        ensure_ready()
        return {"status": "ok", "model": PRIMARY_MODEL}
    except AINotReady as exc:
        return {"status": "not_ready", "detail": str(exc)}


@app.post("/api/chat")
def chat(body: ChatRequest):
    _check_access_code(body.access_code)

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