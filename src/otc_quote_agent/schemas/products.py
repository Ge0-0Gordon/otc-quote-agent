"""Product-specific quote schemas."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from otc_quote_agent.schemas.common import BaseQuote, ProductType


class SnowballQuote(BaseQuote):
    product_type: Literal[ProductType.SNOWBALL] = ProductType.SNOWBALL
    initial_price: float | None = None
    initial_price_date: date | None = None
    knock_out_barrier: float | None = None
    knock_in_barrier: float | None = None
    coupon_rate: float | None = None
    observation_frequency: str | None = None
    knock_out_observation_dates: list[date] = Field(default_factory=list)
    knock_in_observation_type: str | None = None
    lockout_period: str | None = None
    redemption_rule: str | None = None
    coupon_payment_rule: str | None = None
    principal_protection: bool | None = None


class FCNQuote(BaseQuote):
    product_type: Literal[ProductType.FCN] = ProductType.FCN
    worst_of: bool | None = None
    strike_price: float | None = None
    knock_in_barrier: float | None = None
    coupon_rate: float | None = None
    coupon_frequency: str | None = None
    observation_frequency: str | None = None
    memory_coupon: bool | None = None
    autocall_barrier: float | None = None
    redemption_rule: str | None = None


class EuropeanOptionQuote(BaseQuote):
    product_type: Literal[ProductType.EUROPEAN_OPTION] = (
        ProductType.EUROPEAN_OPTION
    )
    option_type: Literal["call", "put"] | None = None
    position: Literal["buy", "sell"] | None = None
    strike: float | None = None
    expiry_date: date | None = None
    premium: float | None = None
    exercise_style: Literal["european"] = "european"


QuoteModel = SnowballQuote | FCNQuote | EuropeanOptionQuote


PRODUCT_SCHEMAS: dict[ProductType, type[BaseQuote]] = {
    ProductType.SNOWBALL: SnowballQuote,
    ProductType.FCN: FCNQuote,
    ProductType.EUROPEAN_OPTION: EuropeanOptionQuote,
}
