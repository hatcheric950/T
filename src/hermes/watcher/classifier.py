from __future__ import annotations

import asyncio

from anthropic import Anthropic

from .settings import Settings
from .state import State
from .types import InboundMessage


SYSTEM = (
    "You decide whether an inbound message from a human wants a personal reply. "
    "Answer with exactly one word: YES or NO. "
    "YES means a human is asking the recipient something or expecting a response. "
    "NO means it's a newsletter, receipt, notification, marketing, or automated digest."
)


class Classifier:
    def __init__(self, settings: Settings, state: State):
        self.settings = settings
        self.state = state
        self._client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    async def wants_reply(self, msg: InboundMessage) -> bool:
        cached = await self.state.get_classification(msg.message_id)
        if cached is not None:
            return cached
        verdict = await asyncio.to_thread(self._call, msg)
        await self.state.cache_classification(msg.message_id, verdict)
        return verdict

    def _call(self, msg: InboundMessage) -> bool:
        if self._client is None:
            return True  # fail-open in absence of key; policy still gates sending
        prompt = (
            f"Channel: {msg.channel}\nFrom: {msg.sender}\n"
            f"Subject: {msg.subject}\n\n{msg.body[:2000]}"
        )
        try:
            resp = self._client.messages.create(
                model=self.settings.classifier_model,
                max_tokens=4,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in resp.content if b.type == "text").strip().upper()
            return text.startswith("YES")
        except Exception:
            return True  # fail-open; policy gate still applies
