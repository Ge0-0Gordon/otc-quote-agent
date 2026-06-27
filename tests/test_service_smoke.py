from pathlib import Path

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
        "extracted_quote.json",
        "quote_table.csv",
        "report.html",
    }
