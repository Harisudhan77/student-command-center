"""Pure study-planner logic shared by the desktop app and the web app.

Extracted from planner.py so the web API can use it without importing
PySide6 (which is GUI-only and not installed on the server). planner.py
re-exports these names, so the desktop app and tests keep working.

No GUI code, no database code - only parsing and validation.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

MAX_DAYS = 14

PLANNER_INSTRUCTIONS = """You are a study planner. Reply with ONLY a JSON object - \
no markdown fences, no explanation before or after.

Schema:
{"plan_title": string, "days": [{"day_offset": integer, "blocks": \
[{"title": string, "start_time": "HH:MM", "minutes": integer}]}]}

Rules:
- day_offset counts from 0 = today, up to the number of days available minus 1.
- 1 to 4 blocks per day; every block: minutes between 15 and 180, total per day \
must not exceed the daily study minutes.
- Order topics from hardest/most unfamiliar to easiest across the whole plan.
- Mix explanation, practice problems and revision. The final day should be revision.
- Titles are short and specific (e.g. "Kinematics - numericals practice"), never "Study".
- start_time is 24-hour "HH:MM".


Student request:
"""


def _parse_plan(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    data = json.loads(text[start:end + 1])
    if not isinstance(data.get("days"), list) or not data["days"]:
        raise ValueError("plan has no days")
    return data


def _valid_blocks(plan: dict, days_available: int, daily_minutes: int,
                  today: date | None = None) -> list[dict]:
    """Clamp and validate the model's output into trustworthy rows."""
    today = today or date.today()
    valid_days = []
    for day in plan.get("days", []):
        if not isinstance(day, dict):
            continue
        offset = day.get("day_offset")
        if not isinstance(offset, int):
            try:
                offset = int(offset)
            except (TypeError, ValueError):
                continue
        offset = max(0, min(offset, days_available - 1, MAX_DAYS - 1))

        blocks = []
        total = 0
        for block in day.get("blocks", []) or []:
            if not isinstance(block, dict):
                continue
            title = str(block.get("title", "")).strip()
            minutes = block.get("minutes")
            start_time = str(block.get("start_time", "")).strip()
            if not title or not re.fullmatch(r"\d{1,2}:\d{2}", start_time):
                continue
            if not isinstance(minutes, int):
                try:
                    minutes = int(float(minutes))
                except (TypeError, ValueError):
                    continue
            minutes = max(15, min(minutes, 180))
            if total + minutes > daily_minutes * 2:  # hard sanity cap
                continue
            total += minutes
            when = today + timedelta(days=offset)
            start_time = start_time if len(start_time) == 5 else "0" + start_time
            blocks.append({
                "title": title,
                "start_time": start_time,
                "due_at": f"{when.isoformat()} {start_time}",
                "minutes": minutes,
            })
        if blocks:
            valid_days.append({"offset": offset, "blocks": blocks})
    return valid_days