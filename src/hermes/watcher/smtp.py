from __future__ import annotations

from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import aiosmtplib

from .settings import Settings
from .types import InboundMessage


async def send_email_reply(settings: Settings, msg: InboundMessage, body: str) -> None:
    em = EmailMessage()
    em["From"] = settings.gmail_address
    em["To"] = msg.sender
    subject = msg.subject or ""
    em["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}".strip()
    em["Date"] = formatdate(localtime=True)
    em["Message-ID"] = make_msgid(domain=settings.hostname or "localhost")
    if msg.message_id:
        em["In-Reply-To"] = msg.message_id
        em["References"] = (msg.references + " " + msg.message_id).strip()
    em.set_content(body)

    await aiosmtplib.send(
        em,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        start_tls=True,
        username=settings.gmail_address,
        password=settings.gmail_app_password,
    )
