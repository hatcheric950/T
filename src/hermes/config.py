from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SESSIONS_DIR = HERMES_HOME / "sessions"
SKILLS_DIR = HERMES_HOME / "skills"

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"
DEFAULT_TOOLSETS = ("web", "terminal", "skills")


@dataclass
class Config:
    model: str = DEFAULT_MODEL
    provider: str | None = None  # auto-detected from model prefix if None
    toolsets: tuple[str, ...] = DEFAULT_TOOLSETS
    skills: tuple[str, ...] = ()
    verbose: bool = False
    system_prompt: str = "You are Hermes, a helpful CLI agent."
    extra: dict = field(default_factory=dict)

    def resolve_provider(self) -> str:
        if self.provider:
            return self.provider
        if "/" in self.model:
            vendor = self.model.split("/", 1)[0].lower()
            if vendor in {"anthropic", "openrouter", "nous"}:
                return vendor
        return "anthropic"


def ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
