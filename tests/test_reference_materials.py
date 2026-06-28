from pathlib import Path

import yaml

from otc_quote_agent.schemas import BaseQuote


ROOT = Path(__file__).parents[1]


def test_reference_yaml_files_are_valid_and_cover_cases_7_to_13() -> None:
    terms = yaml.safe_load(
        (ROOT / "reference_materials/standard_derivative_terms.yaml").read_text(
            encoding="utf-8"
        )
    )
    cases = yaml.safe_load(
        (ROOT / "reference_materials/inquiry_cases.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert len(terms["terms"]) >= 15
    assert {case["case_id"] for case in cases["cases"]} == {
        f"reference_case_{number:02d}" for number in range(7, 14)
    }


def test_reference_term_fields_exist_in_base_schema() -> None:
    terms = yaml.safe_load(
        (ROOT / "reference_materials/standard_derivative_terms.yaml").read_text(
            encoding="utf-8"
        )
    )
    schema_fields = set(BaseQuote.model_fields)
    expected_base_fields = {
        "structure_name",
        "product_type",
        "underlyings",
        "notional",
        "trade_date",
        "start_date",
        "margin_ratio",
        "max_loss",
        "tenor",
        "coupon_structure",
        "annualized_rebate",
        "absolute_rebate",
        "front_back_annualized_return",
        "front_return",
        "remarks",
    }

    assert expected_base_fields <= schema_fields
    assert all(
        {
            "original_field",
            "suggested_schema_field",
            "suggested_type",
            "requirement_level",
            "notes",
        }
        <= set(term)
        for term in terms["terms"]
    )
