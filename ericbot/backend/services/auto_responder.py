"""Inbound SMS routing — the brain of the auto-responder.

Routing rules:

  protected = True  (e.g. spouse)
    → NEVER draft a reply in Eric's voice.
      Optionally send one honest away-reply ("tied up, I'll get back to you")
      and always create a high-priority reminder so Eric responds himself.

  everyone else  (business, personal, unknown)
    → Draft a reply in Eric's voice.
      business + auto_send + SMS_AUTO_SEND_ENABLED + routine message
        → send automatically
      everything else
        → queue for one-tap approval (never silent-dropped)

The key change from the previous model: the protected flag is a narrow,
named exception for a specific person. Everyone else gets drafted in Eric's
voice and at minimum lands in the approval queue.
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
    name = (contact["name"] if contact else None) or phone
    venture = contact["venture"] if contact else None
    tier = contact["tier"] if contact else "unknown"
    is_protected = bool(contact["protected"]) if contact else False

    await _log_message(db, contact_id, phone, "in", body, "received")

    if is_protected:
        result = await _handle_protected(db, contact, phone, name, body)
    else:
        result = await _handle_draft_and_queue(db, contact, contact_id, phone, name, venture, tier, body)

    await db.commit()
    return result


async def _handle_protected(db, contact, phone, name, body):
    """Protected contact: honest away-reply (optional) + reminder. Never impersonates Eric."""
    await _add_reminder(db, name, phone, body, contact["venture"] if contact else None)

    sent_away = False
    if contact and contact["away_mode"]:
        style_ctx, _ = await load_style_context(db)
        away_text = contact["away_reply"] or await ai_engine.generate_away_reply(name, style_ctx)
        send_result = sms.send_sms(phone, away_text)
        await _log_message(db, contact["id"], phone, "out", away_text, "away_reply")
        sent_away = bool(send_result.get("sent"))

    return {
        "action": "away_reply_and_reminder" if sent_away else "reminder_only",
        "protected": True,
        "note": "Protected contact — no in-voice reply generated.",
    }


async def _handle_draft_and_queue(db, contact, contact_id, phone, name, venture, tier, body):
    """Draft a reply in Eric's voice, then either auto-send (routine business) or queue."""
    style_ctx, _ = await load_style_context(db)
    history = await _recent_thread(db, phone)
    draft = await ai_engine.draft_sms_reply(name, venture or "eric_digital", body, style_ctx, history)
    classification = await ai_engine.classify_sms(body)

    can_auto = (
        tier == "business"
        and contact is not None
        and bool(contact["auto_send"])
        and classification["routine"]
        and sms.auto_send_enabled()
    )

    if can_auto:
        send_result = sms.send_sms(phone, draft)
        if send_result.get("sent"):
            await _log_message(db, contact_id, phone, "out", draft, "auto_sent")
            return {
                "action": "auto_sent",
                "draft": draft,
                "intent": classification["intent"],
                "protected": False,
            }
        # Send failed — fall through to queue so nothing is lost silently.

    # Everything else: approval queue
    async with db.execute(
        """SELECT id FROM sms_messages WHERE phone = ? AND direction = 'in'
           ORDER BY created_at DESC LIMIT 1""",
        (phone,),
    ) as cur:
        row = await cur.fetchone()
    inbound_id = row["id"] if row else None

    await db.execute(
        "INSERT INTO pending_replies (contact_id, phone, inbound_message_id, draft, intent) VALUES (?, ?, ?, ?, ?)",
        (contact_id, phone, inbound_id, draft, classification["intent"]),
    )
    return {
        "action": "queued_for_approval",
        "draft": draft,
        "intent": classification["intent"],
        "protected": False,
    }
