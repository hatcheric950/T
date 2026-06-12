from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import Response
from typing import Optional
import aiosqlite

from backend.database import get_db
from backend.models import ContactCreate, ContactUpdate, ApprovalRequest, ManualSend
from backend.services import sms, auto_responder

router = APIRouter(prefix="/api/sms", tags=["sms"])

VALID_TIERS = {"business", "personal", "unknown"}
EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


# ── Inbound webhook ───────────────────────────────────────────────────────────


@router.post("/webhook")
async def twilio_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Twilio inbound-SMS webhook.

    We return empty TwiML and send any reply out-of-band via the REST API, so
    the webhook path and the approval path share one send code path.
    """
    try:
        form = await request.form()
        signature = request.headers.get("X-Twilio-Signature")
        if not sms.verify_signature(str(request.url), dict(form), signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

        await auto_responder.handle_inbound(db, From, Body)
        return Response(content=EMPTY_TWIML, media_type="application/xml")
    finally:
        await db.close()


# ── Contacts ──────────────────────────────────────────────────────────────────


@router.post("/contacts", status_code=201)
async def create_contact(contact: ContactCreate, db: aiosqlite.Connection = Depends(get_db)):
    if contact.tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"tier must be one of: {', '.join(VALID_TIERS)}")
    try:
        async with db.execute(
            """INSERT INTO contacts (name, phone, tier, venture, auto_send, protected, away_mode, away_reply)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (contact.name, contact.phone, contact.tier, contact.venture,
             int(contact.auto_send), int(contact.protected), int(contact.away_mode), contact.away_reply),
        ) as cur:
            contact_id = cur.lastrowid
        await db.commit()
        return {"id": contact_id, "status": "created"}
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=409, detail="A contact with that phone already exists")
    finally:
        await db.close()


@router.get("/contacts")
async def list_contacts(tier: Optional[str] = None, db: aiosqlite.Connection = Depends(get_db)):
    try:
        query, params = "SELECT * FROM contacts", []
        if tier:
            query += " WHERE tier = ?"
            params.append(tier)
        query += " ORDER BY name COLLATE NOCASE"
        async with db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.patch("/contacts/{contact_id}")
async def update_contact(contact_id: int, update: ContactUpdate, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Contact not found")

        if update.tier and update.tier not in VALID_TIERS:
            raise HTTPException(status_code=422, detail=f"tier must be one of: {', '.join(VALID_TIERS)}")

        fields, params = [], []
        for field, val in update.model_dump(exclude_none=True).items():
            if isinstance(val, bool):
                val = int(val)
            fields.append(f"{field} = ?")
            params.append(val)
        if not fields:
            raise HTTPException(status_code=422, detail="No fields to update")
        params.append(contact_id)

        await db.execute(f"UPDATE contacts SET {', '.join(fields)} WHERE id = ?", params)
        await db.commit()
        return {"status": "updated"}
    finally:
        await db.close()


# ── Approval queue ────────────────────────────────────────────────────────────


@router.get("/pending")
async def list_pending(db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute(
            """SELECT p.*, c.name as contact_name, c.tier as contact_tier
               FROM pending_replies p
               LEFT JOIN contacts c ON c.id = p.contact_id
               WHERE p.resolved = 0
               ORDER BY p.created_at ASC"""
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.post("/pending/{pending_id}/approve")
async def approve_pending(pending_id: int, payload: ApprovalRequest, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute(
            "SELECT * FROM pending_replies WHERE id = ? AND resolved = 0", (pending_id,)
        ) as cur:
            pending = await cur.fetchone()
        if not pending:
            raise HTTPException(status_code=404, detail="Pending reply not found or already resolved")

        text = payload.edited_text or pending["draft"]
        send_result = sms.send_sms(pending["phone"], text)

        await db.execute(
            "INSERT INTO sms_messages (contact_id, phone, direction, body, status) VALUES (?, ?, 'out', ?, 'approved')",
            (pending["contact_id"], pending["phone"], text),
        )
        await db.execute("UPDATE pending_replies SET resolved = 1 WHERE id = ?", (pending_id,))
        await db.commit()
        return {"status": "approved", "sent": send_result.get("sent", False), "detail": send_result}
    finally:
        await db.close()


@router.post("/pending/{pending_id}/reject")
async def reject_pending(pending_id: int, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute(
            "SELECT id FROM pending_replies WHERE id = ? AND resolved = 0", (pending_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Pending reply not found or already resolved")
        await db.execute("UPDATE pending_replies SET resolved = 1 WHERE id = ?", (pending_id,))
        await db.commit()
        return {"status": "rejected"}
    finally:
        await db.close()


# ── Message log + manual send ─────────────────────────────────────────────────


@router.get("/messages")
async def list_messages(phone: Optional[str] = None, limit: int = 50, db: aiosqlite.Connection = Depends(get_db)):
    try:
        query, params = "SELECT * FROM sms_messages", []
        if phone:
            query += " WHERE phone = ?"
            params.append(phone)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        async with db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.post("/send")
async def manual_send(payload: ManualSend, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute("SELECT id FROM contacts WHERE phone = ?", (payload.phone,)) as cur:
            row = await cur.fetchone()
        contact_id = row["id"] if row else None
        send_result = sms.send_sms(payload.phone, payload.body)
        await db.execute(
            "INSERT INTO sms_messages (contact_id, phone, direction, body, status) VALUES (?, ?, 'out', ?, 'manual')",
            (contact_id, payload.phone, payload.body),
        )
        await db.commit()
        return {"sent": send_result.get("sent", False), "detail": send_result}
    finally:
        await db.close()


@router.get("/status")
async def sms_status():
    """Surface whether SMS is live and whether auto-send is armed."""
    return {
        "configured": sms.is_configured(),
        "auto_send_enabled": sms.auto_send_enabled(),
    }
