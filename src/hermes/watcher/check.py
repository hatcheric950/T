"""Pre-flight config validator: `hermes watch --check`."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .settings import Settings


def _ok(label: str, detail: str = "") -> None:
    print(f"  ✓ {label}" + (f": {detail}" if detail else ""))


def _warn(label: str, detail: str = "") -> None:
    print(f"  ! {label}" + (f": {detail}" if detail else ""))


def _err(label: str, detail: str = "") -> None:
    print(f"  ✗ {label}" + (f": {detail}" if detail else ""))


def check(settings: Settings) -> int:
    errors = 0

    print(f"\nhermes watcher config check (mode={settings.mode}, host={settings.hostname})")

    print("\nSecrets:")
    if settings.anthropic_api_key:
        _ok("ANTHROPIC_API_KEY", f"...{settings.anthropic_api_key[-6:]}")
    else:
        _err("ANTHROPIC_API_KEY", "missing"); errors += 1

    print("\nGmail:")
    if settings.gmail_address and "@" in settings.gmail_address:
        _ok("GMAIL_ADDRESS", settings.gmail_address)
    else:
        _err("GMAIL_ADDRESS", "missing or malformed"); errors += 1
    if settings.gmail_app_password and len(settings.gmail_app_password.replace(" ", "")) >= 16:
        _ok("GMAIL_APP_PASSWORD", "looks like a 16-char app password")
    else:
        _warn("GMAIL_APP_PASSWORD",
              "missing or not 16 chars — IMAP/SMTP login will fail (use a Google App Password, not your regular pw)")

    print("\nTwilio:")
    if settings.twilio_account_sid.startswith("AC"):
        _ok("TWILIO_ACCOUNT_SID", settings.twilio_account_sid[:10] + "...")
    else:
        _err("TWILIO_ACCOUNT_SID", "missing or doesn't start with 'AC'"); errors += 1
    if settings.twilio_auth_token:
        _ok("TWILIO_AUTH_TOKEN", "set")
    else:
        _err("TWILIO_AUTH_TOKEN", "missing"); errors += 1
    if settings.twilio_from_number.startswith("+"):
        _ok("TWILIO_FROM_NUMBER", settings.twilio_from_number)
    else:
        _err("TWILIO_FROM_NUMBER", "missing or not E.164 (must start with +)"); errors += 1
    if settings.twilio_webhook_url.startswith("https://"):
        _ok("TWILIO_WEBHOOK_URL", settings.twilio_webhook_url)
    else:
        _err("TWILIO_WEBHOOK_URL", "missing or not https://"); errors += 1

    print("\nPaths:")
    if settings.allowlist_path.exists():
        try:
            data = yaml.safe_load(settings.allowlist_path.read_text()) or {}
            emails = data.get("emails") or []
            phones = data.get("phones") or []
            if not emails and not phones:
                _warn("allowlist.yaml", "exists but is empty — nothing will ever be replied to")
            else:
                _ok("allowlist.yaml", f"{len(emails)} email(s), {len(phones)} phone(s)")
        except Exception as e:
            _err("allowlist.yaml", f"parse error: {e}"); errors += 1
    else:
        _err("allowlist.yaml", f"not found at {settings.allowlist_path}"); errors += 1

    if settings.state_db.parent.exists():
        _ok("state_db dir", str(settings.state_db.parent))
    else:
        _err("state_db dir", f"missing parent dir: {settings.state_db.parent}"); errors += 1

    if settings.pause_file.exists():
        _warn("PAUSE file", f"present at {settings.pause_file} — all sends are blocked until removed")
    else:
        _ok("PAUSE file", "not present (sending allowed by mode)")

    print()
    if errors:
        print(f"FAIL: {errors} error(s). Fix them in /etc/hermes/env or allowlist.yaml.\n")
        return 1
    print("OK: config looks valid. Start with: systemctl start hermes-watcher\n")
    return 0


def main() -> int:
    return check(Settings())


if __name__ == "__main__":
    sys.exit(main())
