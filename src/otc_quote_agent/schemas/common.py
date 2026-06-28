"""Shared Pydantic models for quote extraction."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ProductType(str, Enum):
    SNOWBALL = "snowball"
    FCN = "fcn"
    EUROPEAN_OPTION = "european_option"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


class SourceType(str, Enum):
    PASTED_TEXT = "pasted_text"
    TXT = "txt"
    MD = "md"
    DOCX = "docx"
    XLSX = "xlsx"
    PDF = "pdf"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class Underlying(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    ticker: str | None = None
    asset_class: str | None = None
    exchange: str | None = None
    currency: str | None = None


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    source_text: str
    location: str | None = None


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    severity: IssueSeverity
    code: str
    message: str


class BaseQuote(BaseModel):
    """Common quote fields.

    Extracted business values remain nullable. Business completeness is handled
    by RuleValidator and recorded in missing_fields/validation issues.
    """

    model_config = ConfigDict(extra="forbid")

    quote_id: str = Field(default_factory=lambda: str(uuid4()))
    source_file: str | None = None
    source_type: SourceType = SourceType.PASTED_TEXT
    counterparty: str | None = None
    quote_date: date | None = None
    trade_date: date | None = None
    product_type: ProductType
    structure_name: str | None = None
    currency: str | None = None
    notional: float | None = None
    margin_ratio: float | None = None
    max_loss: float | None = None
    trade_direction: str | None = None
    underlyings: list[Underlying] = Field(default_factory=list)
    tenor: str | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    pricing_date: date | None = None
    settlement_method: str | None = None
    coupon_structure: str | None = None
    annualized_rebate: float | None = None
    absolute_rebate: float | None = None
    front_back_annualized_return: str | None = None
    front_return: float | None = None
    remarks: str | None = None
    raw_text: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    validation_errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)

    def business_fields(self) -> dict[str, Any]:
        """Return values intended for tabular quote display."""
        return self.model_dump(
            mode="json",
            exclude={
                "raw_text",
                "evidence",
                "missing_fields",
                "validation_errors",
                "warnings",
            },
        )
