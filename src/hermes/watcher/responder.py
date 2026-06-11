from __future__ import annotations

import asyncio
from pathlib import Path

from ..agent import Agent
from ..config import Config, SESSIONS_DIR
from ..session import Session
from .settings import Settings
from .types import InboundMessage


def _agent_for(settings: Settings, msg: InboundMessage) -> Agent:
    sid = msg.session_id()
    path = SESSIONS_DIR / f"{sid}.json"
    cfg = Config(model=settings.model, verbose=False, toolsets=())
    if path.exists():
        session = Session.load(sid)
    else:
        session = Session(id=sid, model=cfg.model, provider=cfg.resolve_provider())
    return Agent(config=cfg, session=session)


def _format_input(msg: InboundMessage) -> str:
    if msg.channel == "email":
        return (
            f"You received an email.\nFrom: {msg.sender}\nSubject: {msg.subject}\n\n"
            f"{msg.body}\n\nReply briefly and naturally, as the recipient."
        )
    return (
        f"You received a text message from {msg.sender}:\n\n{msg.body}\n\n"
        f"Reply briefly (max 320 characters), as the recipient."
    )


async def draft(settings: Settings, msg: InboundMessage) -> str:
    agent = _agent_for(settings, msg)
    prompt = _format_input(msg)
    return await asyncio.to_thread(agent.send, prompt)
