from __future__ import annotations

import logging

from .classifier import Classifier
from .policy import Policy
from .responder import draft
from .settings import Settings
from .smtp import send_email_reply
from .state import State
from .twilio_sender import send_sms_reply
from .types import InboundMessage


log = logging.getLogger("hermes.watcher")


class Pipeline:
    def __init__(self, settings: Settings, state: State, policy: Policy, classifier: Classifier):
        self.settings = settings
        self.state = state
        self.policy = policy
        self.classifier = classifier

    async def handle(self, msg: InboundMessage) -> str:
        if not await self.state.mark_seen(msg.message_id):
            log.info("drop_duplicate sender=%s id=%s", msg.sender, msg.message_id)
            return "drop_duplicate"

        decision = await self.policy.evaluate(msg)
        if decision.action != "reply":
            await self.state.log_audit(
                channel=msg.channel, sender=msg.sender, message_id=msg.message_id,
                decision=decision.action,
            )
            log.info("%s sender=%s reason=%s", decision.action, msg.sender, decision.reason)
            return decision.action

        if not await self.classifier.wants_reply(msg):
            await self.state.log_audit(
                channel=msg.channel, sender=msg.sender, message_id=msg.message_id,
                decision="drop_no_reply_wanted",
            )
            log.info("drop_no_reply_wanted sender=%s", msg.sender)
            return "drop_no_reply_wanted"

        reply_text = await draft(self.settings, msg)

        if self.settings.mode == "shadow":
            await self.state.log_audit(
                channel=msg.channel, sender=msg.sender, message_id=msg.message_id,
                decision="shadow_would_send", draft=reply_text, sent=False,
            )
            log.info("SHADOW would_send sender=%s draft_len=%d", msg.sender, len(reply_text))
            return "shadow_would_send"

        try:
            cost = 0.0
            if msg.channel == "email":
                await send_email_reply(self.settings, msg, reply_text)
            else:
                cost = await send_sms_reply(self.settings, msg.sender, reply_text)
            await self.state.log_audit(
                channel=msg.channel, sender=msg.sender, message_id=msg.message_id,
                decision="sent", draft=reply_text, sent=True, cost_usd=cost,
            )
            log.info("sent sender=%s channel=%s cost=$%.4f", msg.sender, msg.channel, cost)
            return "sent"
        except Exception as e:
            await self.state.log_audit(
                channel=msg.channel, sender=msg.sender, message_id=msg.message_id,
                decision=f"send_error:{type(e).__name__}", draft=reply_text, sent=False,
            )
            log.exception("send_error sender=%s", msg.sender)
            return "send_error"
