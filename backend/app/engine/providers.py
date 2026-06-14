"""LLM provider adapters.

Each adapter exposes the same minimal surface::

    client.chat(system: str, user: str, *, want_json: bool = False) -> str

so the agent layer is provider-agnostic. The ``mock`` provider does not use a
client at all (see ``agents.MockAgent``). The real adapters are intentionally
thin wrappers over each vendor's HTTP API using ``httpx`` and require no extra
SDK dependency.

Note: the real adapters are exercised against live services in deployment, not
in CI. CI runs the fully deterministic ``mock`` path.
"""
from __future__ import annotations

from typing import Protocol

import httpx


class ProviderClient(Protocol):
    def chat(self, system: str, user: str, *, want_json: bool = False) -> str:  # noqa: D401
        ...


class AnthropicClient:
    BASE = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model or "claude-haiku-4-5-20251001"

    def chat(self, system: str, user: str, *, want_json: bool = False) -> str:
        if want_json:
            user = user + "\n\nReturn ONLY valid JSON, no markdown, no prose."
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        with httpx.Client(timeout=60) as c:
            r = c.post(self.BASE, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )


class OpenAIClient:
    BASE = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"

    def chat(self, system: str, user: str, *, want_json: bool = False) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if want_json:
            body["response_format"] = {"type": "json_object"}
        with httpx.Client(timeout=60) as c:
            r = c.post(self.BASE, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]


class OllamaClient:
    """Talks to a local/remote Ollama server (the original project's runtime)."""

    def __init__(self, model: str | None = None,
                 base_url: str = "http://localhost:11434") -> None:
        self.model = model or "llama3.2"
        self.base_url = base_url.rstrip("/")

    def chat(self, system: str, user: str, *, want_json: bool = False) -> str:
        body: dict = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if want_json:
            body["format"] = "json"
        with httpx.Client(timeout=120) as c:
            r = c.post(f"{self.base_url}/api/chat", json=body)
            r.raise_for_status()
            data = r.json()
        return data["message"]["content"]


def build_client(provider: str, api_key: str | None, model: str | None) -> ProviderClient:
    if provider == "anthropic":
        if not api_key:
            raise ValueError("Anthropic provider requires an api_key")
        return AnthropicClient(api_key, model)
    if provider == "openai":
        if not api_key:
            raise ValueError("OpenAI provider requires an api_key")
        return OpenAIClient(api_key, model)
    if provider == "ollama":
        return OllamaClient(model)
    raise ValueError(f"No HTTP client for provider {provider!r}")
