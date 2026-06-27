"""Business completeness and consistency rules."""

from __future__ import annotations

from otc_quote_agent.schemas import (
    BaseQuote,
    EuropeanOptionQuote,
    FCNQuote,
    IssueSeverity,
    SnowballQuote,
    ValidationIssue,
)


class QuoteValidator:
    def validate(
        self,
        quote: BaseQuote,
        preexisting_errors: list[ValidationIssue] | None = None,
    ) -> BaseQuote:
        missing: list[str] = []
        errors = list(preexisting_errors or [])
        warnings: list[ValidationIssue] = []

        self._require(quote.notional, "notional", missing)
        self._require(quote.currency, "currency", missing)
        self._require(quote.quote_date, "quote_date", missing)
        if quote.tenor is None and quote.maturity_date is None:
            missing.append("tenor_or_maturity_date")
        if not quote.underlyings:
            missing.append("underlyings")

        if quote.notional is not None and quote.notional <= 0:
            errors.append(self._error("notional", "non_positive", "Notional must be positive."))
        self._validate_date_order(quote, errors)

        if isinstance(quote, SnowballQuote):
            self._validate_snowball(quote, missing, errors, warnings)
        elif isinstance(quote, FCNQuote):
            self._validate_fcn(quote, missing, errors, warnings)
        elif isinstance(quote, EuropeanOptionQuote):
            self._validate_option(quote, missing)
        self._warn_if_coupon_is_target(quote, warnings)

        update = {
            "missing_fields": list(dict.fromkeys(missing)),
            "validation_errors": errors,
            "warnings": warnings,
        }
        return quote.model_copy(update=update)

    def _validate_snowball(
        self,
        quote: SnowballQuote,
        missing: list[str],
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        for field in (
            "start_date",
            "maturity_date",
            "initial_price",
            "initial_price_date",
            "knock_out_barrier",
            "knock_in_barrier",
            "coupon_rate",
            "observation_frequency",
        ):
            self._require(getattr(quote, field), field, missing)
        if (
            quote.knock_out_barrier is not None
            and quote.knock_in_barrier is not None
            and quote.knock_out_barrier <= quote.knock_in_barrier
        ):
            errors.append(
                self._error(
                    "knock_out_barrier",
                    "invalid_barrier_order",
                    "Knock-out barrier should be higher than knock-in barrier.",
                )
            )
        if quote.lockout_period is None:
            warnings.append(
                self._warning(
                    "lockout_period",
                    "missing_lockout_period",
                    "Lockout period is not specified.",
                )
            )
        if len(quote.underlyings) > 1:
            errors.append(
                self._error(
                    "underlyings",
                    "expected_single_underlying",
                    "Snowball quote should contain exactly one underlying.",
                )
            )

    @staticmethod
    def _warn_if_coupon_is_target(
        quote: BaseQuote,
        warnings: list[ValidationIssue],
    ) -> None:
        coupon_rate = getattr(quote, "coupon_rate", None)
        target_markers = ("希望", "不低于", "目标", "target", "at least")
        if coupon_rate is not None and any(
            marker in quote.raw_text.casefold() for marker in target_markers
        ):
            warnings.append(
                QuoteValidator._warning(
                    "coupon_rate",
                    "indicative_coupon_target",
                    "Coupon appears to be a client target rather than a firm quote.",
                )
            )

    def _validate_fcn(
        self,
        quote: FCNQuote,
        missing: list[str],
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
    ) -> None:
        for field in (
            "coupon_rate",
            "strike_price",
            "knock_in_barrier",
            "coupon_frequency",
            "worst_of",
        ):
            self._require(getattr(quote, field), field, missing)
        if len(quote.underlyings) > 1 and quote.worst_of is not True:
            errors.append(
                self._error(
                    "worst_of",
                    "ambiguous_worst_of",
                    "Multi-underlying FCN must explicitly confirm worst-of structure.",
                )
            )
        for field in ("counterparty", "autocall_barrier", "redemption_rule"):
            if getattr(quote, field) is None:
                warnings.append(
                    self._warning(
                        field,
                        f"missing_{field}",
                        f"FCN {field.replace('_', ' ')} is not specified.",
                    )
                )

    def _validate_option(
        self,
        quote: EuropeanOptionQuote,
        missing: list[str],
    ) -> None:
        for field in ("option_type", "position", "strike", "expiry_date", "premium"):
            self._require(getattr(quote, field), field, missing)

    @staticmethod
    def _validate_date_order(
        quote: BaseQuote,
        errors: list[ValidationIssue],
    ) -> None:
        end_date = quote.maturity_date
        if isinstance(quote, EuropeanOptionQuote):
            end_date = quote.expiry_date or end_date
        if quote.start_date and end_date and quote.start_date >= end_date:
            errors.append(
                QuoteValidator._error(
                    "start_date",
                    "invalid_date_order",
                    "Start date must be earlier than maturity or expiry date.",
                )
            )

    @staticmethod
    def _require(value: object, field: str, missing: list[str]) -> None:
        if value is None or value == "" or value == []:
            missing.append(field)

    @staticmethod
    def _error(field: str, code: str, message: str) -> ValidationIssue:
        return ValidationIssue(
            field=field,
            severity=IssueSeverity.ERROR,
            code=code,
            message=message,
        )

    @staticmethod
    def _warning(field: str, code: str, message: str) -> ValidationIssue:
        return ValidationIssue(
            field=field,
            severity=IssueSeverity.WARNING,
            code=code,
            message=message,
        )
