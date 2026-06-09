from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from hermes.watcher.policy import Policy
from hermes.watcher.settings import Settings
from hermes.watcher.state import State
from hermes.watcher.types import InboundMessage


def _msg(sender="alice@example.com", channel="email", mid="m1"):
    return InboundMessage(channel=channel, sender=sender, body="hi", message_id=mid)


def _settings(tmp: Path, mode="shadow") -> Settings:
    allow = tmp / "allow.yaml"
    allow.write_text(
        "emails:\n  - alice@example.com\n  - '*@trusted.com'\nphones:\n  - '+15551234567'\n"
    )
    return Settings(
        HERMES_MODE=mode,
        ALLOWLIST_PATH=str(allow),
        PAUSE_FILE=str(tmp / "PAUSE"),
        STATE_DB=str(tmp / "state.db"),
        RATE_HOURLY=2,
        RATE_PER_SENDER_DAILY=1,
        DAILY_SMS_BUDGET_USD=1.0,
    )


async def _open(tmp: Path, mode="shadow") -> tuple[Policy, State]:
    s = _settings(tmp, mode)
    st = State(s.state_db)
    await st.open()
    return Policy(s, st), st


@pytest.mark.asyncio
async def test_allowlist_exact_match(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        d = await policy.evaluate(_msg())
        assert d.action == "reply"
    finally:
        await st.close()


@pytest.mark.asyncio
async def test_allowlist_wildcard(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        d = await policy.evaluate(_msg(sender="bob@trusted.com"))
        assert d.action == "reply"
    finally:
        await st.close()


@pytest.mark.asyncio
async def test_not_allowlisted_drops(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        d = await policy.evaluate(_msg(sender="stranger@nope.com"))
        assert d.action == "drop_not_allowlisted"
    finally:
        await st.close()


@pytest.mark.asyncio
async def test_denylist_pattern(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        d = await policy.evaluate(_msg(sender="noreply@trusted.com"))
        assert d.action == "drop_denylisted"
    finally:
        await st.close()


@pytest.mark.asyncio
async def test_pause_file_blocks(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        Path(policy.settings.pause_file).touch()
        d = await policy.evaluate(_msg())
        assert d.action == "drop_paused"
    finally:
        await st.close()


@pytest.mark.asyncio
async def test_hourly_rate_cap(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        for i in range(2):
            await st.log_audit(
                channel="email", sender=f"a{i}@trusted.com", message_id=f"x{i}",
                decision="sent", sent=True,
            )
        d = await policy.evaluate(_msg(sender="alice@example.com"))
        assert d.action == "drop_rate_hourly"
    finally:
        await st.close()


@pytest.mark.asyncio
async def test_per_sender_daily_cap(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        await st.log_audit(
            channel="email", sender="alice@example.com", message_id="x",
            decision="sent", sent=True,
        )
        d = await policy.evaluate(_msg())
        assert d.action == "drop_rate_sender"
    finally:
        await st.close()


@pytest.mark.asyncio
async def test_sms_budget_cap(tmp_path):
    policy, st = await _open(tmp_path)
    try:
        await st.log_audit(
            channel="sms", sender="+15559999999", message_id="x",
            decision="sent", sent=True, cost_usd=1.0,
        )
        d = await policy.evaluate(_msg(sender="+15551234567", channel="sms", mid="m2"))
        assert d.action == "drop_sms_budget"
    finally:
        await st.close()
