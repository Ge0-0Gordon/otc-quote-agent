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
        "annualized_rebate",
        "absolute_rebate",
        "strike_price",
        "autocall_barrier",
        "margin_ratio",
        "max_loss",
        "front_return",
    }
    DATE_FIELDS = {
        "quote_date",
        "trade_date",
        "start_date",
        "maturity_date",
        "pricing_date",
        "initial_price_date",
        "expiry_date",
    }
    CANONICAL_UNDERLYINGS = {
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
        "沪深300": {
            "name": "沪深300",
            "ticker": "000300.SH",
            "asset_class": "equity_index",
            "exchange": "SSE",
            "currency": "CNY",
        },
    }
    UNDERLYING_ALIASES = {
        "中证1000": "中证1000",
        "csi1000": "中证1000",
        "000852.sh": "中证1000",
        "中证500": "中证500",
        "csi500": "中证500",
        "000905.sh": "中证500",
        "沪深300": "沪深300",
        "csi300": "沪深300",
        "000300": "沪深300",
        "000300.sh": "沪深300",
    }

    def normalize(self, payload: dict[str, Any]) -> NormalizationResult:
        data = deepcopy(payload)
        issues: list[ValidationIssue] = []

        self._normalize_underlyings(data)
        if data.get("evidence") is None:
            data["evidence"] = []
        self._normalize_reference_coupon_terms(data)
        self._fallback_lockout_period(data)
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
        if data.get("lockout_period") is not None:
            try:
                data["lockout_period"] = self.parse_tenor(data["lockout_period"])
            except ValueError as exc:
                issues.append(
                    self._issue("lockout_period", "invalid_tenor", str(exc))
                )
                data["lockout_period"] = None

        currency = data.get("currency")
        if isinstance(currency, str):
            data["currency"] = currency.strip().upper()

        for field in ("observation_frequency", "coupon_frequency"):
            value = data.get(field)
            if isinstance(value, str):
                data[field] = self._normalize_frequency(value)

        return NormalizationResult(data=data, issues=issues)

    @staticmethod
    def _normalize_reference_coupon_terms(data: dict[str, Any]) -> None:
        raw_text = data.get("raw_text")
        if not isinstance(raw_text, str):
            return

        labeled_patterns = {
            "annualized_rebate": r"年化返息[^%\d]{0,20}(\d+(?:\.\d+)?)\s*[%％]",
            "absolute_rebate": r"(?:绝对返息|绝反)[^%\d]{0,20}(\d+(?:\.\d+)?)\s*[%％]",
        }
        for field, pattern in labeled_patterns.items():
            if data.get(field) in (None, ""):
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    data[field] = f"{match.group(1)}%"

        primary_coupon = re.search(
            r"敲出\s*(?:&|＆|和)\s*红利票息[^%\d]{0,30}(\d+(?:\.\d+)?)\s*[%％]",
            raw_text,
            re.IGNORECASE,
        )
        if primary_coupon:
            data["coupon_rate"] = f"{primary_coupon.group(1)}%"
            return

        if data.get("coupon_rate") not in (None, ""):
            return
        match = re.search(
            r"(?:票息|coupon)[^%\d]{0,30}(\d+(?:\.\d+)?)\s*[%％]",
            raw_text,
            re.IGNORECASE,
        )
        if match:
            data["coupon_rate"] = f"{match.group(1)}%"

    @staticmethod
    def _fallback_lockout_period(data: dict[str, Any]) -> None:
        if data.get("lockout_period") not in (None, ""):
            return
        raw_text = data.get("raw_text")
        if not isinstance(raw_text, str):
            return
        match = re.search(r"从第\s*(\d+)\s*个月开始观察", raw_text)
        if match is None:
            match = re.search(r"锁\s*(\d+)\s*(?:M|个月|月)?", raw_text, re.IGNORECASE)
        if match:
            data["lockout_period"] = f"{int(match.group(1))}M"

    def _normalize_observation_dates(
        self,
        data: dict[str, Any],
        issues: list[ValidationIssue],
    ) -> None:
        field = "knock_out_observation_dates"
        if field not in data:
            return
        if data[field] in (None, ""):
            data[field] = []
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
                mapped = self._canonical_underlying(value)
                normalized.append(mapped or {"name": value.strip()})
                continue
            item = dict(value)
            if not item.get("name") and item.get("ticker"):
                item["name"] = item["ticker"]
            name = item.get("name")
            mapped = self._canonical_underlying(name) if name else None
            if mapped is None and item.get("ticker"):
                mapped = self._canonical_underlying(item["ticker"])
            if mapped is not None:
                item = {
                    **{key: val for key, val in item.items() if val is not None},
                    **mapped,
                }
            normalized.append(item)
        data["underlyings"] = normalized

    @classmethod
    def _canonical_underlying(cls, value: str) -> dict[str, str] | None:
        normalized = value.casefold().strip()
        normalized = re.sub(r"[【】\[\]]", "", normalized)
        normalized = re.sub(r"[（(][^）)]*[）)]", "", normalized)
        normalized = normalized.replace("指数", "")
        normalized = re.sub(r"\s+", "", normalized)
        canonical_name = cls.UNDERLYING_ALIASES.get(normalized)
        if canonical_name is None:
            return None
        return dict(cls.CANONICAL_UNDERLYINGS[canonical_name])

    @staticmethod
    def parse_number(value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("Boolean is not a valid number.")
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        match = re.search(
            r"([-+]?\d+(?:\.\d+)?)\s*(亿|万|w|mn|mm|million|m|k)?",
            text,
            re.I,
        )
        if not match:
            raise ValueError(f"Cannot parse number: {value}")
        number = float(match.group(1))
        unit = (match.group(2) or "").lower()
        multiplier = {
            "亿": 100_000_000,
            "万": 10_000,
            "w": 10_000,
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
            result = number / 100 if abs(number) > 2 else number
            return round(result, 12)
        text = str(value).strip()
        has_percent_sign = "%" in text or "％" in text
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
        if not match:
            raise ValueError(f"Cannot parse percentage: {value}")
        number = float(match.group())
        result = number / 100 if has_percent_sign or abs(number) > 2 else number
        return round(result, 12)

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
