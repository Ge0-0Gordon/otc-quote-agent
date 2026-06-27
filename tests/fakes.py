from __future__ import annotations

from typing import Any

from otc_quote_agent.llm import LLMClient
from otc_quote_agent.schemas import ProductType


class FakeLLM(LLMClient):
    provider_name = "fake"
    model = "pytest-fixture"

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.call_count = 0

    def complete_json(
        self,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.call_count += 1
        if not self.responses:
            raise AssertionError("FakeLLM received an unexpected call.")
        return self.responses.pop(0)

    def classify_product(self, text: str) -> ProductType:
        self.call_count += 1
        if not self.responses:
            raise AssertionError("FakeLLM received an unexpected classification call.")
        return ProductType(self.responses.pop(0)["product_type"])
