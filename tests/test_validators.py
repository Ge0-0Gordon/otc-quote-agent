from datetime import date

from otc_quote_agent.schemas import EuropeanOptionQuote, FCNQuote, SnowballQuote
from otc_quote_agent.validators import QuoteValidator


def test_snowball_required_fields_and_lockout_warning() -> None:
    quote = SnowballQuote(
        raw_text="snowball",
        notional=10_000_000,
        currency="CNY",
        tenor="12M",
        quote_date=date(2026, 6, 28),
        start_date=date(2026, 7, 1),
        maturity_date=date(2027, 7, 1),
        underlyings=[{"name": "中证1000"}],
        initial_price=6000,
        initial_price_date=date(2026, 7, 1),
        knock_out_barrier=1.03,
        knock_in_barrier=0.75,
        coupon_rate=0.15,
        observation_frequency="monthly",
    )

    validated = QuoteValidator().validate(quote)

    assert validated.missing_fields == []
    assert validated.warnings[0].code == "missing_lockout_period"


def test_snowball_sample_reports_expected_dates_and_initial_price() -> None:
    quote = SnowballQuote(
        raw_text="希望年化票息不低于15%",
        notional=10_000_000,
        currency="CNY",
        tenor="12M",
        underlyings=[{"name": "中证1000"}],
        knock_out_barrier=1.03,
        knock_in_barrier=0.75,
        coupon_rate=0.15,
        observation_frequency="monthly",
        lockout_period="3M",
    )

    validated = QuoteValidator().validate(quote)

    assert {"quote_date", "start_date", "maturity_date", "initial_price", "initial_price_date"} <= set(
        validated.missing_fields
    )
    assert any(issue.code == "indicative_coupon_target" for issue in validated.warnings)


def test_snowball_invalid_barrier_order() -> None:
    quote = SnowballQuote(
        raw_text="snowball",
        knock_out_barrier=0.7,
        knock_in_barrier=0.8,
    )

    validated = QuoteValidator().validate(quote)

    assert any(issue.code == "invalid_barrier_order" for issue in validated.validation_errors)


def test_multi_underlying_fcn_requires_worst_of() -> None:
    quote = FCNQuote(
        raw_text="FCN",
        underlyings=[{"name": "AAPL"}, {"name": "MSFT"}],
        worst_of=False,
    )

    validated = QuoteValidator().validate(quote)

    assert "worst_of" not in validated.missing_fields
    assert any(issue.code == "ambiguous_worst_of" for issue in validated.validation_errors)


def test_option_reports_missing_premium() -> None:
    quote = EuropeanOptionQuote(
        raw_text="option",
        option_type="call",
        position="buy",
        strike=1.085,
        expiry_date=date(2026, 9, 28),
    )

    validated = QuoteValidator().validate(quote)

    assert "premium" in validated.missing_fields
