"""File locations that work both when running from source and as a PyInstaller exe.

- base_dir(): read-only resources bundled with the app (icons, splash art)
- data_dir(): writable location for the user's database and .env
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def base_dir() -> Path:
    """Where bundled resources live (PyInstaller's _MEIPASS when frozen)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    """Where the app may write. Next to the exe for portable distribution."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def env_candidates() -> list[Path]:
    """Places to look for .env: beside the exe first when frozen."""
    candidates = [data_dir() / ".env"]
    if not is_frozen():
        candidates += [base_dir().parent / ".env", base_dir() / ".env"]
    return candidates