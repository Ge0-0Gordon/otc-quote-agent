from otc_quote_agent.service import QuoteExtractionService
from tests.fakes import FakeLLM


def test_human_review_re_normalizes_and_revalidates_without_llm_call() -> None:
    fake = FakeLLM(
        [
            {
                "underlying": "中证1000",
                "notional": "1000万",
                "currency": "CNY",
                "tenor": "12个月",
                "knock_out_barrier": "103%",
                "knock_in_barrier": "75%",
                "coupon_rate": "15%",
                "observation_frequency": "每月",
            }
        ]
    )
    service = QuoteExtractionService(fake)
    result = service.run(text="中证1000雪球，票息15%，敲出103%，敲入75%")
    call_count = fake.call_count

    reviewed = service.apply_review(
        result,
        {
            "notional": "2000w",
            "coupon_rate": "16%",
        },
    )

    assert fake.call_count == call_count
    assert reviewed.quote is not None
    assert reviewed.quote.notional == 20_000_000
    assert reviewed.quote.coupon_rate == 0.16
    assert reviewed.quote.field_metadata["notional"].extraction_method == "human_review"
    assert reviewed.quote.field_metadata["notional"].confidence == 1.0
    assert reviewed.processing_metadata["human_reviewed"] is True
    assert len(reviewed.processing_metadata["review_corrections"]) == 2


def test_review_rejects_system_managed_fields() -> None:
    service = QuoteExtractionService(
        FakeLLM(
            [
                {
                    "underlying": "EURUSD",
                    "option_type": "call",
                    "position": "buy",
                    "strike": 1.1,
                }
            ]
        )
    )
    result = service.run(text="EURUSD European call strike 1.1")

    try:
        service.apply_review(result, {"product_type": "snowball"})
    except ValueError as exc:
        assert "managed fields" in str(exc)
    else:
        raise AssertionError("Managed review field should be rejected.")
