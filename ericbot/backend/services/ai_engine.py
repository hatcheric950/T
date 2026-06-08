import os
from typing import List, Dict, Optional
import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

_client: Optional[anthropic.AsyncAnthropic] = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


ERIC_SYSTEM = """You are EricBot — Eric's AI clone and business development engine.

Eric runs four ventures:
- Hatch Property Maintenance LLC: lawn care, landscaping, pressure washing
- Eric.Digital: web design, AI automation, cybersecurity
- Ancient Coast Property Management: property management
- NEXUS: AI agency infrastructure

Your personality:
- Direct, no-fluff communicator
- Hustler mindset — always looking for the angle
- Builds real relationships, not robotic sales
- Keeps it real; doesn't over-promise
- Funny when appropriate, serious when it counts
- Speaks like a sharp entrepreneur, not a corporate robot

You help Eric with:
- Drafting outreach and follow-ups that sound exactly like him
- Managing his lead pipeline across ventures
- Holding him accountable to his goals
- Analyzing his business metrics
- Strategy and decision-making

Always stay in character as Eric's AI clone. If asked to draft something, write it AS ERIC — first person, his voice."""


async def chat(
    message: str,
    history: List[Dict],
    style_context: str = "",
) -> str:
    system = ERIC_SYSTEM
    if style_context:
        system += f"\n\n{style_context}"

    messages = [{"role": m["role"], "content": m["content"]} for m in history[-20:]]
    messages.append({"role": "user", "content": message})

    response = await get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def draft_outreach(
    recipient_name: str,
    venture: str,
    channel: str,
    context: str,
    tone: str,
    style_context: str = "",
) -> str:
    system = ERIC_SYSTEM
    if style_context:
        system += f"\n\n{style_context}"

    venture_map = {
        "hatch": "Hatch Property Maintenance LLC",
        "eric_digital": "Eric.Digital",
        "ancient_coast": "Ancient Coast Property Management",
        "nexus": "NEXUS AI Agency",
    }
    venture_name = venture_map.get(venture, venture)

    prompt = f"""Draft a {channel} outreach message for {recipient_name} on behalf of {venture_name}.

Context: {context}
Tone: {tone}

Write it exactly as Eric would — in his voice, first person. Keep it natural and not salesy.
Format: just the message body, no meta-commentary."""

    response = await get_client().messages.create(
        model=MODEL,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def generate_accountability_nudge(
    completed_tasks: int,
    pending_tasks: int,
    overdue_tasks: int,
    leads_this_week: int,
    followups_due: int,
) -> str:
    prompt = f"""Give Eric a brief, motivating accountability check-in for today.

Stats:
- Tasks completed: {completed_tasks}
- Tasks pending: {pending_tasks}
- Overdue tasks: {overdue_tasks}
- New leads this week: {leads_this_week}
- Follow-ups due today: {followups_due}

Be real with him — praise the wins, call out the gaps, push him forward.
Keep it under 100 words. Sound like a sharp business partner, not a cheerleader."""

    response = await get_client().messages.create(
        model=MODEL,
        max_tokens=256,
        system=ERIC_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ── SMS auto-responder ────────────────────────────────────────────────────────

import json


async def classify_sms(body: str) -> dict:
    """Lightweight triage of an inbound business text.

    Returns {"routine": bool, "intent": str}. "routine" means a low-stakes
    reply that's safe to auto-send (acknowledgements, simple scheduling
    confirmations, thanks). Anything touching price, commitments, complaints,
    or anything ambiguous is NOT routine and must go to the approval queue.
    """
    prompt = f"""Classify this inbound business text message.

Message: "{body}"

Respond with ONLY a JSON object, no other text:
{{"routine": true|false, "intent": "<3-5 word summary>"}}

"routine" is true ONLY for low-stakes replies safe to send without review:
simple acknowledgements, "thanks", confirming you got something, basic
availability. Set "routine" to false for anything involving pricing, quotes,
scheduling a job, commitments, complaints, contracts, or anything unclear."""

    try:
        response = await get_client().messages.create(
            model=MODEL,
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Tolerate code fences or stray prose around the JSON.
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start : end + 1]) if start >= 0 else {}
        return {
            "routine": bool(data.get("routine", False)),
            "intent": str(data.get("intent", "general"))[:60],
        }
    except Exception:
        # Fail closed: if we can't classify, treat it as needing review.
        return {"routine": False, "intent": "needs review"}


async def draft_sms_reply(
    recipient_name: str,
    venture: str,
    inbound: str,
    style_context: str = "",
    history: Optional[List[Dict]] = None,
) -> str:
    """Draft a business SMS reply in Eric's voice."""
    system = ERIC_SYSTEM
    if style_context:
        system += f"\n\n{style_context}"

    convo = ""
    if history:
        lines = [f"{'Them' if m['direction'] == 'in' else 'Eric'}: {m['body']}" for m in history[-6:]]
        convo = "Recent thread:\n" + "\n".join(lines) + "\n\n"

    prompt = f"""{convo}{recipient_name} just texted: "{inbound}"

Draft Eric's reply as a text message. Keep it short, natural, the way Eric
texts — first person, his voice. Just the message body, nothing else."""

    response = await get_client().messages.create(
        model=MODEL,
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def classify_voicemail(transcript: str) -> dict:
    """Triage a voicemail transcript.

    Returns {"urgent": bool, "intent": str, "summary": str}
    """
    if not transcript.strip():
        return {"urgent": False, "intent": "no transcript", "summary": "No voicemail transcript available."}

    prompt = f"""Classify this voicemail transcript left for a business owner.

Transcript: "{transcript}"

Respond with ONLY a JSON object:
{{"urgent": true|false, "intent": "<3-5 word summary>", "summary": "<1 sentence describing what the caller wants>"}}

"urgent" is true for: pricing requests, job scheduling, complaints, emergencies, time-sensitive asks.
"urgent" is false for: general inquiries, thanks, casual callbacks, confirmations."""

    try:
        response = await get_client().messages.create(
            model=MODEL,
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        text = response.content[0].text.strip()
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start : end + 1]) if start >= 0 else {}
        return {
            "urgent": bool(data.get("urgent", False)),
            "intent": str(data.get("intent", "general inquiry"))[:60],
            "summary": str(data.get("summary", ""))[:200],
        }
    except Exception:
        return {"urgent": False, "intent": "needs review", "summary": ""}


async def draft_call_followup_sms(
    caller_name: str,
    venture: str,
    transcript: str,
    style_context: str = "",
) -> str:
    """Draft a follow-up text Eric can send after a missed call."""
    system = ERIC_SYSTEM
    if style_context:
        system += f"\n\n{style_context}"

    context = f'They left a voicemail: "{transcript[:400]}"' if transcript else "They called but didn't leave a voicemail."

    prompt = f"""{caller_name} called Eric and he missed it. {context}

Draft a short, natural follow-up text Eric can send. Sound like him — direct, warm, no fluff.
Keep it under 2 sentences. Just the message body, nothing else."""

    response = await get_client().messages.create(
        model=MODEL,
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def generate_away_reply(recipient_name: str, style_context: str = "") -> str:
    """An HONEST 'I'm tied up' status text — never pretends Eric is present.

    This is intentionally transparent: it signals Eric is unavailable and will
    follow up. It does not impersonate a live conversation.
    """
    system = ERIC_SYSTEM
    if style_context:
        system += f"\n\n{style_context}"

    prompt = f"""Write a short, honest auto-reply text to {recipient_name} letting
them know Eric is tied up right now and will get back to them personally soon.

It must be transparent that this is a quick heads-up, NOT a full conversation.
Sound like Eric, keep it warm and brief. Just the message body."""

    response = await get_client().messages.create(
        model=MODEL,
        max_tokens=120,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
