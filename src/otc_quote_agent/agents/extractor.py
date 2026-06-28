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

    def extract_candidates(
        self,
        text: str,
        product_type: ProductType,
        schema: type[BaseQuote],
        llm_client: LLMClient,
    ) -> list[dict[str, Any]]:
        item_schema = schema.model_json_schema()
        wrapper_schema = {
            "type": "object",
            "properties": {
                "quote_candidates": {
                    "type": "array",
                    "minItems": 2,
                    "items": item_schema,
                }
            },
            "required": ["quote_candidates"],
            "additionalProperties": False,
        }
        last_error: LLMResponseError | None = None
        for attempt in range(2):
            try:
                payload = llm_client.complete_json(
                    extraction_messages(
                        text,
                        product_type,
                        wrapper_schema,
                        correction=attempt == 1,
                        multiple=True,
                    ),
                    json_schema=wrapper_schema,
                )
                candidates = payload.get("quote_candidates")
                if not isinstance(candidates, list) or len(candidates) < 2:
                    raise LLMResponseError(
                        "Multi-option response must contain at least two quote_candidates."
                    )
                if not all(isinstance(item, dict) for item in candidates):
                    raise LLMResponseError("Every quote candidate must be a JSON object.")
                return candidates
            except LLMResponseError as exc:
                last_error = exc
        raise LLMResponseError(
            f"Model returned invalid multi-option JSON after one retry: {last_error}"
        ) from last_error
