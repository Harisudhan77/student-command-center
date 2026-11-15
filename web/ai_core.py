"""Shared AI core for Study Buddy - talks to Groq (GPT-OSS), no GUI code.

Used by:
  - study_buddy.py    (desktop chat, imports this as web.ai_core)
  - web/app.py        (web chat, FastAPI on Vercel)

The key is read from the first .env found: the project root (STUDENT COMMAND
CENTER/.env) or this folder. On Vercel it comes from the project's environment
variables instead.

Optional .env overrides:
    STUDY_BUDDY_MODEL=openai/gpt-oss-20b   # faster / cheaper model
    STUDY_BUDDY_REASONING=medium            # low | medium | high
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

try:
    from groq import Groq

    _GROQ_IMPORT_OK = True
except ImportError:
    Groq = None
    _GROQ_IMPORT_OK = False

APP_DIR = Path(__file__).resolve().parent
ENV_CANDIDATES = (APP_DIR.parent / ".env", APP_DIR / ".env")

PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"
REASONING_EFFORT = "low"
MAX_COMPLETION_TOKENS = 2048

SYSTEM_PROMPT = """You are Study Buddy, a friendly and patient tutor helping a \
school/college student in India.

How you answer:
- Be warm, encouraging and plain-spoken. No lecturing.
- Explain in short numbered steps, then give ONE short worked example.
- Use simple analogies when a concept is abstract.
- Keep answers compact by default (under 250 words). Expand only if asked.
- For maths and science, show the reasoning, not just the final answer.
- If the student asks for a plan or timetable, give day-by-day actionable items.
- If the student is stuck on homework, give hints and guiding questions first.
  Only give the full solution if they ask for it directly.
- End with one short follow-up question or suggestion to keep them learning.
- If a question is outside studying, gently steer back to their studies.

Use Markdown lightly: short headings, bullet points, **bold** for key terms, \
and fenced code blocks for code."""


class AINotReady(Exception):
    """Raised when the AI cannot be used yet, with a message meant for the user."""


def _load_env() -> None:
    """Load the first .env found, with python-dotenv if installed, else a tiny parser."""
    env_file = next((path for path in ENV_CANDIDATES if path.exists()), None)
    if env_file is None:
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
        return
    except ImportError:
        pass

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


_load_env()

PRIMARY_MODEL = os.getenv("STUDY_BUDDY_MODEL", PRIMARY_MODEL)
REASONING_EFFORT = os.getenv("STUDY_BUDDY_REASONING", REASONING_EFFORT)

_client: Groq | None = None


def ensure_ready() -> None:
    """Raise AINotReady with a user-friendly reason if the AI cannot be used."""
    global _client

    if not _GROQ_IMPORT_OK:
        raise AINotReady("The 'groq' package is missing. Run:  pip install groq python-dotenv")

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise AINotReady(f"No GROQ_API_KEY found. Add it to {ENV_CANDIDATES[0]}")

    if _client is None:
        _client = Groq(api_key=api_key)


def friendly_error(exc: Exception) -> str:
    """Turn a raw API exception into something a student can act on."""
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    detail = str(exc).strip()
    if len(detail) > 300:
        detail = detail[:300] + "..."

    if status == 401:
        return "Groq rejected the API key (401). Check GROQ_API_KEY in .env."
    if status == 403:
        return "This API key is not allowed to use that model (403)."
    if status == 404:
        return f"Model not available on your account (404). {detail}"
    if status == 429:
        return "Rate limit reached (429). Wait a few seconds and try again."
    if status == 400:
        return f"The request was rejected (400). {detail}"
    if "Connection" in name or "connect" in detail.lower():
        return "Could not reach Groq. Check your internet connection."
    return f"{name}: {detail}"


def stream_reply(messages: list[dict], model: str = PRIMARY_MODEL) -> Iterator[str]:
    """Ask the model and yield the reply piece by piece.

    Tries the primary model first, then FALLBACK_MODEL if nothing was produced.
    Raises the last exception if every attempt fails - pass it to friendly_error().
    """
    ensure_ready()
    assert _client is not None

    models = [model] if model == FALLBACK_MODEL else [model, FALLBACK_MODEL]

    for index, candidate in enumerate(models):
        received: list[str] = []
        kwargs = {
            "model": candidate,
            "messages": messages,
            "temperature": 0.6,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "top_p": 0.95,
            "stream": True,
            "reasoning_effort": REASONING_EFFORT,
            "include_reasoning": False,
        }

        try:
            try:
                stream = _client.chat.completions.create(**kwargs)
            except TypeError:
                # Older SDKs do not know the reasoning parameters.
                kwargs.pop("reasoning_effort", None)
                kwargs.pop("include_reasoning", None)
                stream = _client.chat.completions.create(**kwargs)

            for event in stream:
                if not event.choices:
                    continue
                piece = event.choices[0].delta.content
                if piece:
                    received.append(piece)
                    yield piece

            return

        except Exception:  # noqa: BLE001 - caller maps it via friendly_error()
            is_last_model = index == len(models) - 1
            # Fall back to the smaller model only if nothing was shown yet.
            if not received and not is_last_model:
                continue
            raise