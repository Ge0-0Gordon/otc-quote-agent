from pathlib import Path

import yaml

from otc_quote_agent.agents import ProductClassifier
from otc_quote_agent.parsers import DocumentParser
from otc_quote_agent.schemas import BaseQuote, ProductType


ROOT = Path(__file__).parents[1]


def test_reference_yaml_files_are_valid_and_cover_cases_1_to_13() -> None:
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
        f"reference_case_{number:02d}" for number in range(1, 14)
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


def test_transcribed_image_cases_follow_supported_boundaries() -> None:
    parser = DocumentParser()
    classifier = ProductClassifier()

    for number in range(1, 6):
        path = next((ROOT / "sample_data").glob(f"reference_case_{number:02d}_*.txt"))
        result = classifier.classify(parser.parse_path(path).text)
        assert result.product_type is ProductType.SNOWBALL

    case_06 = ROOT / "sample_data" / "reference_case_06_phoenix_dcn_unsupported.txt"
    result = classifier.classify(parser.parse_path(case_06).text)
    assert result.product_type is ProductType.UNSUPPORTED
