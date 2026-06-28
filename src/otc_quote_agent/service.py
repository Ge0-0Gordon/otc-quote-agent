"""Shared orchestration service used by CLI and Streamlit."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from otc_quote_agent.agents import ProductClassifier, ReviewQuestionGenerator
from otc_quote_agent.agents.extractor import LLMExtractor
from otc_quote_agent.config import Settings
from otc_quote_agent.exporters import ExportBundle
from otc_quote_agent.llm import (
    LLMClient,
    LLMResponseError,
    OllamaClient,
    OpenAICompatibleClient,
)
from otc_quote_agent.normalizers import QuoteNormalizer
from otc_quote_agent.parsers import DocumentParser, ParsedDocument
from otc_quote_agent.provenance import build_field_metadata, evidence_coverage
from otc_quote_agent.schemas import (
    BaseQuote,
    ExtractionResult,
    ExtractionStatus,
    FieldMetadata,
    ProductType,
)
from otc_quote_agent.schemas.products import PRODUCT_SCHEMAS
from otc_quote_agent.validators import QuoteValidator


class QuoteExtractionError(RuntimeError):
    """Raised when a supported quote cannot be safely structured."""


class QuoteExtractionService:
    SYSTEM_MANAGED_FIELDS = {
        "quote_id",
        "source_file",
        "source_type",
        "raw_text",
        "confidence",
        "product_type",
        "missing_fields",
        "validation_errors",
        "warnings",
        "field_metadata",
    }

    def __init__(
        self,
        llm_client: LLMClient,
        parser: DocumentParser | None = None,
        classifier: ProductClassifier | None = None,
        extractor: LLMExtractor | None = None,
        normalizer: QuoteNormalizer | None = None,
        validator: QuoteValidator | None = None,
        reviewer: ReviewQuestionGenerator | None = None,
        exporter: ExportBundle | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.parser = parser or DocumentParser()
        self.classifier = classifier or ProductClassifier()
        self.extractor = extractor or LLMExtractor()
        self.normalizer = normalizer or QuoteNormalizer()
        self.validator = validator or QuoteValidator()
        self.reviewer = reviewer or ReviewQuestionGenerator()
        self.exporter = exporter or ExportBundle()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "QuoteExtractionService":
        resolved = settings or Settings.from_env()
        if resolved.llm_provider == "ollama":
            client: LLMClient = OllamaClient(
                base_url=resolved.llm_base_url,
                model=resolved.llm_model,
                timeout_seconds=resolved.llm_timeout_seconds,
            )
        else:
            client = OpenAICompatibleClient(
                base_url=resolved.llm_base_url,
                api_key=resolved.llm_api_key,
                model=resolved.llm_model,
                timeout_seconds=resolved.llm_timeout_seconds,
            )
        return cls(client)

    def run(
        self,
        *,
        text: str | None = None,
        input_path: str | Path | None = None,
        filename: str | None = None,
        content: bytes | None = None,
        output_dir: str | Path | None = None,
    ) -> ExtractionResult:
        document = self._parse_input(text, input_path, filename, content)
        classification = self.classifier.classify(
            document.text,
            llm_client=self.llm_client,
        )
        if classification.product_type in {
            ProductType.UNKNOWN,
            ProductType.UNSUPPORTED,
        }:
            result = self._unsupported_result(document, classification)
            if output_dir is not None:
                self.exporter.export(result, output_dir)
            return result

        schema = PRODUCT_SCHEMAS[classification.product_type]
        try:
            if self._contains_multiple_options(document.text):
                extracted_candidates = self.extractor.extract_candidates(
                    document.text,
                    classification.product_type,
                    schema,
                    self.llm_client,
                )
            else:
                extracted_candidates = [
                    self.extractor.extract(
                        document.text,
                        classification.product_type,
                        schema,
                        self.llm_client,
                    )
                ]
            quotes = []
            coverages = []
            for extracted in extracted_candidates:
                quote, coverage = self._build_quote(
                    extracted,
                    document,
                    classification,
                    schema,
                )
                quotes.append(quote)
                coverages.append(coverage)
        except (ValidationError, LLMResponseError) as exc:
            raise QuoteExtractionError(f"Quote extraction failed: {exc}") from exc

        quote = quotes[0]
        questions = self.reviewer.generate(quote.missing_fields)
        result = ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            product_type=classification.product_type,
            classification_reason=classification.reason,
            source_summary=self._summarize(document.text),
            quote=quote,
            quote_candidates=quotes if len(quotes) > 1 else [],
            review_questions=questions,
            processing_metadata={
                "provider": self.llm_client.provider_name,
                "model": self.llm_client.model,
                "source_type": document.source_type.value,
                "source_file": document.source_file,
                "reference_case_id": self._reference_case_id(document.source_file),
                "classification_confidence": classification.confidence,
                "evidence_coverage": round(sum(coverages) / len(coverages), 4),
                "quote_candidate_count": len(quotes),
            },
        )
        if output_dir is not None:
            self.exporter.export(result, output_dir)
        return result

    def _build_quote(
        self,
        extracted: dict[str, Any],
        document: ParsedDocument,
        classification: Any,
        schema: type[BaseQuote],
    ) -> tuple[BaseQuote, float]:
        cleaned = dict(extracted)
        for field in self.SYSTEM_MANAGED_FIELDS:
            cleaned.pop(field, None)
        llm_extracted = dict(cleaned)
        cleaned.update(
            {
                "product_type": classification.product_type.value,
                "source_file": document.source_file,
                "source_type": document.source_type.value,
                "raw_text": document.text,
                "confidence": classification.confidence,
            }
        )
        if classification.product_type is ProductType.EUROPEAN_OPTION:
            cleaned["exercise_style"] = "european"
        normalized = self.normalizer.normalize(cleaned)
        field_metadata = build_field_metadata(
            llm_extracted,
            normalized.data,
            set(schema.model_fields),
            document.text,
        )
        normalized.data["field_metadata"] = field_metadata
        quote = schema.model_validate(normalized.data)
        quote = self.validator.validate(quote, normalized.issues)
        return quote, evidence_coverage(field_metadata)

    def apply_review(
        self,
        result: ExtractionResult,
        updates: dict[str, Any],
    ) -> ExtractionResult:
        """Apply human corrections without making another provider call."""

        if result.quote is None:
            raise ValueError("Unsupported results do not contain a quote to review.")
        quote = result.quote
        schema = type(quote)
        allowed_fields = set(schema.model_fields) - self.SYSTEM_MANAGED_FIELDS
        unknown_fields = set(updates) - allowed_fields
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Review contains unknown or managed fields: {names}")

        original = quote.model_dump(mode="python")
        reviewed_data = dict(original)
        corrections: list[dict[str, Any]] = []
        for field, value in updates.items():
            if original.get(field) != value:
                corrections.append(
                    {
                        "field": field,
                        "original_value": original.get(field),
                        "corrected_value": value,
                    }
                )
                reviewed_data[field] = value

        normalized = self.normalizer.normalize(reviewed_data)
        metadata = dict(quote.field_metadata)
        for correction in corrections:
            field = correction["field"]
            metadata[field] = FieldMetadata(
                source_text=None,
                extraction_method="human_review",
                confidence=1.0,
                normalized=reviewed_data.get(field) != normalized.data.get(field),
            )
        normalized.data["field_metadata"] = metadata
        normalized.data["missing_fields"] = []
        normalized.data["validation_errors"] = []
        normalized.data["warnings"] = []
        try:
            reviewed_quote: BaseQuote = schema.model_validate(normalized.data)
        except ValidationError as exc:
            raise QuoteExtractionError(f"Reviewed quote is invalid: {exc}") from exc
        reviewed_quote = self.validator.validate(reviewed_quote, normalized.issues)

        processing_metadata = dict(result.processing_metadata)
        processing_metadata.update(
            {
                "human_reviewed": bool(corrections),
                "review_corrections": corrections,
            }
        )
        candidates = list(result.quote_candidates)
        if candidates:
            candidates[0] = reviewed_quote
        return result.model_copy(
            update={
                "quote": reviewed_quote,
                "quote_candidates": candidates,
                "review_questions": self.reviewer.generate(
                    reviewed_quote.missing_fields
                ),
                "processing_metadata": processing_metadata,
            }
        )

    def _parse_input(
        self,
        text: str | None,
        input_path: str | Path | None,
        filename: str | None,
        content: bytes | None,
    ) -> ParsedDocument:
        supplied = sum(
            (
                text is not None,
                input_path is not None,
                filename is not None or content is not None,
            )
        )
        if supplied != 1:
            raise ValueError("Provide exactly one of text, input_path, or filename/content.")
        if text is not None:
            return self.parser.parse_text(text)
        if input_path is not None:
            return self.parser.parse_path(input_path)
        if filename is None or content is None:
            raise ValueError("Both filename and content are required for uploaded files.")
        return self.parser.parse_bytes(filename, content)

    def _unsupported_result(
        self,
        document: ParsedDocument,
        classification: Any,
    ) -> ExtractionResult:
        return ExtractionResult(
            status=ExtractionStatus.UNSUPPORTED,
            product_type=classification.product_type,
            classification_reason=classification.reason,
            source_summary=self._summarize(document.text),
            quote=None,
            review_questions=[],
            processing_metadata={
                "provider": self.llm_client.provider_name,
                "model": self.llm_client.model,
                "source_type": document.source_type.value,
                "source_file": document.source_file,
                "reference_case_id": self._reference_case_id(document.source_file),
                "extension_suggestion": (
                    "Add a dedicated schema, normalization rules and validator "
                    "before enabling extraction for this product."
                ),
            },
        )

    @staticmethod
    def _summarize(text: str, limit: int = 300) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        return compact if len(compact) <= limit else f"{compact[:limit].rstrip()}…"

    @staticmethod
    def _reference_case_id(source_file: str | None) -> str | None:
        if source_file is None:
            return None
        match = re.search(r"(reference_case_\d+)", source_file, re.IGNORECASE)
        return match.group(1).lower() if match else None

    @staticmethod
    def _contains_multiple_options(text: str) -> bool:
        compact = re.sub(r"\s+", "", text).casefold()
        return "二选一" in compact or (
            "方案一" in compact and "方案二" in compact
        )
