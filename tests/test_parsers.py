from io import BytesIO

import pytest
from docx import Document
from openpyxl import Workbook
from pypdf import PdfWriter

from otc_quote_agent.parsers import (
    DocumentParser,
    ScannedPdfError,
    UnsupportedDocumentError,
)
from otc_quote_agent.schemas import SourceType


@pytest.fixture
def parser() -> DocumentParser:
    return DocumentParser()


def test_parse_pasted_text(parser: DocumentParser) -> None:
    result = parser.parse_text("  Snowball inquiry  ")

    assert result.text == "Snowball inquiry"
    assert result.source_type is SourceType.PASTED_TEXT


@pytest.mark.parametrize("filename", ["quote.txt", "quote.md"])
def test_parse_plain_text(parser: DocumentParser, filename: str) -> None:
    result = parser.parse_bytes(filename, "中证1000雪球".encode())

    assert result.text == "中证1000雪球"


def test_parse_docx_paragraphs_and_tables(parser: DocumentParser) -> None:
    document = Document()
    document.add_paragraph("FCN quote")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Coupon"
    table.cell(0, 1).text = "12%"
    content = BytesIO()
    document.save(content)

    result = parser.parse_bytes("quote.docx", content.getvalue())

    assert "FCN quote" in result.text
    assert "Coupon | 12%" in result.text


def test_parse_xlsx_visible_cells(parser: DocumentParser) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Quote"
    sheet.append(["Product", "European Option"])
    content = BytesIO()
    workbook.save(content)

    result = parser.parse_bytes("quote.xlsx", content.getvalue())

    assert "[Sheet: Quote]" in result.text
    assert "Product | European Option" in result.text


def test_empty_text_pdf_is_reported_as_scanned(parser: DocumentParser) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    content = BytesIO()
    writer.write(content)

    with pytest.raises(ScannedPdfError, match="OCR is not supported"):
        parser.parse_bytes("scan.pdf", content.getvalue())


def test_unsupported_extension_is_rejected(parser: DocumentParser) -> None:
    with pytest.raises(UnsupportedDocumentError):
        parser.parse_bytes("quote.csv", b"product,snowball")
