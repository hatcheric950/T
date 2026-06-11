from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .config import SESSIONS_DIR, ensure_dirs


@dataclass
class Message:
    role: str
    content: object  # str or list[dict] (Anthropic structured content blocks)
    ts: float = field(default_factory=time.time)


@dataclass
class Session:
    id: str
    model: str
    provider: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: list[Message] = field(default_factory=list)

    @classmethod
    def new(cls, model: str, provider: str) -> "Session":
        return cls(id=uuid.uuid4().hex[:12], model=model, provider=provider)

    def path(self) -> Path:
        return SESSIONS_DIR / f"{self.id}.json"

    def add(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
        self.updated_at = time.time()

    def save(self) -> None:
        ensure_dirs()
        data = asdict(self)
        self.path().write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, session_id: str) -> "Session":
        path = SESSIONS_DIR / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"No session: {session_id}")
        data = json.loads(path.read_text())
        msgs = [Message(**m) for m in data.pop("messages", [])]
        return cls(messages=msgs, **data)

    @classmethod
    def most_recent(cls) -> "Session | None":
        ensure_dirs()
        files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return None
        return cls.load(files[0].stem)
