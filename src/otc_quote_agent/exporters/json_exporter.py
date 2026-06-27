"""Canonical JSON rendering."""

from otc_quote_agent.schemas import ExtractionResult


class JSONExporter:
    def filename_for(self, result: ExtractionResult) -> str:
        return f"extracted_quote-{result.product_type.value}.json"

    def render(self, result: ExtractionResult) -> str:
        return result.model_dump_json(indent=2)
