"""Common JSON-oriented LLM interface."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from otc_quote_agent.llm.prompts import classification_messages
from otc_quote_agent.schemas import ProductType


class LLMError(RuntimeError):
    """Base error for visible model failures."""


class LLMProviderError(LLMError):
    """Raised when a provider request fails."""


class LLMResponseError(LLMError):
    """Raised when a provider returns invalid structured output."""


class LLMClient(ABC):
    provider_name: str
    model: str

    @abstractmethod
    def complete_json(
        self,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return one parsed JSON object or raise a visible error."""

    def classify_product(self, text: str) -> ProductType:
        payload = self.complete_json(classification_messages(text))
        raw_product = payload.get("product_type")
        try:
            return ProductType(raw_product)
        except ValueError as exc:
            raise LLMResponseError(
                f"Model returned invalid product_type: {raw_product!r}"
            ) from exc


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object, accepting a single Markdown code fence."""
    cleaned = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.S | re.I)
    if fenced:
        cleaned = fenced.group(1)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"Model did not return valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LLMResponseError("Model response must be a JSON object.")
    return payload
