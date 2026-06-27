"""Service output models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from otc_quote_agent.schemas.common import ProductType
from otc_quote_agent.schemas.products import QuoteModel


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    UNSUPPORTED = "unsupported"


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExtractionStatus
    product_type: ProductType
    classification_reason: str
    source_summary: str | None = None
    quote: QuoteModel | None = None
    review_questions: list[str] = Field(default_factory=list)
    processing_metadata: dict[str, Any] = Field(default_factory=dict)
