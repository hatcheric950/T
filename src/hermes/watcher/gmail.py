from __future__ import annotations

import asyncio
import email
import logging
import re
from email.header import decode_header, make_header
from email.utils import getaddresses, parseaddr

from aioimaplib import aioimaplib

from .pipeline import Pipeline
from .settings import Settings
from .types import InboundMessage


log = logging.getLogger("hermes.watcher.gmail")
IDLE_TIMEOUT = 29 * 60  # Gmail kicks IDLE around 30m


def _decode(s: str | None) -> str:
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def _body_from(em: email.message.Message) -> str:
    if em.is_multipart():
        for part in em.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in (part.get("Content-Disposition") or ""):
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
    payload = em.get_payload(decode=True) or b""
    charset = em.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _parse(raw: bytes) -> InboundMessage | None:
    em = email.message_from_bytes(raw)
    msg_id = (em.get("Message-ID") or "").strip()
    if not msg_id:
        return None
    from_addr = parseaddr(em.get("From", ""))[1].lower()
    if not from_addr:
        return None
    return InboundMessage(
        channel="email",
        sender=from_addr,
        body=_body_from(em).strip(),
        message_id=msg_id,
        subject=_decode(em.get("Subject")),
        in_reply_to=(em.get("In-Reply-To") or "").strip(),
        references=(em.get("References") or "").strip(),
    )


class GmailListener:
    def __init__(self, settings: Settings, pipeline: Pipeline):
        self.settings = settings
        self.pipeline = pipeline

    async def run(self) -> None:
        backoff = 5
        while True:
            try:
                await self._cycle()
                backoff = 5
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("imap cycle failed; reconnecting in %ss", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)

    async def _cycle(self) -> None:
        client = aioimaplib.IMAP4_SSL(host=self.settings.imap_host, port=self.settings.imap_port)
        await client.wait_hello_from_server()
        await client.login(self.settings.gmail_address, self.settings.gmail_app_password)
        await client.select("INBOX")
        log.info("imap connected as %s", self.settings.gmail_address)

        await self._drain_unseen(client)

        while True:
            idle = await client.idle_start(timeout=IDLE_TIMEOUT)
            await client.wait_server_push()
            client.idle_done()
            await asyncio.wait_for(idle, timeout=30)
            await self._drain_unseen(client)

    async def _drain_unseen(self, client: aioimaplib.IMAP4_SSL) -> None:
        status, data = await client.search("UNSEEN")
        if status != "OK" or not data:
            return
        ids = (data[0] or b"").split()
        for uid in ids:
            try:
                _, fetched = await client.fetch(uid.decode(), "(RFC822)")
                raw = next((b for b in fetched if isinstance(b, (bytes, bytearray)) and len(b) > 100), None)
                if not raw:
                    continue
                inbound = _parse(bytes(raw))
                if inbound is None:
                    continue
                asyncio.create_task(self.pipeline.handle(inbound))
            except Exception:
                log.exception("failed processing uid=%s", uid)
