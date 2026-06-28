from otc_quote_agent.evaluation import evaluate_result, value_at_path
from otc_quote_agent.schemas import ExtractionResult, ExtractionStatus, ProductType


def test_value_at_path_supports_nested_lists() -> None:
    data = {"quote": {"underlyings": [{"ticker": "000300.SH"}]}}

    assert value_at_path(data, "quote.underlyings.0.ticker") == "000300.SH"
    assert value_at_path(data, "quote.underlyings.1.ticker") is None


def test_evaluator_reports_exact_field_mismatch() -> None:
    result = ExtractionResult(
        status=ExtractionStatus.UNSUPPORTED,
        product_type=ProductType.UNSUPPORTED,
        classification_reason="DCN",
        quote=None,
    )

    report = evaluate_result(
        "case",
        result,
        {
            "status": "unsupported",
            "product_type": "unsupported",
            "quote_is_null": True,
        },
    )

    assert report.passed
    assert report.checked_fields == 3


def test_evaluator_exposes_expected_and_actual_values() -> None:
    result = ExtractionResult(
        status=ExtractionStatus.UNSUPPORTED,
        product_type=ProductType.UNSUPPORTED,
        classification_reason="DCN",
        quote=None,
    )

    report = evaluate_result(
        "case",
        result,
        {
            "status": "success",
            "product_type": "snowball",
        },
    )

    assert not report.passed
    assert report.mismatches[0].path == "status"
    assert report.mismatches[0].expected == "success"
    assert report.mismatches[0].actual == "unsupported"
