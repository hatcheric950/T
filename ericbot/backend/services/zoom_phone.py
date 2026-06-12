"""Zoom Phone API wrapper.

Handles:
- Server-to-Server OAuth token acquisition (cached, auto-refreshed)
- Webhook signature verification (HMAC-SHA256, v0: prefix)
- Endpoint URL validation challenge/response
- Voicemail transcript + metadata fetching
- Outbound SMS via Zoom (optional, falls back gracefully)
"""
import os
import hmac
import hashlib
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

def _cfg():
    return {
        "account_id": os.getenv("ZOOM_ACCOUNT_ID", ""),
        "client_id": os.getenv("ZOOM_CLIENT_ID", ""),
        "client_secret": os.getenv("ZOOM_CLIENT_SECRET", ""),
        "webhook_secret": os.getenv("ZOOM_WEBHOOK_SECRET_TOKEN", ""),
        "phone_number": os.getenv("ZOOM_PHONE_NUMBER", ""),
    }


def is_configured() -> bool:
    c = _cfg()
    return bool(c["account_id"] and c["client_id"] and c["client_secret"])


def zoom_phone_number() -> str:
    return _cfg()["phone_number"]


# ── OAuth token cache ─────────────────────────────────────────────────────────

_token_cache: dict = {"token": None, "expires_at": 0}


async def _get_access_token() -> Optional[str]:
    """Fetch (or return cached) Server-to-Server OAuth token."""
    if not is_configured():
        return None
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    c = _cfg()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://zoom.us/oauth/token",
                params={"grant_type": "account_credentials", "account_id": c["account_id"]},
                auth=(c["client_id"], c["client_secret"]),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            _token_cache["token"] = data["access_token"]
            _token_cache["expires_at"] = now + data.get("expires_in", 3600)
            return _token_cache["token"]
        except Exception as e:
            logger.error("Zoom OAuth token error: %s", e)
            return None


async def _zoom_get(path: str) -> Optional[dict]:
    """Authenticated GET to Zoom API."""
    token = await _get_access_token()
    if not token:
        return None
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"https://api.zoom.us/v2{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Zoom API GET %s error: %s", path, e)
            return None


# ── Webhook verification ──────────────────────────────────────────────────────

def verify_webhook_signature(
    timestamp: str,
    body_raw: bytes,
    signature: str,
) -> bool:
    """Verify Zoom webhook HMAC-SHA256 signature.

    Zoom format: v0=HMAC-SHA256(secret, "v0:{timestamp}:{body}")
    """
    secret = _cfg()["webhook_secret"]
    if not secret:
        logger.warning("ZOOM_WEBHOOK_SECRET_TOKEN not set — skipping signature check")
        return True  # dev mode

    message = f"v0:{timestamp}:{body_raw.decode('utf-8', errors='replace')}"
    expected = "v0=" + hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_url_validation(payload: dict) -> dict:
    """Respond to Zoom's endpoint URL validation challenge."""
    token = payload.get("payload", {}).get("plainToken", "")
    secret = _cfg()["webhook_secret"]
    if not secret:
        return {"plainToken": token, "encryptedToken": token}
    encrypted = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
    return {"plainToken": token, "encryptedToken": encrypted}


# ── Voicemail API ─────────────────────────────────────────────────────────────

async def get_voicemail(voicemail_id: str) -> Optional[dict]:
    """Fetch voicemail details including transcript from Zoom API."""
    return await _zoom_get(f"/phone/voice_mails/{voicemail_id}")


async def get_voicemail_transcript(voicemail_id: str) -> str:
    """Return transcript text or empty string if unavailable."""
    data = await get_voicemail(voicemail_id)
    if not data:
        return ""
    # Zoom includes transcript in `transcription` field (when feature enabled)
    return data.get("transcription", "") or data.get("transcript", "") or ""
