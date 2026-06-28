# OTC Quote Agent Optimization Implementation Plan

## Implementation status

- Phase 1: completed — offline Golden Dataset and JSON evaluation report.
- Phase 2: completed — field provenance, deterministic confidence, and evidence checks.
- Phase 3: completed — Streamlit human review, revalidation, and reviewed export.
- Phase 4: completed — backward-compatible `quote_candidates` for explicit alternatives.
- Phase 5: completed — input limits and untrusted-document prompt boundaries.
- Phase 6: completed — `.eml` headers and body extraction.
- Phase 7: completed — cases 1-6 manually verified from six inline images; runtime OCR deferred.

## Scope and constraints

- Preserve the existing deterministic workflow and shared `QuoteExtractionService`.
- Keep existing JSON consumers compatible for single-quote documents.
- Keep pytest offline with `FakeLLM`; do not require API keys or Ollama.
- Do not add a database, RAG, multi-agent orchestration, pricing, or OCR runtime.
- Do not force unsupported products into a supported product schema.

## Phase 1: Golden dataset and evaluation

Deliverables:

- Machine-readable expected fields for the existing three samples and official reference cases.
- An offline evaluator for classification, normalized field values, unsupported handling, and evidence coverage.
- Pytest coverage and a command that writes a concise JSON evaluation report.

Acceptance:

- Evaluation runs without network access.
- Incorrect fields are reported by path with expected and actual values.
- Unsupported cases are verified to contain no quote.

## Phase 2: Field provenance and confidence

Deliverables:

- Backward-compatible field metadata containing source text, extraction method, normalized status, and confidence.
- Deterministic confidence rules; no LLM self-reported score is treated as truth.
- Evidence consistency warnings when a populated field has no usable source evidence.

Acceptance:

- Existing quote fields remain unchanged.
- Canonically mapped or deterministically verified fields receive traceable metadata.
- Classification confidence is named separately from field confidence.

## Phase 3: Human review in Streamlit

Deliverables:

- Editable form for extracted business fields.
- Re-normalize and re-validate action using the same normalizer and validator.
- Export reviewed JSON, CSV, and HTML.
- Original and corrected values recorded in review metadata.

Acceptance:

- A user can correct a field, rerun validation, and download corrected artifacts.
- No provider call is required for review.

## Phase 4: Multiple quote alternatives

Deliverables:

- Optional `quote_candidates` on `ExtractionResult`.
- Case 13 can preserve two explicitly labelled alternatives.
- Single-quote output remains unchanged.

Acceptance:

- Existing samples still produce `quote`.
- Case 13 produces separate candidates without mixing option terms.

## Phase 5: Input safety and prompt boundaries

Deliverables:

- Limits for upload size, extracted text length, PDF pages, XLSX sheets/cells, and DOCX archive expansion.
- Explicit prompt boundary treating document content as untrusted data.
- Clear errors for rejected inputs.

Acceptance:

- Limit tests are offline and deterministic.
- Existing small samples continue to parse.
- Reports continue to HTML-escape document content.

## Phase 6: EML parsing

Deliverables:

- Simple `.eml` parser for headers and plain-text/HTML message bodies.
- Existing attachments remain outside this phase.

Acceptance:

- A representative email fixture parses without network access.
- History/signature removal is conservative and does not invent text.

## Phase 7: Official image cases and OCR decision

Deliverables:

- Inventory official cases 1-6 embedded as images.
- One-time extraction only when local OCR is reliable, followed by manual/source verification.
- Written decision on whether runtime OCR is justified.

Acceptance:

- Unverified OCR text is never added as authoritative reference data.
- Runtime scanned-PDF behavior remains an explicit unsupported error unless requirements change.

## Final verification

Run:

```powershell
python -m pytest
python scripts/evaluate_samples.py
python cli.py --input sample_data/snowball_inquiry_zh.txt --output outputs/sample_snowball
python cli.py --input sample_data/fcn_quote_zh.txt --output outputs/sample_fcn
python cli.py --input sample_data/european_option_email_en.txt --output outputs/sample_option
python cli.py --input sample_data/reference_case_09_limited_loss_snowball.txt --output outputs/reference_case_09
python cli.py --input sample_data/reference_case_11_dcn_unsupported.txt --output outputs/reference_case_11
python cli.py --input sample_data/reference_case_12_sharkfin_unsupported.txt --output outputs/reference_case_12
```
