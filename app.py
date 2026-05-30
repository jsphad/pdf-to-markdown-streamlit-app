"""Streamlit app for converting PDF files to Markdown — cloud-ready with OCR."""

from __future__ import annotations

import io
import re
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import streamlit as st

from converter.pdf_to_md import (
    convert_pdf_bytes_to_markdown,
    get_pdf_page_count,
    ocr_available,
)

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

# Maps the UI label shown in the sidebar to the internal mode string.
CONVERSION_MODES: dict[str, str] = {
    "Auto-detect (recommended)": "auto",
    "Text extraction — fast, digital PDFs only": "text",
    "OCR — Tesseract, for scanned PDFs": "ocr",
}


@dataclass(frozen=True)
class ConversionResult:
    """Result data for one converted PDF."""

    original_name: str
    output_name: str
    markdown_text: str
    page_count: int
    used_ocr: bool
    elapsed_seconds: float


def log_conversion(message: str) -> None:
    """Append a timestamped entry to the in-session conversion log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    if "conversion_log" not in st.session_state:
        st.session_state.conversion_log = []
    st.session_state.conversion_log.append(entry)


def is_safe_pdf_filename(file_name: str) -> bool:
    """Return True when a PDF file name contains only safe characters."""
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
    mode: str = "auto",
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
            pages = get_pdf_page_count(pdf_bytes)

            t0 = time.perf_counter()
            markdown_text, used_ocr = convert_pdf_bytes_to_markdown(pdf_bytes, mode=mode)
            elapsed = time.perf_counter() - t0

            output_name = Path(uploaded_file.name).stem + ".md"
            result = ConversionResult(
                original_name=uploaded_file.name,
                output_name=output_name,
                markdown_text=markdown_text,
                page_count=pages,
                used_ocr=used_ocr,
                elapsed_seconds=elapsed,
            )
            results.append(result)
            method = "OCR" if used_ocr else "text"
            log_conversion(
                f"SUCCESS [{method}, {pages}p, {elapsed:.1f}s] "
                f"- {uploaded_file.name} -> {output_name}"
            )
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
    defaults = {
        "conversion_results": [],
        "conversion_errors": [],
        "conversion_log": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar(tesseract_ready: bool) -> str:
    """Render sidebar controls and return the selected mode label."""
    st.sidebar.header("Conversion settings")

    if not tesseract_ready:
        st.sidebar.warning(
            "Tesseract is not installed on this machine. "
            "OCR mode is unavailable — only **Text extraction** will work. "
            "On Streamlit Community Cloud, Tesseract is installed automatically via `packages.txt`."
        )

    available_modes = list(CONVERSION_MODES.keys())
    if not tesseract_ready:
        # Hide OCR-only mode; auto-detect will still fall back gracefully.
        available_modes = [m for m in available_modes if "OCR" not in m]

    mode_label = st.sidebar.radio(
        "Conversion mode",
        options=available_modes,
        index=0,
        help=(
            "**Auto-detect**: uses pymupdf4llm for digital PDFs (preserves structure, "
            "tables, headings). Automatically switches to Tesseract OCR for scanned pages.\n\n"
            "**Text extraction**: fast path — skips OCR entirely. Use for digital PDFs.\n\n"
            "**OCR**: forces Tesseract on every page. Best for scanned or image-only PDFs."
        ),
    )

    st.sidebar.markdown("---")
    st.sidebar.header("About")
    st.sidebar.write(
        "PDFs are converted entirely in memory. "
        "Nothing is stored on the server after conversion."
    )
    st.sidebar.write(
        "Converted Markdown files are downloaded directly to your computer."
    )
    st.sidebar.write("No API key, database, or login required.")

    return mode_label


def render_results(results: list[ConversionResult]) -> None:
    """Render Markdown previews and download buttons for all results."""
    if not results:
        return

    total_pages = sum(r.page_count for r in results)
    total_time = sum(r.elapsed_seconds for r in results)
    st.success(
        f"Converted {len(results)} file(s) — "
        f"{total_pages} page(s) in {total_time:.1f} s."
    )

    for index, result in enumerate(results, start=1):
        method_tag = "OCR" if result.used_ocr else "text"
        expander_label = (
            f"{index}. {result.original_name}  →  {result.output_name} "
            f"[{result.page_count} page(s) · {method_tag} · {result.elapsed_seconds:.1f} s]"
        )
        with st.expander(expander_label, expanded=index == 1):
            if result.used_ocr:
                st.info(
                    "This file was converted using **Tesseract OCR**. "
                    "Structure (headings, tables) may differ from a digital PDF."
                )

            preview_text = result.markdown_text
            if len(preview_text) > MAX_PREVIEW_CHARS:
                preview_text = (
                    preview_text[:MAX_PREVIEW_CHARS]
                    + "\n\n<!-- Preview truncated — download for the full file. -->"
                )
                st.info(
                    "Preview is truncated for display speed. "
                    "The downloaded file contains the full Markdown."
                )

            st.markdown("#### Markdown preview")
            st.text_area(
                label=f"Preview for {result.output_name}",
                value=preview_text,
                height=400,
                label_visibility="collapsed",
            )
            st.download_button(
                label=f"⬇ Download {result.output_name}",
                data=result.markdown_text.encode("utf-8"),
                file_name=result.output_name,
                mime="text/markdown",
            )

    if len(results) > 1:
        st.download_button(
            label="⬇ Download all as ZIP",
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

    tesseract_ready = ocr_available()
    mode_label = render_sidebar(tesseract_ready)

    st.title("📄 PDF to Markdown Converter")
    st.write(
        "Upload one or more PDF files and convert them to Markdown. "
        "Digital PDFs are processed with **pymupdf4llm** (preserves headings, tables, and lists). "
        "Scanned or image-only PDFs are handled by **Tesseract OCR**. "
        "Nothing is stored on the server — files are downloaded directly to your computer."
    )

    uploaded_files = st.file_uploader(
        "Choose PDF file(s)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files to convert.",
    )

    if uploaded_files:
        total_mb = sum(getattr(f, "size", 0) for f in uploaded_files) / (1024 * 1024)
        st.caption(f"Selected {len(uploaded_files)} file(s) — {total_mb:.1f} MB total.")

    if st.button("Convert PDF(s) to Markdown", type="primary", disabled=not uploaded_files):
        mode = CONVERSION_MODES.get(mode_label, "auto")
        if mode == "ocr" and not tesseract_ready:
            st.error(
                "Tesseract is not installed on this machine. "
                "Install it from https://github.com/UB-Mannheim/tesseract/wiki "
                "and make sure `tesseract` is on your PATH, then restart the app."
            )
        else:
            with st.spinner("Converting… (OCR pages may take a few seconds each)"):
                results, errors = convert_uploaded_files(uploaded_files, mode=mode)
                st.session_state.conversion_results = results
                st.session_state.conversion_errors = errors

    if st.session_state.conversion_errors:
        st.error("Some files could not be converted.")
        for error in st.session_state.conversion_errors:
            st.warning(error)

    render_results(st.session_state.conversion_results)

    with st.expander("How it works"):
        st.markdown(
            "| Engine | Best for | Output quality |\n"
            "|--------|----------|----------------|\n"
            "| pymupdf4llm | Digital PDFs with embedded text | Excellent — preserves headings, tables, lists |\n"
            "| Tesseract OCR | Scanned or image-only PDFs | Good — plain text, organised by page |\n"
        )
        st.write(
            "**Auto-detect** checks the average number of embedded characters per page. "
            "If a document is below the threshold it is treated as scanned and OCR is applied."
        )
        st.write("No API key, database, login, or internet connection is needed during conversion.")


if __name__ == "__main__":
    main()
