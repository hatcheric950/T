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
