from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI, Form, HTTPException, Request, Response
from twilio.request_validator import RequestValidator

from .pipeline import Pipeline
from .settings import Settings
from .types import InboundMessage


log = logging.getLogger("hermes.watcher.twilio")


def build_app(settings: Settings, pipeline: Pipeline) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    router = APIRouter()
    validator = RequestValidator(settings.twilio_auth_token) if settings.twilio_auth_token else None

    @router.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "mode": settings.mode}

    @router.post("/sms/inbound")
    async def sms_inbound(
        request: Request,
        From: str = Form(...),
        Body: str = Form(""),
        MessageSid: str = Form(...),
    ) -> Response:
        if validator is None:
            raise HTTPException(500, "twilio not configured")
        signature = request.headers.get("X-Twilio-Signature", "")
        form = dict(await request.form())
        if not validator.validate(settings.twilio_webhook_url, form, signature):
            log.warning("twilio signature mismatch from=%s", From)
            raise HTTPException(403, "invalid signature")

        msg = InboundMessage(
            channel="sms",
            sender=From.strip(),
            body=Body.strip(),
            message_id=MessageSid.strip(),
        )
        try:
            await pipeline.handle(msg)
        except Exception:
            log.exception("pipeline failed for sms %s", MessageSid)

        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
            media_type="application/xml",
        )

    app.include_router(router)
    return app
