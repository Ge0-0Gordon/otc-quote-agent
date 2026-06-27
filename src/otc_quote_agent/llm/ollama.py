"""Ollama local chat client."""

from __future__ import annotations

from typing import Any

import httpx

from otc_quote_agent.llm.base import (
    LLMClient,
    LLMProviderError,
    LLMResponseError,
    parse_json_object,
)


class OllamaClient(LLMClient):
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 60,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def complete_json(
        self,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": json_schema or "json",
            "options": {"temperature": 0},
        }
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc

        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMResponseError(
                "Ollama response did not contain message content."
            ) from exc
        if not isinstance(content, str):
            raise LLMResponseError("Ollama message content must be text.")
        return parse_json_object(content)
