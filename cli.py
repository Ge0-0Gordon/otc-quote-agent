"""Command-line entrypoint for real quote extraction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from otc_quote_agent.config import ConfigurationError, Settings
from otc_quote_agent.llm import LLMError
from otc_quote_agent.parsers import DocumentParseError
from otc_quote_agent.service import QuoteExtractionError, QuoteExtractionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Structure an OTC derivatives quote with a configured LLM.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Input document path.")
    parser.add_argument("--output", required=True, type=Path, help="Output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_env()
        service = QuoteExtractionService.from_settings(settings)
        result = service.run(input_path=args.input, output_dir=args.output)
    except (ConfigurationError, DocumentParseError, LLMError, QuoteExtractionError, ValueError) as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 1

    print(f"Status: {result.status.value}")
    print(f"Product: {result.product_type.value}")
    print(f"Reason: {result.classification_reason}")
    print(f"Artifacts: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
