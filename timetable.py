"""Exam timetable import - read a PDF, let GPT-OSS pull out the exams.

Pure logic + a QThread worker. The model proposes; Python validates every
row (real dates, sane times) before anything is shown to the student.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta

from PySide6.QtCore import QThread, Signal

from web.ai_core import friendly_error, stream_reply

EXTRACTION_INSTRUCTIONS = """You extract exam entries from an exam timetable. \
Reply with ONLY a JSON object - no markdown fences, no commentary.

Schema:
{"exams": [{"subject": string, "date": "YYYY-MM-DD", "time": "HH:MM"}]}

Rules:
- Timetables often omit the year. Use the provided current date to work it out, \
and if a date would already be in the past, assume next year.
- "time" is 24-hour "HH:MM". Use "09:00" when the timetable does not say a time.
- "subject" is the clean subject name ("Physics", not "PHY-101 Paper 2"); keep \
level or session words like Paper/Turns/Session out of the subject.
- Include only real exam entries. Ignore headers, instructions, seating plans \
and rule text.
- Do not invent exams that are not in the text."""


def extract_pdf_text(path: str) -> str:
    """Read all text from a PDF. Raises ValueError for unreadable/scanned PDFs."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - a broken page should not kill the import
            continue
    text = "\n".join(pages).strip()
    if len(text) < 30:
        raise ValueError(
            "No readable text in that PDF. If it is a scanned photo, it needs OCR first."
        )
    return text


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    return json.loads(text[start:end + 1])


def validate_exams(raw_text: str, today: date | None = None) -> list[dict]:
    """Turn the model's JSON into trustworthy rows, newest-proof and de-duplicated."""
    today = today or date.today()
    data = _parse_json(raw_text)
    entries = data.get("exams") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ValueError("no exam list found")

    valid: list[dict] = []
    seen: set[tuple[str, str]] = set()
    existing = {(e["subject"].lower(), e["occurs_at"][:10]) for e in _existing_exams()}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        subject = str(entry.get("subject", "")).strip()
        raw_date = str(entry.get("date", "")).strip()
        raw_time = str(entry.get("time", "")).strip()
        if not subject or len(subject) > 60:
            continue
        try:
            exam_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if exam_date < today - timedelta(days=1):
            continue
        try:
            exam_time = datetime.strptime(raw_time, "%H:%M").time()
        except ValueError:
            exam_time = datetime.strptime("09:00", "%H:%M").time()

        key = (subject.lower(), exam_date.isoformat())
        if key in seen or key in existing:
            continue
        seen.add(key)
        valid.append({
            "subject": subject,
            "occurs_at": f"{exam_date.isoformat()} {exam_time.strftime('%H:%M')}",
        })
    return valid


def _existing_exams() -> list[dict]:
    import store

    return store.list_exams()


class TimetableWorker(QThread):
    """Reads the timetable via the AI off the GUI thread."""

    done = Signal(list)      # list[dict] of validated exams
    failed = Signal(str)

    def __init__(self, pdf_path: str, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path

    def run(self) -> None:
        try:
            text = extract_pdf_text(self.pdf_path)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.failed.emit(str(exc))
            return

        prompt = (
            f"Today's date: {date.today().isoformat()} ({date.today().strftime('%A')})\n\n"
            f"Exam timetable text:\n\"\"\"\n{text[:12000]}\n\"\"\"\n\n"
            "Extract the exams now as the JSON object."
        )
        messages = [
            {"role": "system", "content": EXTRACTION_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ]

        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                reply = "".join(stream_reply(messages))
            except Exception as exc:  # noqa: BLE001
                self.failed.emit(friendly_error(exc))
                return
            try:
                self.done.emit(validate_exams(reply))
                return
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                messages = messages + [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content": "That was not valid JSON for the schema. "
                     "Reply again with ONLY the JSON object."},
                ]

        self.failed.emit("Could not find any exams in that timetable. "
                         f"Try again or add them manually. ({last_error})")