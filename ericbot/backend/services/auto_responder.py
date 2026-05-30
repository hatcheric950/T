"""Inbound SMS routing — the brain of the auto-responder.

Routing rules by contact tier:

  business : Draft a reply in Eric's voice. If the message is ROUTINE and both
             the global master switch and the contact's auto_send are on, send
             it automatically. Otherwise queue it for one-tap approval.

  personal : NEVER impersonate Eric. Optionally send a single HONEST away-reply
             ("tied up, I'll get back to you"), and always create a task
             reminding Eric to reply himself.

  unknown  : Log it and remind Eric. No automatic reply.

This separation is deliberate: the only fully-automatic, in-voice replies that
ever go out are routine BUSINESS messages the user has explicitly opted into.
Personal relationships are never ghostwritten.
"""
import logging
import aiosqlite

from backend.services import ai_engine, sms
from backend.services.style_context import load_style_context

logger = logging.getLogger(__name__)


async def _log_message(db, contact_id, phone, direction, body, status):
    async with db.execute(
        "INSERT INTO sms_messages (contact_id, phone, direction, body, status) VALUES (?, ?, ?, ?, ?)",
        (contact_id, phone, direction, body, status),
    ) as cur:
        return cur.lastrowid


async def _recent_thread(db, phone, limit=6):
    async with db.execute(
        "SELECT direction, body FROM sms_messages WHERE phone = ? ORDER BY created_at DESC LIMIT ?",
        (phone, limit),
    ) as cur:
        rows = await cur.fetchall()
    return list(reversed([{"direction": r["direction"], "body": r["body"]} for r in rows]))


async def _add_reminder(db, contact_name, phone, body, venture=None):
    title = f"Reply to {contact_name or phone}"
    desc = f'They texted: "{body[:160]}"'
    await db.execute(
        "INSERT INTO tasks (title, description, venture, priority) VALUES (?, ?, ?, ?)",
        (title, desc, venture, "high"),
    )


async def handle_inbound(db: aiosqlite.Connection, phone: str, body: str) -> dict:
    """Process one inbound SMS. Returns a summary of what was done."""
    async with db.execute("SELECT * FROM contacts WHERE phone = ?", (phone,)) as cur:
        contact = await cur.fetchone()

    contact_id = contact["id"] if contact else None
    tier = contact["tier"] if contact else "unknown"
    name = (contact["name"] if contact else None) or phone
    venture = contact["venture"] if contact else None

    inbound_id = await _log_message(db, contact_id, phone, "in", body, "received")

    if tier == "business":
        result = await _handle_business(db, contact, inbound_id, phone, name, venture, body)
    elif tier == "personal":
        result = await _handle_personal(db, contact, phone, name, body)
    else:
        result = await _handle_unknown(db, phone, name, body)

    await db.commit()
    return result


async def _handle_business(db, contact, inbound_id, phone, name, venture, body):
    style_ctx, _ = await load_style_context(db)
    history = await _recent_thread(db, phone)
    draft = await ai_engine.draft_sms_reply(name, venture or "eric_digital", body, style_ctx, history)
    classification = await ai_engine.classify_sms(body)

    can_auto = (
        classification["routine"]
        and bool(contact["auto_send"])
        and sms.auto_send_enabled()
    )

    if can_auto:
        send_result = sms.send_sms(phone, draft)
        status = "auto_sent" if send_result.get("sent") else "pending"
        await _log_message(db, contact["id"], phone, "out", draft, status)
        if send_result.get("sent"):
            return {"tier": "business", "action": "auto_sent", "draft": draft, "intent": classification["intent"]}
        # Send failed — fall through to the approval queue so nothing is lost.

    await db.execute(
        "INSERT INTO pending_replies (contact_id, phone, inbound_message_id, draft, intent) VALUES (?, ?, ?, ?, ?)",
        (contact["id"], phone, inbound_id, draft, classification["intent"]),
    )
    return {"tier": "business", "action": "queued_for_approval", "draft": draft, "intent": classification["intent"]}


async def _handle_personal(db, contact, phone, name, body):
    # Always remind Eric to reply personally.
    await _add_reminder(db, name, phone, body)

    sent_away = False
    if contact["away_mode"]:
        style_ctx, _ = await load_style_context(db)
        # Use the contact's custom away message if set, else generate an honest one.
        away_text = contact["away_reply"] or await ai_engine.generate_away_reply(name, style_ctx)
        send_result = sms.send_sms(phone, away_text)
        await _log_message(db, contact["id"], phone, "out", away_text, "away_reply")
        sent_away = bool(send_result.get("sent"))

    return {
        "tier": "personal",
        "action": "away_reply_and_reminder" if sent_away else "reminder_only",
        "note": "Personal contacts are never auto-answered in Eric's voice.",
    }


async def _handle_unknown(db, phone, name, body):
    await _add_reminder(db, name, phone, body)
    return {
        "tier": "unknown",
        "action": "reminder_only",
        "note": "Unknown sender — logged and flagged for Eric. No auto-reply.",
    }
