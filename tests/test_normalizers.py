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


@pytest.mark.parametrize("raw", ["2000w", "2000W", "不超过2000w"])
def test_parse_w_as_ten_thousand(raw: str) -> None:
    assert QuoteNormalizer.parse_number(raw) == 20_000_000


def test_explicit_reference_notional_unit_overrides_bare_llm_number() -> None:
    result = QuoteNormalizer().normalize(
        {
            "notional": 2000,
            "raw_text": "名义本金：【不超过2000w】",
        }
    )

    assert result.data["notional"] == 20_000_000


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("103%", 1.03),
        ("15％", 0.15),
        ("9.21%", 0.0921),
        (75, 0.75),
        (0.6, 0.6),
    ],
)
def test_parse_percentage(raw: object, expected: float) -> None:
    assert QuoteNormalizer.parse_percent(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12个月", "12M"),
        ("3-month", "3M"),
        ("一年期", "1Y"),
        ("2Y", "2Y"),
        ("前三个月", "3M"),
    ],
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


def test_underlying_ticker_fills_missing_name() -> None:
    result = QuoteNormalizer().normalize(
        {"underlyings": [{"name": None, "ticker": "AAPL"}]}
    )

    assert result.data["underlyings"][0]["name"] == "AAPL"


@pytest.mark.parametrize(
    ("raw", "ticker"),
    [
        ("沪深300", "000300.SH"),
        ("沪深300指数", "000300.SH"),
        ("CSI300", "000300.SH"),
        ("CSI 300", "000300.SH"),
        ("中证1000", "000852.SH"),
        ("中证1000指数", "000852.SH"),
        ("CSI1000", "000852.SH"),
        ("CSI 1000", "000852.SH"),
        ("中证500", "000905.SH"),
        ("中证500指数", "000905.SH"),
        ("CSI500", "000905.SH"),
        ("CSI 500", "000905.SH"),
    ],
)
def test_official_index_aliases(raw: str, ticker: str) -> None:
    result = QuoteNormalizer().normalize({"underlying": raw})

    assert result.data["underlyings"][0]["ticker"] == ticker
    assert result.data["underlyings"][0]["asset_class"] == "equity_index"


def test_canonical_underlying_overrides_llm_reference_data() -> None:
    result = QuoteNormalizer().normalize(
        {
            "underlyings": [
                {
                    "name": "沪深300指数",
                    "ticker": "WRONG",
                    "asset_class": "single_stock",
                    "exchange": "WRONG",
                    "currency": "USD",
                }
            ]
        }
    )

    assert result.data["underlyings"][0] == {
        "name": "沪深300",
        "ticker": "000300.SH",
        "asset_class": "equity_index",
        "exchange": "SSE",
        "currency": "CNY",
    }


def test_reference_percentages_and_lockout_are_normalized() -> None:
    result = QuoteNormalizer().normalize(
        {
            "margin_ratio": "50%",
            "max_loss": "50%",
            "front_return": "0.3%",
            "lockout_period": None,
            "raw_text": "交易期限36个月，从第3个月开始观察",
        }
    )

    assert result.data["margin_ratio"] == 0.5
    assert result.data["max_loss"] == 0.5
    assert result.data["front_return"] == 0.003
    assert result.data["lockout_period"] == "3M"


def test_official_coupon_terms_are_split_by_source_labels() -> None:
    result = QuoteNormalizer().normalize(
        {
            "coupon_rate": 0.3,
            "raw_text": (
                "年化返息：【0.3%】；绝对返息1.5%；"
                "敲出&红利票息（年化）：【9.21%】"
            ),
        }
    )

    assert result.data["annualized_rebate"] == 0.003
    assert result.data["absolute_rebate"] == 0.015
    assert result.data["coupon_rate"] == 0.0921


def test_reference_labels_override_wrong_numeric_llm_semantics() -> None:
    result = QuoteNormalizer().normalize(
        {
            "coupon_rate": 0.75,
            "annualized_rebate": 0.3,
            "lockout_period": "第二个月",
            "raw_text": (
                "中证1000 2年 锁3 65-96 递减0.75%；"
                "年化返息0.3%，二选一"
            ),
        }
    )

    assert result.data["coupon_rate"] is None
    assert result.data["annualized_rebate"] == 0.003
    assert result.data["lockout_period"] == "3M"


def test_explicit_observation_start_overrides_wrong_llm_lockout() -> None:
    result = QuoteNormalizer().normalize(
        {
            "lockout_period": "第二个月",
            "raw_text": "交易期限36个月，从第3个月开始观察",
        }
    )

    assert result.data["lockout_period"] == "3M"


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
