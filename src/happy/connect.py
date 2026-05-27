"""happy connect — establish and verify a provider connection."""

from __future__ import annotations

import os
import sys

from . import config


def _connect_claude() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        sys.exit(
            "error: ANTHROPIC_API_KEY is not set.\n"
            "Export your key or add it to ~/.happy/.env:\n"
            "  ANTHROPIC_API_KEY=sk-ant-..."
        )

    print("Connecting to Claude (Anthropic)…", flush=True)

    try:
        import anthropic
    except ModuleNotFoundError:
        sys.exit(
            "error: 'anthropic' package not found.\n"
            "Install it with:  pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )
        reply = msg.content[0].text.strip()
    except anthropic.AuthenticationError:
        sys.exit("error: API key rejected — check ANTHROPIC_API_KEY.")
    except anthropic.APIConnectionError as exc:
        sys.exit(f"error: could not reach Anthropic API — {exc}")

    cfg = config.load()
    cfg.setdefault("providers", {})["claude"] = {
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-haiku-4-5-20251001",
        "verified": True,
    }
    config.save(cfg)

    print(f"✓ Connected. Claude replied: {reply!r}")
    print(f"  Config saved to {config.CONFIG_FILE}")


PROVIDERS: dict[str, object] = {
    "claude": _connect_claude,
}


def run(provider_name: str) -> None:
    key = provider_name.lower()
    handler = PROVIDERS.get(key)
    if handler is None:
        known = ", ".join(sorted(PROVIDERS))
        sys.exit(f"error: unknown provider {provider_name!r}. Known: {known}")
    handler()  # type: ignore[operator]
