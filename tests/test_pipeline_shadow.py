from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hermes.watcher.classifier import Classifier
from hermes.watcher.pipeline import Pipeline
from hermes.watcher.policy import Policy
from hermes.watcher.settings import Settings
from hermes.watcher.state import State
from hermes.watcher.types import InboundMessage


def _settings(tmp: Path) -> Settings:
    allow = tmp / "allow.yaml"
    allow.write_text("emails:\n  - alice@example.com\nphones: []\n")
    return Settings(
        HERMES_MODE="shadow",
        ALLOWLIST_PATH=str(allow),
        PAUSE_FILE=str(tmp / "PAUSE"),
        STATE_DB=str(tmp / "state.db"),
        HERMES_HOME=str(tmp / "home"),
        ANTHROPIC_API_KEY="",
    )


@pytest.mark.asyncio
async def test_shadow_mode_drafts_but_does_not_send(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    st = State(s.state_db); await st.open()
    pipeline = Pipeline(s, st, Policy(s, st), Classifier(s, st))

    msg = InboundMessage(
        channel="email", sender="alice@example.com",
        body="Hey, what time tomorrow?", message_id="<m@x>", subject="meeting",
    )

    async def fake_draft(_s, _m): return "Sure, 3pm works."

    sent = {"email": 0, "sms": 0}
    async def boom_email(*a, **k): sent["email"] += 1; raise AssertionError("must not send")
    async def boom_sms(*a, **k): sent["sms"] += 1; raise AssertionError("must not send")

    with patch("hermes.watcher.pipeline.draft", fake_draft), \
         patch("hermes.watcher.pipeline.send_email_reply", boom_email), \
         patch("hermes.watcher.pipeline.send_sms_reply", boom_sms):
        result = await pipeline.handle(msg)

    assert result == "shadow_would_send"
    assert sent == {"email": 0, "sms": 0}

    async with st.db.execute(
        "SELECT decision, draft, sent FROM audit WHERE message_id=?", (msg.message_id,)
    ) as cur:
        row = await cur.fetchone()
    assert row[0] == "shadow_would_send"
    assert "3pm" in row[1]
    assert row[2] == 0
    await st.close()


@pytest.mark.asyncio
async def test_duplicate_dropped(tmp_path):
    s = _settings(tmp_path)
    st = State(s.state_db); await st.open()
    pipeline = Pipeline(s, st, Policy(s, st), Classifier(s, st))
    msg = InboundMessage(channel="email", sender="alice@example.com",
                         body="hi", message_id="<dup@x>")

    async def fake_draft(_s, _m): return "ok"
    with patch("hermes.watcher.pipeline.draft", fake_draft):
        first = await pipeline.handle(msg)
        second = await pipeline.handle(msg)
    assert first == "shadow_would_send"
    assert second == "drop_duplicate"
    await st.close()
