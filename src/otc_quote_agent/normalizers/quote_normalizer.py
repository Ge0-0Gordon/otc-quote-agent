"""Normalize common OTC quote values before Pydantic validation."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from otc_quote_agent.schemas import IssueSeverity, ValidationIssue


@dataclass(frozen=True)
class NormalizationResult:
    data: dict[str, Any]
    issues: list[ValidationIssue]


class QuoteNormalizer:
    NUMBER_FIELDS = {
        "notional",
        "initial_price",
        "strike",
        "premium",
    }
    PERCENT_FIELDS = {
        "knock_out_barrier",
        "knock_in_barrier",
        "coupon_rate",
        "strike_price",
        "autocall_barrier",
    }
    DATE_FIELDS = {
        "quote_date",
        "start_date",
        "maturity_date",
        "pricing_date",
        "initial_price_date",
        "expiry_date",
    }
    UNDERLYING_MAP = {
        "中证1000": {
            "name": "中证1000",
            "ticker": "000852.SH",
            "asset_class": "equity_index",
            "exchange": "SSE",
            "currency": "CNY",
        },
        "中证500": {
            "name": "中证500",
            "ticker": "000905.SH",
            "asset_class": "equity_index",
            "exchange": "SSE",
            "currency": "CNY",
        },
    }

    def normalize(self, payload: dict[str, Any]) -> NormalizationResult:
        data = deepcopy(payload)
        issues: list[ValidationIssue] = []

        self._normalize_underlyings(data)
        for field in self.NUMBER_FIELDS:
            self._normalize_value(data, field, self.parse_number, issues)
        for field in self.PERCENT_FIELDS:
            self._normalize_value(data, field, self.parse_percent, issues)
        for field in self.DATE_FIELDS:
            self._normalize_value(data, field, self.parse_date, issues)
        self._normalize_observation_dates(data, issues)

        if data.get("tenor") is not None:
            try:
                data["tenor"] = self.parse_tenor(data["tenor"])
            except ValueError as exc:
                issues.append(self._issue("tenor", "invalid_tenor", str(exc)))
                data["tenor"] = None

        currency = data.get("currency")
        if isinstance(currency, str):
            data["currency"] = currency.strip().upper()

        for field in ("observation_frequency", "coupon_frequency"):
            value = data.get(field)
            if isinstance(value, str):
                data[field] = self._normalize_frequency(value)

        return NormalizationResult(data=data, issues=issues)

    def _normalize_observation_dates(
        self,
        data: dict[str, Any],
        issues: list[ValidationIssue],
    ) -> None:
        field = "knock_out_observation_dates"
        if field not in data or data[field] in (None, ""):
            return
        values = data[field]
        if not isinstance(values, list):
            values = [values]
        parsed = []
        for value in values:
            try:
                parsed.append(self.parse_date(value))
            except (TypeError, ValueError) as exc:
                issues.append(self._issue(field, "invalid_date", str(exc)))
        data[field] = parsed

    def _normalize_value(
        self,
        data: dict[str, Any],
        field: str,
        parser: Any,
        issues: list[ValidationIssue],
    ) -> None:
        if field not in data:
            return
        value = data.get(field)
        if value in (None, ""):
            data[field] = None
            return
        try:
            data[field] = parser(value)
        except (TypeError, ValueError) as exc:
            code = "invalid_percentage" if field in self.PERCENT_FIELDS else "invalid_value"
            if field in self.DATE_FIELDS:
                code = "invalid_date"
            issues.append(self._issue(field, code, str(exc)))
            data[field] = None

    def _normalize_underlyings(self, data: dict[str, Any]) -> None:
        raw = data.pop("underlying", None)
        values = data.get("underlyings")
        if not values and raw is not None:
            values = [raw]
        elif isinstance(values, (str, dict)):
            values = [values]
        if not values:
            data["underlyings"] = []
            return

        normalized = []
        for value in values:
            if isinstance(value, str):
                normalized.append(self.UNDERLYING_MAP.get(value.strip(), {"name": value.strip()}))
                continue
            item = dict(value)
            name = item.get("name")
            if name in self.UNDERLYING_MAP:
                mapped = dict(self.UNDERLYING_MAP[name])
                mapped.update({key: val for key, val in item.items() if val is not None})
                item = mapped
            normalized.append(item)
        data["underlyings"] = normalized

    @staticmethod
    def parse_number(value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("Boolean is not a valid number.")
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(亿|万|mn|mm|m|million|k)?", text, re.I)
        if not match:
            raise ValueError(f"Cannot parse number: {value}")
        number = float(match.group(1))
        unit = (match.group(2) or "").lower()
        multiplier = {
            "亿": 100_000_000,
            "万": 10_000,
            "mn": 1_000_000,
            "mm": 1_000_000,
            "m": 1_000_000,
            "million": 1_000_000,
            "k": 1_000,
        }.get(unit, 1)
        return number * multiplier

    @staticmethod
    def parse_percent(value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("Boolean is not a valid percentage.")
        if isinstance(value, (int, float)):
            number = float(value)
            return number / 100 if abs(number) > 2 else number
        text = str(value).strip()
        has_percent_sign = "%" in text or "％" in text
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
        if not match:
            raise ValueError(f"Cannot parse percentage: {value}")
        number = float(match.group())
        return number / 100 if has_percent_sign or abs(number) > 2 else number

    @staticmethod
    def parse_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {value}")

    @staticmethod
    def parse_tenor(value: Any) -> str:
        text = str(value).strip().casefold()
        if re.fullmatch(r"\d+\s*[dmyw]", text):
            return text.replace(" ", "").upper()
        patterns = (
            (r"(\d+)\s*-?\s*(?:个月|月|months?|mos?)", "M"),
            (r"(\d+)\s*-?\s*(?:年|years?|yrs?)", "Y"),
            (r"(\d+)\s*-?\s*(?:天|days?)", "D"),
            (r"(\d+)\s*-?\s*(?:周|weeks?)", "W"),
        )
        if "一年" in text:
            return "1Y"
        for pattern, suffix in patterns:
            match = re.search(pattern, text)
            if match:
                return f"{int(match.group(1))}{suffix}"
        raise ValueError(f"Cannot parse tenor: {value}")

    @staticmethod
    def _normalize_frequency(value: str) -> str:
        text = value.strip().casefold()
        mapping = {
            "月度": "monthly",
            "每月": "monthly",
            "monthly": "monthly",
            "季度": "quarterly",
            "每季": "quarterly",
            "quarterly": "quarterly",
            "annual": "annually",
            "annually": "annually",
            "年度": "annually",
        }
        return mapping.get(text, text)

    @staticmethod
    def _issue(field: str, code: str, message: str) -> ValidationIssue:
        return ValidationIssue(
            field=field,
            severity=IssueSeverity.ERROR,
            code=code,
            message=message,
        )
