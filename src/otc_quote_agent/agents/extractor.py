"""Schema-guided LLM extraction."""

from __future__ import annotations

from typing import Any

from otc_quote_agent.llm import LLMClient, LLMResponseError
from otc_quote_agent.llm.prompts import extraction_messages
from otc_quote_agent.schemas import BaseQuote, ProductType


class LLMExtractor:
    def extract(
        self,
        text: str,
        product_type: ProductType,
        schema: type[BaseQuote],
        llm_client: LLMClient,
    ) -> dict[str, Any]:
        json_schema = schema.model_json_schema()
        last_error: LLMResponseError | None = None
        for attempt in range(2):
            try:
                payload = llm_client.complete_json(
                    extraction_messages(
                        text,
                        product_type,
                        json_schema,
                        correction=attempt == 1,
                    ),
                    json_schema=json_schema,
                )
                payload["product_type"] = product_type.value
                return payload
            except LLMResponseError as exc:
                last_error = exc
        raise LLMResponseError(
            f"Model returned invalid JSON after one retry: {last_error}"
        ) from last_error
