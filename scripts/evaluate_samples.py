"""Run the offline golden sample evaluation and write a JSON report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from otc_quote_agent.evaluation import evaluate_result  # noqa: E402
from otc_quote_agent.service import QuoteExtractionService  # noqa: E402
from tests.fakes import FakeLLM  # noqa: E402


def main() -> int:
    dataset_path = PROJECT_ROOT / "reference_materials" / "golden_cases.yaml"
    dataset = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))

    case_reports = []
    for case in dataset["cases"]:
        responses = []
        if case.get("llm_response") is not None:
            responses.append(case["llm_response"])
        service = QuoteExtractionService(FakeLLM(responses))
        result = service.run(input_path=PROJECT_ROOT / case["input_file"])
        case_reports.append(
            evaluate_result(case["case_id"], result, case["expected"])
        )

    checked = sum(case.checked_fields for case in case_reports)
    matched = sum(case.matched_fields for case in case_reports)
    report = {
        "dataset_version": dataset["version"],
        "scope": "offline deterministic regression; not live LLM accuracy",
        "passed": all(case.passed for case in case_reports),
        "cases_passed": sum(case.passed for case in case_reports),
        "cases_total": len(case_reports),
        "field_accuracy": matched / checked if checked else 0.0,
        "checked_fields": checked,
        "matched_fields": matched,
        "cases": [case.as_dict() for case in case_reports],
    }

    output_path = PROJECT_ROOT / "outputs" / "evaluation_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Report: {output_path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
