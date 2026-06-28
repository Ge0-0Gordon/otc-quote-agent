"""Offline evaluation helpers for quote extraction regression cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from typing import Any

from otc_quote_agent.schemas import ExtractionResult


@dataclass(frozen=True)
class EvaluationMismatch:
    path: str
    expected: Any
    actual: Any


@dataclass
class CaseEvaluation:
    case_id: str
    passed: bool
    checked_fields: int
    matched_fields: int
    mismatches: list[EvaluationMismatch] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "checked_fields": self.checked_fields,
            "matched_fields": self.matched_fields,
            "mismatches": [
                {
                    "path": mismatch.path,
                    "expected": mismatch.expected,
                    "actual": mismatch.actual,
                }
                for mismatch in self.mismatches
            ],
        }


def evaluate_result(
    case_id: str,
    result: ExtractionResult,
    expected: dict[str, Any],
) -> CaseEvaluation:
    """Compare an extraction result with normalized expected values."""

    result_data = result.model_dump(mode="json")
    checks: dict[str, Any] = {
        "status": expected["status"],
        "product_type": expected["product_type"],
    }
    for path, value in expected.get("fields", {}).items():
        checks[f"quote.{path}"] = value
    if "quote_is_null" in expected:
        checks["quote"] = None if expected["quote_is_null"] else result_data["quote"]

    warning_codes = expected.get("warning_codes", [])
    if warning_codes:
        actual_codes = {
            warning["code"]
            for warning in (result_data.get("quote") or {}).get("warnings", [])
        }
        for code in warning_codes:
            checks[f"quote.warnings.code[{code}]"] = True
            result_data.setdefault("_warning_code_checks", {})[code] = code in actual_codes

    mismatches: list[EvaluationMismatch] = []
    for path, expected_value in checks.items():
        lookup_path = path
        if path.startswith("quote.warnings.code["):
            code = path.removeprefix("quote.warnings.code[").removesuffix("]")
            lookup_path = f"_warning_code_checks.{code}"
        actual_value = value_at_path(result_data, lookup_path)
        if not values_equal(expected_value, actual_value):
            mismatches.append(
                EvaluationMismatch(
                    path=path,
                    expected=expected_value,
                    actual=actual_value,
                )
            )

    checked = len(checks)
    return CaseEvaluation(
        case_id=case_id,
        passed=not mismatches,
        checked_fields=checked,
        matched_fields=checked - len(mismatches),
        mismatches=mismatches,
    )


def value_at_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (IndexError, ValueError):
                return None
        elif isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        else:
            return None
    return current


def values_equal(expected: Any, actual: Any) -> bool:
    if (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
    ):
        return isclose(float(expected), float(actual), rel_tol=1e-9, abs_tol=1e-12)
    return expected == actual
