"""PDF-to-Markdown conversion utilities.

The conversion layer is intentionally small so alternative engines, such as OCR
or Docling, can be added later without changing the Streamlit interface.
"""

from pathlib import Path

import pymupdf
import pymupdf4llm


def convert_pdf_bytes_to_markdown(pdf_bytes: bytes) -> str:
    """Convert PDF content from bytes to Markdown without writing to disk."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        markdown_text = pymupdf4llm.to_markdown(doc)
    finally:
        doc.close()
    if not isinstance(markdown_text, str):
        raise TypeError("pymupdf4llm did not return Markdown text.")
    return markdown_text


def convert_pdf_to_markdown(pdf_path: str) -> str:
    """Convert a PDF file at a local path to Markdown text."""
    source_path = Path(pdf_path)

    if not source_path.exists():
        raise FileNotFoundError(f"PDF file not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"PDF path is not a file: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise ValueError("Only .pdf files can be converted.")

    markdown_text = pymupdf4llm.to_markdown(str(source_path))

    if not isinstance(markdown_text, str):
        raise TypeError("pymupdf4llm did not return Markdown text.")

    return markdown_text
