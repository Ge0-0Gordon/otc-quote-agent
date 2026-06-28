"""Single-row quote table rendering."""

from __future__ import annotations

import csv
from io import StringIO

from otc_quote_agent.exporters.presentation import format_display_value
from otc_quote_agent.schemas import ExtractionResult


def quote_table_row(result: ExtractionResult) -> dict[str, str]:
    if result.quote is None:
        return {
            "status": result.status.value,
            "product_type": result.product_type.value,
            "classification_reason": result.classification_reason,
            "source_summary": result.source_summary or "",
        }
    payload = result.quote.business_fields()
    return {
        field: format_display_value(field, value)
        for field, value in payload.items()
    }


def quote_table_rows(result: ExtractionResult) -> list[dict[str, str]]:
    if not result.quote_candidates:
        return [quote_table_row(result)]
    rows = []
    for index, quote in enumerate(result.quote_candidates, start=1):
        row = {
            field: format_display_value(field, value)
            for field, value in quote.business_fields().items()
        }
        rows.append({"candidate_index": str(index), **row})
    return rows


class CSVExporter:
    filename = "quote_table.csv"

    def render(self, result: ExtractionResult) -> str:
        rows = quote_table_rows(result)
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        output = StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
