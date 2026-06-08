"""Inbound Zoom Phone call/voicemail routing.

Routing rules mirror auto_responder.py:

  protected = True  (e.g. spouse)
    → Log the call, create high-priority reminder.
    → NEVER draft a follow-up in Eric's voice.

  everyone else  (business, personal, unknown)
    → Log the missed call or voicemail.
    → Draft a follow-up SMS in Eric's voice.
    → Queue for one-tap approval (never auto-sent for calls).
"""
import logging
import aiosqlite

from backend.services import ai_engine, zoom_phone
from backend.services.style_context import load_style_context

logger = logging.getLogger(__name__)


async def _log_call(db, contact_id, phone, direction, call_type, status, zoom_call_id=None):
    async with db.execute(
        """INSERT INTO call_logs (contact_id, phone, direction, call_type, status, zoom_call_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (contact_id, phone, direction, call_type, status, zoom_call_id),
    ) as cur:
        return cur.lastrowid


async def _add_reminder(db, contact_name, phone, description, venture=None):
    title = f"Return call: {contact_name or phone}"
    await db.execute(
        "INSERT INTO tasks (title, description, venture, priority) VALUES (?, ?, ?, ?)",
        (title, description[:500], venture, "high"),
    )


async def handle_missed_call(
    db: aiosqlite.Connection,
    phone: str,
    zoom_call_id: str = None,
) -> dict:
    """Process a missed inbound call event from Zoom."""
    async with db.execute("SELECT * FROM contacts WHERE phone = ?", (phone,)) as cur:
        contact = await cur.fetchone()

    contact_id = contact["id"] if contact else None
    name = (contact["name"] if contact else None) or phone
    venture = contact["venture"] if contact else None
    is_protected = bool(contact["protected"]) if contact else False

    call_log_id = await _log_call(db, contact_id, phone, "in", "missed", "missed", zoom_call_id)

    if is_protected:
        await _add_reminder(db, name, phone, f"Missed call from {name}. Call them back yourself.", venture)
        await db.commit()
        return {
            "action": "reminder_only",
            "protected": True,
            "note": "Protected contact — no follow-up drafted.",
        }

    style_ctx, _ = await load_style_context(db)
    draft = await ai_engine.draft_call_followup_sms(name, venture or "eric_digital", "", style_ctx)

    await db.execute(
        """INSERT INTO voicemails (contact_id, phone, call_log_id, transcript, intent, draft_reply, urgent)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (contact_id, phone, call_log_id, "", "missed call — no voicemail", draft, 0),
    )
    await db.commit()
    return {
        "action": "queued_followup",
        "draft": draft,
        "protected": False,
    }


async def handle_voicemail(
    db: aiosqlite.Connection,
    phone: str,
    voicemail_id: str,
    transcript: str = "",
    zoom_call_id: str = None,
) -> dict:
    """Process a received voicemail event from Zoom."""
    async with db.execute("SELECT * FROM contacts WHERE phone = ?", (phone,)) as cur:
        contact = await cur.fetchone()

    contact_id = contact["id"] if contact else None
    name = (contact["name"] if contact else None) or phone
    venture = contact["venture"] if contact else None
    is_protected = bool(contact["protected"]) if contact else False

    call_log_id = await _log_call(db, contact_id, phone, "in", "voicemail", "voicemail", zoom_call_id)

    # Pull transcript from Zoom API if not provided in webhook payload
    if not transcript and voicemail_id:
        transcript = await zoom_phone.get_voicemail_transcript(voicemail_id)

    if is_protected:
        desc = f"Voicemail from {name}."
        if transcript:
            desc += f' They said: "{transcript[:300]}"'
        await _add_reminder(db, name, phone, desc, venture)
        await db.commit()
        return {
            "action": "reminder_only",
            "protected": True,
            "note": "Protected contact — no follow-up drafted.",
        }

    classification = await ai_engine.classify_voicemail(transcript)
    style_ctx, _ = await load_style_context(db)
    draft = await ai_engine.draft_call_followup_sms(name, venture or "eric_digital", transcript, style_ctx)

    await db.execute(
        """INSERT INTO voicemails (contact_id, phone, call_log_id, zoom_voicemail_id, transcript,
           intent, summary, draft_reply, urgent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            contact_id, phone, call_log_id, voicemail_id, transcript,
            classification["intent"], classification["summary"], draft,
            int(classification["urgent"]),
        ),
    )
    await db.commit()
    return {
        "action": "queued_followup",
        "draft": draft,
        "intent": classification["intent"],
        "urgent": classification["urgent"],
        "protected": False,
    }
