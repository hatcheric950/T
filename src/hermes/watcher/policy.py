from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .settings import Settings
from .state import State
from .types import InboundMessage


DENY_EMAIL_PATTERNS = (
    "noreply@*", "no-reply@*", "donotreply@*", "do-not-reply@*",
    "mailer-daemon@*", "postmaster@*", "bounce@*", "bounces@*",
    "notification@*", "notifications@*",
)
DENY_PHONE_SHORTCODES = re.compile(r"^\+?\d{3,6}$")  # short codes like 22000


@dataclass
class Decision:
    action: str        # 'reply' | 'drop_*'
    reason: str = ""


class Policy:
    def __init__(self, settings: Settings, state: State):
        self.settings = settings
        self.state = state
        self._allowlist_mtime: float = 0.0
        self._emails: set[str] = set()
        self._email_globs: list[str] = []
        self._phones: set[str] = set()

    def _load_allowlist(self) -> None:
        path = self.settings.allowlist_path
        if not path.exists():
            self._emails, self._email_globs, self._phones = set(), [], set()
            self._allowlist_mtime = 0.0
            return
        mtime = path.stat().st_mtime
        if mtime == self._allowlist_mtime:
            return
        data = yaml.safe_load(path.read_text()) or {}
        emails = [str(e).lower().strip() for e in (data.get("emails") or [])]
        self._emails = {e for e in emails if "*" not in e}
        self._email_globs = [e for e in emails if "*" in e]
        self._phones = {str(p).strip() for p in (data.get("phones") or [])}
        self._allowlist_mtime = mtime

    def _allowlisted(self, msg: InboundMessage) -> bool:
        self._load_allowlist()
        sender = msg.sender.lower().strip()
        if msg.channel == "email":
            if sender in self._emails:
                return True
            return any(fnmatch.fnmatchcase(sender, g) for g in self._email_globs)
        return sender in self._phones

    def _denied(self, msg: InboundMessage) -> bool:
        sender = msg.sender.lower().strip()
        if msg.channel == "email":
            return any(fnmatch.fnmatchcase(sender, p) for p in DENY_EMAIL_PATTERNS)
        return bool(DENY_PHONE_SHORTCODES.match(sender))

    async def evaluate(self, msg: InboundMessage) -> Decision:
        if self.settings.pause_file.exists():
            return Decision("drop_paused", "kill switch file present")
        if self.settings.mode == "off":
            return Decision("drop_off", "HERMES_MODE=off")
        if self._denied(msg):
            return Decision("drop_denylisted", "matches denylist pattern")
        if not self._allowlisted(msg):
            return Decision("drop_not_allowlisted", "sender not in allowlist")

        hourly = await self.state.hourly_sent_count()
        if hourly >= self.settings.rate_hourly:
            return Decision("drop_rate_hourly", f"hourly cap {self.settings.rate_hourly}")
        per_sender = await self.state.daily_sender_count(msg.sender)
        if per_sender >= self.settings.rate_per_sender_daily:
            return Decision(
                "drop_rate_sender",
                f"daily per-sender cap {self.settings.rate_per_sender_daily}",
            )
        if msg.channel == "sms":
            cost = await self.state.daily_sms_cost()
            if cost >= self.settings.daily_sms_budget_usd:
                return Decision("drop_sms_budget", f"daily SMS budget exhausted (${cost:.2f})")

        return Decision("reply")
