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


class CSVExporter:
    filename = "quote_table.csv"

    def render(self, result: ExtractionResult) -> str:
        row = quote_table_row(result)
        output = StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
        return output.getvalue()
