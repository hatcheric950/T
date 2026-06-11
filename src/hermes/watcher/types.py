from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal


Channel = Literal["email", "sms"]


@dataclass(frozen=True)
class InboundMessage:
    channel: Channel
    sender: str           # email address or E.164 phone
    body: str
    message_id: str       # globally unique: RFC822 Message-ID or Twilio MessageSid
    subject: str = ""
    in_reply_to: str = ""
    references: str = ""

    def session_id(self) -> str:
        h = hashlib.sha1(f"{self.channel}:{self.sender.lower()}".encode()).hexdigest()[:12]
        return f"{self.channel[:2]}{h}"
