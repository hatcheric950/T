"""Minimal .env file loader — no external dependencies."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_files() -> None:
    for path in [Path.home() / ".happy" / ".env", Path.cwd() / ".env"]:
        if path.exists():
            _parse(path)


def _unquote(value: str) -> str:
    for q in ('"', "'"):
        if value.startswith(q) and value.endswith(q) and len(value) >= 2:
            return value[1:-1]
    # strip trailing inline comment
    if " #" in value:
        value = value[: value.index(" #")]
    return value.strip()


def _parse(path: Path) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        if key:
            os.environ.setdefault(key, _unquote(raw.strip()))
