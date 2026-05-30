"""Twilio SMS gateway — send messages and verify inbound webhook signatures.

Degrades gracefully when credentials are absent (local/dev): sends become
no-ops that are still logged by the caller, and signature verification is
skipped unless explicitly enabled.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def _config() -> dict:
    return {
        "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
        "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
        "from_number": os.getenv("TWILIO_PHONE_NUMBER", ""),
        "validate_signature": os.getenv("TWILIO_VALIDATE_SIGNATURE", "false").lower() == "true",
    }


def is_configured() -> bool:
    c = _config()
    return bool(c["account_sid"] and c["auth_token"] and c["from_number"])


def auto_send_enabled() -> bool:
    """Global master switch for ALL automatic outbound SMS."""
    return os.getenv("SMS_AUTO_SEND_ENABLED", "false").lower() == "true"


def _get_client():
    global _client
    if _client is None:
        from twilio.rest import Client
        c = _config()
        _client = Client(c["account_sid"], c["auth_token"])
    return _client


def send_sms(to: str, body: str) -> dict:
    """Send an SMS. Returns a status dict; never raises on config gaps."""
    c = _config()
    if not is_configured():
        logger.warning("Twilio not configured — SMS to %s not sent (logged only)", to)
        return {"sent": False, "reason": "not_configured"}
    try:
        msg = _get_client().messages.create(body=body, from_=c["from_number"], to=to)
        return {"sent": True, "sid": msg.sid}
    except Exception as e:  # pragma: no cover - network/credential errors
        logger.error("Twilio send failed: %s", e)
        return {"sent": False, "reason": str(e)}


def verify_signature(url: str, params: dict, signature: Optional[str]) -> bool:
    """Verify an inbound Twilio webhook signature.

    Returns True when verification is disabled or unconfigured (dev mode),
    so local testing isn't blocked. Enforced only when
    TWILIO_VALIDATE_SIGNATURE=true and credentials exist.
    """
    c = _config()
    if not c["validate_signature"] or not c["auth_token"]:
        return True
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(c["auth_token"])
        return validator.validate(url, params, signature or "")
    except Exception as e:  # pragma: no cover
        logger.error("Signature verification error: %s", e)
        return False
