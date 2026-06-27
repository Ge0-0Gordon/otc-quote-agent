"""Self-contained HTML result report."""

from __future__ import annotations

import html

from otc_quote_agent.exporters.presentation import format_display_value
from otc_quote_agent.schemas import ExtractionResult


class HTMLExporter:
    filename = "report.html"

    def render(self, result: ExtractionResult) -> str:
        sections = [
            "<h1>OTC Quote Structuring Report</h1>",
            self._summary(result),
        ]
        if result.quote is None:
            sections.append(
                "<section><h2>Unsupported product</h2>"
                "<p>No supported product schema was applied and no quote fields "
                "were generated.</p>"
                f"<p><strong>Extension suggestion:</strong> "
                f"{self._escape(result.processing_metadata.get('extension_suggestion', ''))}"
                "</p></section>"
            )
        else:
            sections.extend(
                [
                    self._quote_table(result),
                    self._issues(result),
                    self._evidence(result),
                    self._review_questions(result),
                    "<section><h2>Source text</h2>"
                    f"<pre>{self._escape(result.quote.raw_text)}</pre></section>",
                ]
            )
        body = "\n".join(sections)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OTC Quote Structuring Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem auto; max-width: 1100px;
            color: #1f2937; line-height: 1.5; }}
    h1, h2 {{ color: #0f3d56; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #d1d5db; padding: .55rem; text-align: left;
              vertical-align: top; }}
    th {{ background: #eef5f7; width: 28%; }}
    .error {{ color: #b91c1c; }}
    .warning {{ color: #92400e; }}
    pre {{ white-space: pre-wrap; background: #f8fafc; padding: 1rem; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""

    def _summary(self, result: ExtractionResult) -> str:
        return (
            "<section><h2>Summary</h2><table>"
            f"<tr><th>Status</th><td>{self._escape(result.status.value)}</td></tr>"
            f"<tr><th>Product type</th><td>{self._escape(result.product_type.value)}</td></tr>"
            f"<tr><th>Classification reason</th><td>{self._escape(result.classification_reason)}</td></tr>"
            f"<tr><th>Source summary</th><td>{self._escape(result.source_summary or '')}</td></tr>"
            "</table></section>"
        )

    def _quote_table(self, result: ExtractionResult) -> str:
        assert result.quote is not None
        rows = []
        for field, value in result.quote.business_fields().items():
            rows.append(
                f"<tr><th>{self._escape(field)}</th>"
                f"<td>{self._escape(format_display_value(field, value))}</td></tr>"
            )
        return "<section><h2>Normalized quote</h2><table>" + "".join(rows) + "</table></section>"

    def _issues(self, result: ExtractionResult) -> str:
        assert result.quote is not None
        missing = "".join(
            f"<li>{self._escape(field)}</li>" for field in result.quote.missing_fields
        ) or "<li>None</li>"
        errors = "".join(
            f'<li class="error">{self._escape(issue.field)}: '
            f"{self._escape(issue.message)}</li>"
            for issue in result.quote.validation_errors
        ) or "<li>None</li>"
        warnings = "".join(
            f'<li class="warning">{self._escape(issue.field)}: '
            f"{self._escape(issue.message)}</li>"
            for issue in result.quote.warnings
        ) or "<li>None</li>"
        return (
            "<section><h2>Quality report</h2>"
            f"<h3>Missing fields</h3><ul>{missing}</ul>"
            f"<h3>Validation errors</h3><ul>{errors}</ul>"
            f"<h3>Warnings</h3><ul>{warnings}</ul></section>"
        )

    def _evidence(self, result: ExtractionResult) -> str:
        assert result.quote is not None
        rows = "".join(
            "<tr>"
            f"<td>{self._escape(item.field)}</td>"
            f"<td>{self._escape(item.source_text)}</td>"
            f"<td>{self._escape(item.location or '')}</td>"
            "</tr>"
            for item in result.quote.evidence
        )
        if not rows:
            return "<section><h2>Evidence</h2><p>No evidence supplied.</p></section>"
        return (
            "<section><h2>Evidence</h2><table>"
            "<tr><th>Field</th><th>Source text</th><th>Location</th></tr>"
            f"{rows}</table></section>"
        )

    def _review_questions(self, result: ExtractionResult) -> str:
        items = "".join(
            f"<li>{self._escape(question)}</li>"
            for question in result.review_questions
        ) or "<li>None</li>"
        return f"<section><h2>Review questions</h2><ul>{items}</ul></section>"

    @staticmethod
    def _escape(value: object) -> str:
        return html.escape(str(value), quote=True)
