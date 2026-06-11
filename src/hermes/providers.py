from __future__ import annotations

import os
from typing import Iterable, Protocol

import httpx


class Provider(Protocol):
    def complete(self, model: str, messages: list[dict], system: str) -> str: ...


class AnthropicProvider:
    def __init__(self) -> None:
        from anthropic import Anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.client = Anthropic(api_key=api_key)

    def complete(self, model: str, messages: list[dict], system: str) -> str:
        model_id = model.split("/", 1)[1] if "/" in model else model
        resp = self.client.messages.create(
            model=model_id,
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def complete_with_tools(self, model: str, messages: list[dict], system: str,
                            tools: list[dict]):
        """Returns the raw Anthropic response so the agent can run a tool loop."""
        model_id = model.split("/", 1)[1] if "/" in model else model
        kwargs: dict = {"model": model_id, "max_tokens": 4096,
                        "system": system, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        return self.client.messages.create(**kwargs)


class OpenAICompatibleProvider:
    """Used for OpenRouter, Nous Portal, and similar OpenAI-compatible endpoints."""

    def __init__(self, base_url: str, api_key_env: str) -> None:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"{api_key_env} not set")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def complete(self, model: str, messages: list[dict], system: str) -> str:
        payload_messages = [{"role": "system", "content": system}, *messages]
        with httpx.Client(timeout=120.0) as client:
            r = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": model, "messages": payload_messages},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]


def make_provider(name: str) -> Provider:
    name = name.lower()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "openrouter":
        return OpenAICompatibleProvider("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY")
    if name == "nous":
        return OpenAICompatibleProvider("https://inference-api.nousresearch.com/v1", "NOUS_API_KEY")
    raise ValueError(f"Unknown provider: {name}")


def normalize_model_id(provider: str, model: str) -> str:
    """Strip provider prefix for non-Anthropic providers that expect bare IDs."""
    if provider == "anthropic":
        return model
    return model.split("/", 1)[1] if "/" in model else model
