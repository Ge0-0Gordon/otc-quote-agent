from otc_quote_agent.provenance import (
    build_field_metadata,
    evidence_coverage,
    source_supports_evidence,
)


def test_provenance_distinguishes_normalized_and_llm_only_fields() -> None:
    extracted = {
        "notional": "2000w",
        "currency": "CNY",
        "evidence": [
            {"field": "notional", "source_text": "名义本金2000w"},
        ],
    }
    normalized = {"notional": 20_000_000.0, "currency": "CNY"}

    metadata = build_field_metadata(
        extracted,
        normalized,
        {"notional", "currency"},
        "询价：名义本金2000w",
    )

    assert metadata["notional"].extraction_method == "llm+deterministic"
    assert metadata["notional"].confidence == 0.98
    assert metadata["notional"].source_text == "名义本金2000w"
    assert metadata["currency"].extraction_method == "llm"
    assert metadata["currency"].confidence == 0.65
    assert evidence_coverage(metadata) == 0.5


def test_provenance_marks_system_fallback() -> None:
    metadata = build_field_metadata(
        {"coupon_rate": None},
        {"coupon_rate": 0.15},
        {"coupon_rate"},
        "目标票息15%",
    )

    assert metadata["coupon_rate"].extraction_method == "deterministic_fallback"
    assert metadata["coupon_rate"].normalized is True


def test_evidence_support_allows_wrapping_and_verified_fragments() -> None:
    raw_text = "Notional EUR\n5,000,000.\n敲出100%\n每月观察"

    assert source_supports_evidence("EUR 5,000,000", raw_text)
    assert source_supports_evidence("敲出100%, 每月观察", raw_text)
    assert not source_supports_evidence("敲出100%, 每日观察", raw_text)
