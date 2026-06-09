from __future__ import annotations

import asyncio

from twilio.rest import Client

from .settings import Settings


def _trim_sms(body: str, limit: int = 1500) -> str:
    body = body.strip()
    return body if len(body) <= limit else body[: limit - 1] + "…"


async def send_sms_reply(settings: Settings, to_number: str, body: str) -> float:
    """Send SMS via Twilio REST. Returns the estimated cost in USD."""
    body = _trim_sms(body)
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    def _send():
        client.messages.create(from_=settings.twilio_from_number, to=to_number, body=body)

    await asyncio.to_thread(_send)
    segments = max(1, (len(body) + 159) // 160)
    return segments * settings.sms_unit_cost_usd
