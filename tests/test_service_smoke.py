from pathlib import Path
from uuid import UUID

import pytest

from otc_quote_agent.schemas import ExtractionStatus, ProductType
from otc_quote_agent.service import QuoteExtractionService
from tests.fakes import FakeLLM


SAMPLE_DIR = Path(__file__).parents[1] / "sample_data"


@pytest.mark.parametrize(
    ("filename", "payload", "expected_product"),
    [
        (
            "snowball_inquiry_zh.txt",
            {
                "underlying": "中证1000",
                "notional": "1000万",
                "currency": "CNY",
                "tenor": "12个月",
                "knock_out_barrier": "103%",
                "knock_in_barrier": "75%",
                "coupon_rate": "15%",
                "observation_frequency": "月度",
                "lockout_period": "3M",
            },
            ProductType.SNOWBALL,
        ),
        (
            "fcn_quote_zh.txt",
            {
                "underlyings": ["AAPL", "MSFT", "TSLA"],
                "worst_of": True,
                "notional": "USD 1,000,000",
                "currency": "USD",
                "tenor": "一年期",
                "strike_price": "80%",
                "knock_in_barrier": "60%",
                "coupon_rate": "12%",
                "coupon_frequency": "每月",
                "observation_frequency": "每月",
            },
            ProductType.FCN,
        ),
        (
            "european_option_email_en.txt",
            {
                "underlying": "EURUSD",
                "notional": "EUR 5,000,000",
                "currency": "EUR",
                "tenor": "3-month",
                "option_type": "call",
                "position": "buy",
                "strike": 1.085,
                "settlement_method": "cash",
            },
            ProductType.EUROPEAN_OPTION,
        ),
    ],
)
def test_service_runs_offline_with_fake_llm(
    filename: str,
    payload: dict[str, object],
    expected_product: ProductType,
) -> None:
    service = QuoteExtractionService(FakeLLM([payload]))

    result = service.run(input_path=SAMPLE_DIR / filename)

    assert result.status is ExtractionStatus.SUCCESS
    assert result.product_type is expected_product
    assert result.quote is not None
    assert result.quote.raw_text


def test_unsupported_product_skips_quote_extraction() -> None:
    fake = FakeLLM([])
    service = QuoteExtractionService(fake)

    result = service.run(text="请报价一笔凤凰结构，期限一年。")

    assert result.status is ExtractionStatus.UNSUPPORTED
    assert result.quote is None
    assert fake.call_count == 0
    assert "extension_suggestion" in result.processing_metadata


def test_reference_case_13_preserves_two_quote_alternatives() -> None:
    service = QuoteExtractionService(
        FakeLLM(
            [
                {
                    "quote_candidates": [
                        {
                            "structure_name": "雪球方案一",
                            "underlying": "中证1000",
                            "notional": "1000万",
                            "currency": "CNY",
                            "tenor": "2年",
                            "lockout_period": "3M",
                            "knock_in_barrier": "65%",
                            "knock_out_barrier": "96%",
                            "coupon_structure": "敲出线递减0.75%",
                        },
                        {
                            "structure_name": "雪球方案二",
                            "underlying": "中证1000",
                            "notional": "1000万",
                            "currency": "CNY",
                            "tenor": "2年",
                            "lockout_period": "3M",
                            "knock_in_barrier": "65%",
                            "knock_out_barrier": "101%",
                            "coupon_structure": "敲出线递减1%",
                        },
                    ]
                }
            ]
        )
    )

    result = service.run(
        input_path=SAMPLE_DIR / "reference_case_13_snowball_two_choices.txt"
    )

    assert result.product_type is ProductType.SNOWBALL
    assert len(result.quote_candidates) == 2
    assert result.quote == result.quote_candidates[0]
    assert result.quote_candidates[0].knock_out_barrier == pytest.approx(0.96)
    assert result.quote_candidates[1].knock_out_barrier == pytest.approx(1.01)
    assert result.quote_candidates[0].coupon_structure == "敲出线递减0.75%"
    assert result.quote_candidates[1].coupon_structure == "敲出线递减1%"
    assert result.quote_candidates[0].coupon_rate is None
    assert result.quote_candidates[1].coupon_rate is None
    assert result.quote_candidates[0].annualized_rebate == pytest.approx(0.003)
    assert result.quote_candidates[1].annualized_rebate == pytest.approx(0.003)
    assert result.processing_metadata["quote_candidate_count"] == 2


def test_european_option_ignores_llm_managed_fields_and_sets_exercise_style() -> None:
    service = QuoteExtractionService(
        FakeLLM(
            [
                {
                    "quote_id": None,
                    "product_type": None,
                    "source_file": "invented.txt",
                    "source_type": None,
                    "raw_text": None,
                    "confidence": None,
                    "missing_fields": None,
                    "validation_errors": None,
                    "warnings": None,
                    "exercise_style": None,
                    "underlying": "EURUSD",
                    "notional": "EUR 5,000,000",
                    "currency": "EUR",
                    "tenor": "3-month",
                    "option_type": "call",
                    "position": "buy",
                    "strike": 1.085,
                    "settlement_method": "cash",
                }
            ]
        )
    )

    result = service.run(input_path=SAMPLE_DIR / "european_option_email_en.txt")

    assert result.quote is not None
    assert isinstance(result.quote.quote_id, str)
    UUID(result.quote.quote_id)
    assert result.quote.exercise_style == "european"
    assert result.quote.source_file == "european_option_email_en.txt"


def test_snowball_target_coupon_falls_back_from_raw_text() -> None:
    service = QuoteExtractionService(
        FakeLLM(
            [
                {
                    "underlying": "中证1000",
                    "notional": "1000万",
                    "currency": "CNY",
                    "tenor": "12个月",
                    "knock_out_barrier": "103%",
                    "knock_in_barrier": "75%",
                    "coupon_rate": None,
                    "observation_frequency": "月度",
                    "lockout_period": "3M",
                }
            ]
        )
    )

    result = service.run(input_path=SAMPLE_DIR / "snowball_inquiry_zh.txt")

    assert result.quote is not None
    assert result.quote.coupon_rate == pytest.approx(0.15)
    assert "coupon_rate" not in result.quote.missing_fields
    assert any(
        issue.code == "indicative_coupon_target"
        for issue in result.quote.warnings
    )


def test_service_writes_all_artifacts(tmp_path) -> None:
    payload = {
        "underlying": "中证1000",
        "notional": "1000万",
        "currency": "CNY",
        "tenor": "12个月",
        "knock_out_barrier": "103%",
        "knock_in_barrier": "75%",
        "coupon_rate": "15%",
        "observation_frequency": "月度",
    }
    service = QuoteExtractionService(FakeLLM([payload]))

    service.run(
        input_path=SAMPLE_DIR / "snowball_inquiry_zh.txt",
        output_dir=tmp_path,
    )

    assert {path.name for path in tmp_path.iterdir()} == {
        "extracted_quote-snowball.json",
        "quote_table.csv",
        "report.html",
    }


def test_reference_case_09_uses_official_terms_and_canonical_mapping() -> None:
    payload = {
        "structure_name": "限亏雪球",
        "underlying": {
            "name": "沪深300指数",
            "asset_class": "single_stock",
            "currency": "USD",
        },
        "notional": "不超过2000w",
        "currency": "CNY",
        "tenor": "36个月",
        "lockout_period": None,
        "knock_in_barrier": "70%",
        "knock_out_barrier": "100%",
        "margin_ratio": "50%",
        "max_loss": "50%",
        "coupon_rate": "9.21%",
        "coupon_structure": "年化返息0.3%；敲出&红利票息（年化）9.21%",
        "observation_frequency": "每月",
        "knock_out_observation_dates": None,
        "knock_in_observation_type": "daily",
        "evidence": None,
    }
    service = QuoteExtractionService(FakeLLM([payload]))

    result = service.run(
        input_path=SAMPLE_DIR / "reference_case_09_limited_loss_snowball.txt"
    )

    assert result.product_type is ProductType.SNOWBALL
    assert result.quote is not None
    assert result.quote.underlyings[0].ticker == "000300.SH"
    assert result.quote.underlyings[0].asset_class == "equity_index"
    assert result.quote.notional == 20_000_000
    assert result.quote.tenor == "36M"
    assert result.quote.lockout_period == "3M"
    assert result.quote.knock_in_barrier == pytest.approx(0.7)
    assert result.quote.knock_out_barrier == pytest.approx(1.0)
    assert result.quote.margin_ratio == pytest.approx(0.5)
    assert result.quote.max_loss == pytest.approx(0.5)
    assert result.quote.coupon_rate == pytest.approx(0.0921)
    assert result.quote.annualized_rebate == pytest.approx(0.003)
    assert result.processing_metadata["reference_case_id"] == "reference_case_09"


@pytest.mark.parametrize(
    "filename",
    [
        "reference_case_11_dcn_unsupported.txt",
        "reference_case_12_sharkfin_unsupported.txt",
    ],
)
def test_official_unsupported_cases_skip_llm(filename: str) -> None:
    fake = FakeLLM([])
    service = QuoteExtractionService(fake)

    result = service.run(input_path=SAMPLE_DIR / filename)

    assert result.status is ExtractionStatus.UNSUPPORTED
    assert result.quote is None
    assert fake.call_count == 0
