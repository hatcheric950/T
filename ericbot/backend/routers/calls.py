"""Zoom Phone webhook + call management endpoints.

Webhook flow:
  1. Zoom POSTs to /api/calls/webhook with JSON payload.
  2. We verify the HMAC-SHA256 signature.
  3. Dispatch on event_type:
       endpoint.url_validation  → challenge/response (Zoom requires this on setup)
       phone.callee_missed      → handle_missed_call()
       phone.voicemail_received → handle_voicemail()
  4. Return 200 immediately; processing is synchronous but fast.

Approval flow mirrors SMS /api/sms/pending — Eric sees the draft and taps
approve (which sends a follow-up SMS via Twilio) or rejects it.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import aiosqlite

from backend.database import get_db
from backend.models import VoicemailApproval, ManualSend
from backend.services import sms, zoom_phone, call_responder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


# ── Webhook ───────────────────────────────────────────────────────────────────


@router.post("/webhook")
async def zoom_webhook(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    """Receive Zoom Phone events.

    Zoom verifies the endpoint with a url_validation challenge before live
    traffic starts — we must respond correctly or Zoom rejects the config.
    """
    try:
        body_raw = await request.body()
        payload = await request.json()

        event_type = payload.get("event", "")

        # ── URL validation challenge (Zoom setup step) ────────────────────────
        if event_type == "endpoint.url_validation":
            return JSONResponse(zoom_phone.handle_url_validation(payload))

        # ── Signature verification ────────────────────────────────────────────
        timestamp = request.headers.get("x-zm-request-timestamp", "")
        signature = request.headers.get("x-zm-signature", "")
        if not zoom_phone.verify_webhook_signature(timestamp, body_raw, signature):
            raise HTTPException(status_code=403, detail="Invalid Zoom webhook signature")

        payload_data = payload.get("payload", {})

        if event_type in ("phone.callee_missed", "phone.caller_missed"):
            caller = payload_data.get("object", {})
            phone = caller.get("caller", {}).get("phone_number", "")
            zoom_call_id = caller.get("call_id", "")
            if phone:
                result = await call_responder.handle_missed_call(db, phone, zoom_call_id)
                logger.info("Missed call from %s — %s", phone, result.get("action"))

        elif event_type == "phone.voicemail_received":
            vm_obj = payload_data.get("object", {})
            phone = vm_obj.get("caller_number", "") or vm_obj.get("caller", {}).get("phone_number", "")
            voicemail_id = vm_obj.get("id", "") or vm_obj.get("voicemail_id", "")
            transcript = vm_obj.get("transcription", "") or vm_obj.get("transcript", "")
            zoom_call_id = vm_obj.get("call_id", "")
            if phone:
                result = await call_responder.handle_voicemail(db, phone, voicemail_id, transcript, zoom_call_id)
                logger.info("Voicemail from %s — %s", phone, result.get("action"))

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Zoom webhook error: %s", e)
        return {"status": "error", "detail": str(e)}
    finally:
        await db.close()


# ── Call logs ─────────────────────────────────────────────────────────────────


@router.get("/logs")
async def list_call_logs(
    phone: Optional[str] = None,
    call_type: Optional[str] = None,
    limit: int = 50,
    db: aiosqlite.Connection = Depends(get_db),
):
    try:
        query = """
            SELECT l.*, c.name as contact_name, c.tier as contact_tier
            FROM call_logs l
            LEFT JOIN contacts c ON c.id = l.contact_id
        """
        params = []
        where = []
        if phone:
            where.append("l.phone = ?")
            params.append(phone)
        if call_type:
            where.append("l.call_type = ?")
            params.append(call_type)
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY l.created_at DESC LIMIT ?"
        params.append(limit)

        async with db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


# ── Voicemail queue ───────────────────────────────────────────────────────────


@router.get("/voicemails")
async def list_voicemails(
    resolved: Optional[bool] = False,
    db: aiosqlite.Connection = Depends(get_db),
):
    try:
        async with db.execute(
            """SELECT v.*, c.name as contact_name, c.tier as contact_tier
               FROM voicemails v
               LEFT JOIN contacts c ON c.id = v.contact_id
               WHERE v.resolved = ?
               ORDER BY v.urgent DESC, v.created_at ASC""",
            (int(resolved),),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.post("/voicemails/{voicemail_id}/approve")
async def approve_voicemail(
    voicemail_id: int,
    payload: VoicemailApproval,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Send the follow-up SMS draft (optionally edited) via Twilio."""
    try:
        async with db.execute(
            "SELECT * FROM voicemails WHERE id = ? AND resolved = 0", (voicemail_id,)
        ) as cur:
            vm = await cur.fetchone()
        if not vm:
            raise HTTPException(status_code=404, detail="Voicemail not found or already resolved")

        text = payload.edited_text or vm["draft_reply"]
        if not text:
            raise HTTPException(status_code=422, detail="No draft reply available")

        send_result = sms.send_sms(vm["phone"], text)

        # Log the outbound SMS
        contact_id = vm["contact_id"]
        await db.execute(
            "INSERT INTO sms_messages (contact_id, phone, direction, body, status) VALUES (?, ?, 'out', ?, 'approved')",
            (contact_id, vm["phone"], text),
        )
        await db.execute("UPDATE voicemails SET resolved = 1 WHERE id = ?", (voicemail_id,))
        await db.commit()
        return {"status": "approved", "sent": send_result.get("sent", False), "detail": send_result}
    finally:
        await db.close()


@router.post("/voicemails/{voicemail_id}/reject")
async def reject_voicemail(voicemail_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Dismiss a voicemail without sending any reply."""
    try:
        async with db.execute(
            "SELECT id FROM voicemails WHERE id = ? AND resolved = 0", (voicemail_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Voicemail not found or already resolved")
        await db.execute("UPDATE voicemails SET resolved = 1 WHERE id = ?", (voicemail_id,))
        await db.commit()
        return {"status": "rejected"}
    finally:
        await db.close()


# ── Status ────────────────────────────────────────────────────────────────────


@router.get("/status")
async def calls_status():
    return {
        "configured": zoom_phone.is_configured(),
        "zoom_phone_number": zoom_phone.zoom_phone_number() or None,
    }
