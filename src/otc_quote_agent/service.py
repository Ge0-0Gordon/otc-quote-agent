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
from otc_quote_agent.schemas import (
    ExtractionResult,
    ExtractionStatus,
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
            extracted = self.extractor.extract(
                document.text,
                classification.product_type,
                schema,
                self.llm_client,
            )
            for field in self.SYSTEM_MANAGED_FIELDS:
                extracted.pop(field, None)
            extracted.update(
                {
                    "product_type": classification.product_type.value,
                    "source_file": document.source_file,
                    "source_type": document.source_type.value,
                    "raw_text": document.text,
                    "confidence": classification.confidence,
                }
            )
            if classification.product_type is ProductType.EUROPEAN_OPTION:
                extracted["exercise_style"] = "european"
            normalized = self.normalizer.normalize(extracted)
            quote = schema.model_validate(normalized.data)
        except (ValidationError, LLMResponseError) as exc:
            raise QuoteExtractionError(f"Quote extraction failed: {exc}") from exc

        quote = self.validator.validate(quote, normalized.issues)
        questions = self.reviewer.generate(quote.missing_fields)
        result = ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            product_type=classification.product_type,
            classification_reason=classification.reason,
            source_summary=self._summarize(document.text),
            quote=quote,
            review_questions=questions,
            processing_metadata={
                "provider": self.llm_client.provider_name,
                "model": self.llm_client.model,
                "source_type": document.source_type.value,
                "source_file": document.source_file,
                "reference_case_id": self._reference_case_id(document.source_file),
            },
        )
        if output_dir is not None:
            self.exporter.export(result, output_dir)
        return result

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
