"""Canonical JSON rendering."""

from otc_quote_agent.schemas import ExtractionResult


class JSONExporter:
    filename = "extracted_quote.json"

    def render(self, result: ExtractionResult) -> str:
        return result.model_dump_json(indent=2)
