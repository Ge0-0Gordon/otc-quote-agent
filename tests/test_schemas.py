from otc_quote_agent.schemas import (
    EuropeanOptionQuote,
    ExtractionResult,
    ExtractionStatus,
    ProductType,
    SnowballQuote,
)


def test_incomplete_quote_is_serializable() -> None:
    quote = SnowballQuote(raw_text="中证1000雪球")

    payload = quote.model_dump(mode="json")

    assert payload["product_type"] == "snowball"
    assert payload["notional"] is None


def test_extraction_result_can_represent_unsupported_product() -> None:
    result = ExtractionResult(
        status=ExtractionStatus.UNSUPPORTED,
        product_type=ProductType.UNSUPPORTED,
        classification_reason="Detected DCN keywords.",
        source_summary="A short DCN inquiry.",
    )

    assert result.quote is None
    assert result.model_dump(mode="json")["status"] == "unsupported"


def test_european_option_has_fixed_exercise_style() -> None:
    quote = EuropeanOptionQuote(raw_text="EURUSD option")

    assert quote.exercise_style == "european"
