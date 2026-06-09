from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from hermes.watcher.classifier import Classifier
from hermes.watcher.pipeline import Pipeline
from hermes.watcher.policy import Policy
from hermes.watcher.settings import Settings
from hermes.watcher.state import State
from hermes.watcher.twilio_webhook import build_app


WEBHOOK_URL = "https://hermes.example.com/sms/inbound"
AUTH_TOKEN = "test_token_xyz"


def _settings(tmp: Path) -> Settings:
    allow = tmp / "allow.yaml"
    allow.write_text("emails: []\nphones: ['+15551234567']\n")
    return Settings(
        HERMES_MODE="shadow",
        ALLOWLIST_PATH=str(allow),
        PAUSE_FILE=str(tmp / "PAUSE"),
        STATE_DB=str(tmp / "state.db"),
        HERMES_HOME=str(tmp / "home"),
        TWILIO_AUTH_TOKEN=AUTH_TOKEN,
        TWILIO_WEBHOOK_URL=WEBHOOK_URL,
        ANTHROPIC_API_KEY="",
    )


@pytest.fixture
async def app_and_state(tmp_path):
    s = _settings(tmp_path)
    st = State(s.state_db); await st.open()
    pipeline = Pipeline(s, st, Policy(s, st), Classifier(s, st))
    yield build_app(s, pipeline), st
    await st.close()


@pytest.mark.asyncio
async def test_valid_signature_accepted(app_and_state):
    app, _ = app_and_state
    form = {"From": "+15551234567", "Body": "hi", "MessageSid": "SM123"}
    sig = RequestValidator(AUTH_TOKEN).compute_signature(WEBHOOK_URL, form)

    async def fake_draft(_s, _m): return "hi back"
    with patch("hermes.watcher.pipeline.draft", fake_draft):
        with TestClient(app) as client:
            r = client.post("/sms/inbound", data=form, headers={"X-Twilio-Signature": sig})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")


@pytest.mark.asyncio
async def test_tampered_body_rejected(app_and_state):
    app, _ = app_and_state
    form = {"From": "+15551234567", "Body": "hi", "MessageSid": "SM123"}
    sig = RequestValidator(AUTH_TOKEN).compute_signature(WEBHOOK_URL, form)
    tampered = dict(form, Body="MALICIOUS")
    with TestClient(app) as client:
        r = client.post("/sms/inbound", data=tampered, headers={"X-Twilio-Signature": sig})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_healthz(app_and_state):
    app, _ = app_and_state
    with TestClient(app) as client:
        r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
