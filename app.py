"""Streamlit app for converting PDF files to Markdown — cloud-ready."""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import streamlit as st

from converter.pdf_to_md import convert_pdf_bytes_to_markdown

MAX_PREVIEW_CHARS = 20_000
SAFE_FILENAME_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9 ._()\-]*\.pdf$", re.IGNORECASE
)
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


@dataclass(frozen=True)
class ConversionResult:
    """Result data for one converted PDF."""

    original_name: str
    output_name: str
    markdown_text: str


def log_conversion(message: str) -> None:
    """Append a timestamped entry to the in-session conversion log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    if "conversion_log" not in st.session_state:
        st.session_state.conversion_log = []
    st.session_state.conversion_log.append(entry)


def is_safe_pdf_filename(file_name: str) -> bool:
    """Return True when a PDF file name is safe to use."""
    name = Path(file_name).name
    stem = Path(name).stem.upper()

    if name != file_name:
        return False
    if not SAFE_FILENAME_PATTERN.fullmatch(name):
        return False
    if name.endswith((" ", ".")):
        return False
    if stem in WINDOWS_RESERVED_NAMES:
        return False
    return True


def validate_uploaded_pdf(uploaded_file) -> list[str]:
    """Validate an uploaded PDF before converting it."""
    errors: list[str] = []

    if uploaded_file is None:
        return ["No file was uploaded."]

    file_name = getattr(uploaded_file, "name", "")
    file_size = getattr(uploaded_file, "size", 0)

    if not file_name:
        errors.append("Uploaded file is missing a file name.")
    elif Path(file_name).suffix.lower() != ".pdf":
        errors.append(f"{file_name}: file extension must be .pdf.")
    elif not is_safe_pdf_filename(file_name):
        errors.append(
            f"{file_name}: file name contains unsupported characters. "
            "Use letters, numbers, spaces, dots, underscores, hyphens, or parentheses."
        )

    if file_size == 0:
        errors.append(f"{file_name or 'Uploaded file'}: file size is zero bytes.")

    return errors


def convert_uploaded_files(
    uploaded_files: Iterable,
) -> tuple[list[ConversionResult], list[str]]:
    """Convert uploaded PDFs in memory and collect user-friendly error messages."""
    results: list[ConversionResult] = []
    errors: list[str] = []

    for uploaded_file in uploaded_files:
        validation_errors = validate_uploaded_pdf(uploaded_file)
        if validation_errors:
            errors.extend(validation_errors)
            for ve in validation_errors:
                log_conversion(f"VALIDATION ERROR - {ve}")
            continue

        try:
            pdf_bytes = bytes(uploaded_file.getbuffer())
            markdown_text = convert_pdf_bytes_to_markdown(pdf_bytes)
            output_name = Path(uploaded_file.name).stem + ".md"

            result = ConversionResult(
                original_name=uploaded_file.name,
                output_name=output_name,
                markdown_text=markdown_text,
            )
            results.append(result)
            log_conversion(f"SUCCESS - {uploaded_file.name} -> {output_name}")
        except Exception as exc:  # noqa: BLE001
            message = f"{uploaded_file.name}: conversion failed ({exc})"
            errors.append(message)
            log_conversion(f"ERROR - {message}")

    return results, errors


def build_zip(results: list[ConversionResult]) -> bytes:
    """Create an in-memory ZIP archive containing all converted Markdown files."""
    zip_buffer = io.BytesIO()
    used_names: set[str] = set()

    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for result in results:
            archive_name = result.output_name
            if archive_name in used_names:
                stem = Path(result.output_name).stem
                archive_name = f"{stem}_{len(used_names) + 1}.md"
            used_names.add(archive_name)
            archive.writestr(archive_name, result.markdown_text)

    return zip_buffer.getvalue()


def initialize_session_state() -> None:
    """Initialize Streamlit session state used by the app."""
    if "conversion_results" not in st.session_state:
        st.session_state.conversion_results = []
    if "conversion_errors" not in st.session_state:
        st.session_state.conversion_errors = []
    if "conversion_log" not in st.session_state:
        st.session_state.conversion_log = []


def render_sidebar() -> None:
    """Render usage notes in the sidebar."""
    st.sidebar.header("How it works")
    st.sidebar.write(
        "PDFs are converted entirely in memory. "
        "No file is stored on the server after conversion."
    )
    st.sidebar.write(
        "Converted Markdown files are downloaded directly to your computer "
        "via the browser download button."
    )
    st.sidebar.write("No API key, database, or login is required.")


def render_results(results: list[ConversionResult]) -> None:
    """Render Markdown previews and download buttons."""
    if not results:
        return

    st.success(f"Converted {len(results)} PDF file(s) successfully.")

    for index, result in enumerate(results, start=1):
        with st.expander(
            f"{index}. {result.original_name} → {result.output_name}", expanded=index == 1
        ):
            preview_text = result.markdown_text
            if len(preview_text) > MAX_PREVIEW_CHARS:
                preview_text = (
                    preview_text[:MAX_PREVIEW_CHARS]
                    + "\n\n<!-- Preview truncated. Download the file for the full output. -->"
                )
                st.info(
                    "Preview is truncated for display speed. "
                    "The download contains the full Markdown file."
                )

            st.markdown("#### Markdown preview")
            st.text_area(
                label=f"Preview for {result.output_name}",
                value=preview_text,
                height=360,
                label_visibility="collapsed",
            )
            st.download_button(
                label=f"Download {result.output_name}",
                data=result.markdown_text.encode("utf-8"),
                file_name=result.output_name,
                mime="text/markdown",
            )

    if len(results) > 1:
        st.download_button(
            label="Download all Markdown files as ZIP",
            data=build_zip(results),
            file_name="converted_markdown_files.zip",
            mime="application/zip",
        )


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(
        page_title="PDF to Markdown Converter", page_icon="📄", layout="wide"
    )
    initialize_session_state()
    render_sidebar()

    st.title("📄 PDF to Markdown Converter")
    st.write(
        "Upload one or more PDF files and convert them into Markdown using `pymupdf4llm`. "
        "PDFs are processed in memory — nothing is stored on the server. "
        "Converted files are downloaded directly to your computer."
    )

    uploaded_files = st.file_uploader(
        "Choose PDF file(s)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files to convert.",
    )

    if uploaded_files:
        st.caption(f"Selected {len(uploaded_files)} file(s).")

    if st.button("Convert PDF(s) to Markdown", type="primary", disabled=not uploaded_files):
        with st.spinner("Converting PDF file(s)..."):
            results, errors = convert_uploaded_files(uploaded_files)
            st.session_state.conversion_results = results
            st.session_state.conversion_errors = errors

    if st.session_state.conversion_errors:
        st.error("Some files could not be converted.")
        for error in st.session_state.conversion_errors:
            st.warning(error)

    render_results(st.session_state.conversion_results)

    with st.expander("About this app"):
        st.write(
            "PDFs are converted to Markdown entirely in server memory using `pymupdf4llm`. "
            "No PDF content is stored on the server. "
            "Converted Markdown files are downloaded to your computer via the browser."
        )
        st.write(
            "This app does not include OCR. "
            "Scanned PDFs without embedded text may produce limited output."
        )


if __name__ == "__main__":
    main()
