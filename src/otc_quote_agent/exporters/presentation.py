"""Shared presentation formatting for UI and reports."""

from __future__ import annotations

import json
from typing import Any


PERCENT_FIELDS = {
    "knock_out_barrier",
    "knock_in_barrier",
    "coupon_rate",
    "annualized_rebate",
    "absolute_rebate",
    "strike_price",
    "autocall_barrier",
    "margin_ratio",
    "max_loss",
    "front_return",
}


def format_display_value(field: str, value: Any) -> str:
    if value is None:
        return ""
    if field in PERCENT_FIELDS and isinstance(value, (int, float)):
        percentage = f"{value * 100:.4f}".rstrip("0").rstrip(".")
        return f"{percentage}%"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
