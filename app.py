"""Streamlit UI for OTC quote structuring."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from otc_quote_agent.config import ConfigurationError, Settings
from otc_quote_agent.exporters import ExportBundle, quote_table_row
from otc_quote_agent.llm import LLMError
from otc_quote_agent.parsers import DocumentParseError
from otc_quote_agent.service import QuoteExtractionError, QuoteExtractionService


st.set_page_config(page_title="OTC Quote Structuring Agent", layout="wide")
st.title("OTC Derivatives Quote Structuring Agent")
st.caption("Deterministic workflow + LLM structured extraction")

try:
    preview_settings = Settings.from_env()
    st.info(
        f"Provider: {preview_settings.llm_provider} · "
        f"Model: {preview_settings.llm_model} · "
        f"Endpoint: {preview_settings.llm_base_url}"
    )
except ConfigurationError as exc:
    st.warning(f"LLM configuration is incomplete: {exc}")

input_mode = st.radio("Input mode", ("Paste text", "Upload file"), horizontal=True)
text = ""
uploaded = None
if input_mode == "Paste text":
    text = st.text_area("Quote text", height=220)
else:
    uploaded = st.file_uploader(
        "Quote document",
        type=["txt", "md", "docx", "xlsx", "pdf"],
    )

if st.button("Run Extraction", type="primary"):
    try:
        settings = Settings.from_env()
        service = QuoteExtractionService.from_settings(settings)
        if input_mode == "Paste text":
            result = service.run(text=text)
        elif uploaded is not None:
            result = service.run(filename=uploaded.name, content=uploaded.getvalue())
        else:
            st.error("Please upload a file.")
            st.stop()
    except (ConfigurationError, DocumentParseError, LLMError, QuoteExtractionError, ValueError) as exc:
        st.error(f"Extraction failed: {exc}")
    else:
        st.subheader("Classification")
        st.write(
            {
                "status": result.status.value,
                "product_type": result.product_type.value,
                "reason": result.classification_reason,
            }
        )
        if result.quote is not None:
            st.subheader("Normalized quote")
            st.dataframe(pd.DataFrame([quote_table_row(result)]), use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Missing fields", len(result.quote.missing_fields))
            with col2:
                st.metric("Validation errors", len(result.quote.validation_errors))
            with col3:
                st.metric("Warnings", len(result.quote.warnings))

            if result.quote.missing_fields:
                st.warning({"missing_fields": result.quote.missing_fields})
            if result.quote.validation_errors:
                st.error(
                    [issue.model_dump(mode="json") for issue in result.quote.validation_errors]
                )
            if result.quote.warnings:
                st.warning([issue.model_dump(mode="json") for issue in result.quote.warnings])
            if result.review_questions:
                st.subheader("Review questions")
                for question in result.review_questions:
                    st.write(f"- {question}")
            with st.expander("Source text"):
                st.text(result.quote.raw_text)
        else:
            st.warning(
                "This product is not supported. No supported schema was applied "
                "and no quote fields were generated."
            )
            st.write(result.source_summary)
            st.write(result.processing_metadata.get("extension_suggestion", ""))

        st.subheader("Canonical JSON")
        st.json(result.model_dump(mode="json"))
        artifacts = ExportBundle().render_all(result)
        download_columns = st.columns(3)
        for column, (filename, payload) in zip(download_columns, artifacts.items()):
            mime_type = {
                ".json": "application/json",
                ".csv": "text/csv",
                ".html": "text/html",
            }[f".{filename.rsplit('.', 1)[-1]}"]
            with column:
                st.download_button(
                    f"Download {filename}",
                    data=payload.encode("utf-8"),
                    file_name=filename,
                    mime=mime_type,
                )
