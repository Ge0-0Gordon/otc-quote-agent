"""Build deterministic field-level extraction provenance."""

from __future__ import annotations

import re
from typing import Any

from otc_quote_agent.schemas import FieldMetadata


SYSTEM_FIELDS = {
    "quote_id",
    "source_file",
    "source_type",
    "raw_text",
    "confidence",
    "product_type",
    "evidence",
    "field_metadata",
    "missing_fields",
    "validation_errors",
    "warnings",
}


def build_field_metadata(
    extracted: dict[str, Any],
    normalized: dict[str, Any],
    business_fields: set[str],
    raw_text: str,
) -> dict[str, FieldMetadata]:
    evidence = _evidence_by_field(extracted.get("evidence"), raw_text)
    metadata: dict[str, FieldMetadata] = {}

    for field in sorted(business_fields - SYSTEM_FIELDS):
        normalized_value = normalized.get(field)
        source_field = field
        original_value = extracted.get(field)
        if field == "underlyings" and original_value in (None, [], ""):
            source_field = "underlying"
            original_value = extracted.get("underlying")
        if normalized_value in (None, "", []):
            continue

        source_text = evidence.get(field) or evidence.get(source_field)
        if original_value in (None, "", []):
            method = "deterministic_fallback"
            confidence = 0.95 if source_text else 0.85
            was_normalized = True
        else:
            was_normalized = original_value != normalized_value
            if field == "underlyings" and _has_canonical_underlying(normalized_value):
                method = "llm+canonical_mapper"
                confidence = 0.98 if source_text else 0.95
            elif was_normalized:
                method = "llm+deterministic"
                confidence = 0.98 if source_text else 0.80
            else:
                method = "llm"
                confidence = 0.90 if source_text else 0.65

        metadata[field] = FieldMetadata(
            source_text=source_text,
            extraction_method=method,
            confidence=confidence,
            normalized=was_normalized,
        )
    return metadata


def evidence_coverage(metadata: dict[str, FieldMetadata]) -> float:
    if not metadata:
        return 0.0
    supported = sum(item.source_text is not None for item in metadata.values())
    return round(supported / len(metadata), 4)


def source_supports_evidence(source_text: str, raw_text: str) -> bool:
    """Accept exact evidence, whitespace wrapping, or verified source fragments."""

    normalized_source = _without_whitespace(source_text)
    normalized_raw = _without_whitespace(raw_text)
    if normalized_source in normalized_raw:
        return True
    fragments = [
        _without_whitespace(fragment)
        for fragment in re.split(r"[,，;；]", source_text)
        if fragment.strip()
    ]
    return len(fragments) > 1 and all(fragment in normalized_raw for fragment in fragments)


def _evidence_by_field(raw_evidence: Any, raw_text: str) -> dict[str, str]:
    if not isinstance(raw_evidence, list):
        return {}
    result: dict[str, str] = {}
    for item in raw_evidence:
        if not isinstance(item, dict):
            continue
        field = item.get("field")
        source_text = item.get("source_text")
        if (
            isinstance(field, str)
            and isinstance(source_text, str)
            and source_text.strip()
            and source_supports_evidence(source_text, raw_text)
        ):
            result.setdefault(field, source_text.strip())
    return result


def _without_whitespace(value: str) -> str:
    return "".join(value.split())


def _has_canonical_underlying(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("ticker") in {"000300.SH", "000852.SH", "000905.SH"}
        for item in value
    )
