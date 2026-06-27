"""OpenAI-compatible chat completions client."""

from __future__ import annotations

from typing import Any

import httpx

from otc_quote_agent.llm.base import (
    LLMClient,
    LLMProviderError,
    LLMResponseError,
    parse_json_object,
)


class OpenAICompatibleClient(LLMClient):
    provider_name = "openai"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def complete_json(
        self,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenAI-compatible request failed: {exc}") from exc

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError(
                "OpenAI-compatible response did not contain message content."
            ) from exc
        if not isinstance(content, str):
            raise LLMResponseError("Model message content must be text.")
        return parse_json_object(content)
