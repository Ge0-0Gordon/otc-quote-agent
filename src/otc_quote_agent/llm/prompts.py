"""Prompt construction for classification and quote extraction."""

from __future__ import annotations

import json
from typing import Any

from otc_quote_agent.schemas import ProductType


SYSTEM_PROMPT = """You extract OTC derivatives quote terms.
Return one JSON object only. Never infer or invent a value.
Use null when the source does not state a field.
Preserve the shortest supporting quote in evidence.
Distinguish a client's target from a firm quoted term and add a warning when needed.
If the text states a client's target coupon, such as “希望年化票息不低于15%”
or “target coupon at least 15%”, still extract the numeric value into coupon_rate.
The validator will add a warning that it is a client target, not a firm quote.
Percentages and amounts may remain as written; deterministic code normalizes them later.
"""


def classification_messages(text: str) -> list[dict[str, str]]:
    values = ", ".join(product.value for product in ProductType)
    return [
        {
            "role": "system",
            "content": (
                "Classify the OTC product. Return JSON only with key product_type. "
                f"Allowed values: {values}. DCN, Phoenix and classic structures "
                "are unsupported."
            ),
        },
        {"role": "user", "content": text},
    ]


def extraction_messages(
    text: str,
    product_type: ProductType,
    json_schema: dict[str, Any],
    correction: bool = False,
) -> list[dict[str, str]]:
    schema_text = json.dumps(json_schema, ensure_ascii=False)
    correction_text = (
        "\nA previous response was invalid. Return a valid object matching the schema."
        if correction
        else ""
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Product type: {product_type.value}\n"
                f"Required JSON Schema:\n{schema_text}\n"
                f"Source document:\n{text}"
                f"{correction_text}"
            ),
        },
    ]
