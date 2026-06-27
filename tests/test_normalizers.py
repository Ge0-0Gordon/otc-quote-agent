from datetime import date

import pytest

from otc_quote_agent.normalizers import QuoteNormalizer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1000万人民币", 10_000_000),
        ("USD 1,000,000", 1_000_000),
        ("5m", 5_000_000),
    ],
)
def test_parse_notional(raw: str, expected: float) -> None:
    assert QuoteNormalizer.parse_number(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("103%", 1.03), ("15％", 0.15), (75, 0.75), (0.6, 0.6)],
)
def test_parse_percentage(raw: object, expected: float) -> None:
    assert QuoteNormalizer.parse_percent(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("12个月", "12M"), ("3-month", "3M"), ("一年期", "1Y"), ("2Y", "2Y")],
)
def test_parse_tenor(raw: str, expected: str) -> None:
    assert QuoteNormalizer.parse_tenor(raw) == expected


def test_normalizes_underlying_and_invalid_date() -> None:
    result = QuoteNormalizer().normalize(
        {
            "underlying": "中证1000",
            "quote_date": "not-a-date",
            "currency": "cny",
        }
    )

    assert result.data["underlyings"][0]["ticker"] == "000852.SH"
    assert result.data["currency"] == "CNY"
    assert result.data["quote_date"] is None
    assert result.issues[0].code == "invalid_date"


def test_parse_iso_date() -> None:
    assert QuoteNormalizer.parse_date("2026-06-28") == date(2026, 6, 28)


def test_normalizes_option_numeric_fields_and_observation_dates() -> None:
    result = QuoteNormalizer().normalize(
        {
            "strike": "1.0850",
            "premium": "USD 50,000",
            "knock_out_observation_dates": ["2026-07-01", "bad-date"],
        }
    )

    assert result.data["strike"] == 1.085
    assert result.data["premium"] == 50_000
    assert result.data["knock_out_observation_dates"] == [date(2026, 7, 1)]
    assert result.issues[0].code == "invalid_date"
