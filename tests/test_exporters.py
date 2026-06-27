import csv
import json
from io import StringIO

from otc_quote_agent.exporters import ExportBundle
from otc_quote_agent.schemas import (
    ExtractionResult,
    ExtractionStatus,
    ProductType,
    SnowballQuote,
)


def make_result() -> ExtractionResult:
    return ExtractionResult(
        status=ExtractionStatus.SUCCESS,
        product_type=ProductType.SNOWBALL,
        classification_reason="Matched 雪球",
        source_summary="中证1000雪球",
        quote=SnowballQuote(
            raw_text="中证1000雪球，敲出103%",
            underlyings=[{"name": "中证1000"}],
            knock_out_barrier=1.03,
            coupon_rate=0.15,
        ),
    )


def test_export_bundle_writes_required_files(tmp_path) -> None:
    paths = ExportBundle().export(make_result(), tmp_path)

    assert set(paths) == {
        "extracted_quote.json",
        "quote_table.csv",
        "report.html",
    }
    assert all(path.is_file() for path in paths.values())


def test_json_keeps_decimal_percentage_and_reports_show_percent() -> None:
    rendered = ExportBundle().render_all(make_result())
    payload = json.loads(rendered["extracted_quote.json"])
    csv_row = next(csv.DictReader(StringIO(rendered["quote_table.csv"])))

    assert payload["quote"]["knock_out_barrier"] == 1.03
    assert csv_row["knock_out_barrier"] == "103%"
    assert "103%" in rendered["report.html"]
    assert "15%" in rendered["report.html"]


def test_unsupported_report_contains_no_quote_fields() -> None:
    result = ExtractionResult(
        status=ExtractionStatus.UNSUPPORTED,
        product_type=ProductType.UNSUPPORTED,
        classification_reason="Detected unsupported product: Phoenix",
        source_summary="凤凰结构询价",
        processing_metadata={"extension_suggestion": "Add a Phoenix schema."},
    )

    rendered = ExportBundle().render_all(result)

    assert "No supported product schema was applied" in rendered["report.html"]
    assert json.loads(rendered["extracted_quote.json"])["quote"] is None
