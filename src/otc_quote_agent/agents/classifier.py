"""Rule-first OTC product classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from otc_quote_agent.schemas import ProductType


class ProductClassificationClient(Protocol):
    def classify_product(self, text: str) -> ProductType:
        """Classify text with an external model."""


@dataclass(frozen=True)
class ClassificationResult:
    product_type: ProductType
    confidence: float
    reason: str


class ProductClassifier:
    """Use deterministic keywords, then optionally ask an LLM."""

    SUPPORTED_KEYWORDS: dict[ProductType, tuple[str, ...]] = {
        ProductType.SNOWBALL: (
            "雪球",
            "snowball",
            "敲出",
            "knock-out",
            "knock out",
        ),
        ProductType.FCN: (
            "fcn",
            "fixed coupon note",
            "固定票息票据",
            "worst-of",
            "worst of",
        ),
        ProductType.EUROPEAN_OPTION: (
            "欧式",
            "香草期权",
            "european option",
            "european call",
            "european put",
            "call option",
            "put option",
        ),
    }
    UNSUPPORTED_KEYWORDS: dict[str, tuple[str, ...]] = {
        "DCN": ("dcn", "dual currency note", "双币票据"),
        "Phoenix": ("凤凰", "phoenix"),
        "Classic structure": ("经典结构", "classic structure"),
    }

    def classify(
        self,
        text: str,
        llm_client: ProductClassificationClient | None = None,
    ) -> ClassificationResult:
        normalized = text.casefold()
        supported_hits = {
            product: [term for term in terms if term in normalized]
            for product, terms in self.SUPPORTED_KEYWORDS.items()
        }
        matched_supported = {
            product: hits for product, hits in supported_hits.items() if hits
        }
        unsupported_hits = {
            label: [term for term in terms if term in normalized]
            for label, terms in self.UNSUPPORTED_KEYWORDS.items()
        }
        matched_unsupported = {
            label: hits for label, hits in unsupported_hits.items() if hits
        }

        if len(matched_supported) == 1 and not matched_unsupported:
            product, hits = next(iter(matched_supported.items()))
            return ClassificationResult(
                product_type=product,
                confidence=0.95,
                reason=f"Matched product keywords: {', '.join(hits)}",
            )

        if matched_unsupported and not matched_supported:
            labels = ", ".join(matched_unsupported)
            return ClassificationResult(
                product_type=ProductType.UNSUPPORTED,
                confidence=0.99,
                reason=f"Detected unsupported product: {labels}",
            )

        if llm_client is not None:
            product = llm_client.classify_product(text)
            return ClassificationResult(
                product_type=product,
                confidence=0.7,
                reason="Rule classification was ambiguous; product confirmed by LLM.",
            )

        if matched_supported or matched_unsupported:
            reason = "Conflicting product keywords require LLM confirmation."
        else:
            reason = "No supported product keywords were found."
        return ClassificationResult(
            product_type=ProductType.UNKNOWN,
            confidence=0.0,
            reason=reason,
        )
