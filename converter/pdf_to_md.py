"""PDF-to-Markdown conversion with optional Tesseract OCR support."""

from pathlib import Path

import pymupdf
import pymupdf4llm

# Pillow and pytesseract are optional — OCR mode requires both plus the
# Tesseract binary. On Streamlit Cloud these are provided via packages.txt.
# On Windows the binary must be installed separately and on PATH.
try:
    import pytesseract
    from PIL import Image
    _OCR_LIBS_AVAILABLE = True
except ImportError:
    _OCR_LIBS_AVAILABLE = False

_OCR_DPI = 300
_MIN_CHARS_PER_PAGE = 50  # average chars/page below this → treat as scanned


def _has_embedded_text(doc: pymupdf.Document) -> bool:
    """Return True when the document has enough embedded text to skip OCR."""
    total = sum(len(page.get_text().strip()) for page in doc)
    return (total / max(len(doc), 1)) >= _MIN_CHARS_PER_PAGE


def _ocr_doc_to_markdown(doc: pymupdf.Document) -> str:
    """Render every page at 300 DPI and OCR it with Tesseract."""
    if not _OCR_LIBS_AVAILABLE:
        raise ImportError(
            "pytesseract or Pillow is not installed. "
            "Run: pip install pytesseract Pillow"
        )

    scale = _OCR_DPI / 72
    mat = pymupdf.Matrix(scale, scale)
    parts: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # --psm 3: fully automatic page segmentation (no OSD).
        # --oem 3: use the best available Tesseract engine.
        text = pytesseract.image_to_string(img, config="--psm 3 --oem 3").strip()
        if text:
            parts.append(f"## Page {page_num}\n\n{text}")

    return "\n\n---\n\n".join(parts) if parts else ""


def _postprocess_markdown(text: str) -> str:
    """Remove excess blank lines and trailing whitespace from extracted text."""
    import re
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def convert_pdf_bytes_to_markdown(
    pdf_bytes: bytes,
    mode: str = "auto",
) -> tuple[str, bool]:
    """Convert PDF bytes to Markdown text.

    Parameters
    ----------
    pdf_bytes:
        Raw PDF file content.
    mode:
        ``"auto"``  — pymupdf4llm for digital PDFs; Tesseract OCR for scanned ones.
        ``"text"``  — always use pymupdf4llm (fast, no OCR).
        ``"ocr"``   — always use Tesseract OCR (slower; handles scanned pages).

    Returns
    -------
    (markdown_text, used_ocr)
    """
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        use_ocr = mode == "ocr" or (mode == "auto" and not _has_embedded_text(doc))
        if use_ocr:
            md = _ocr_doc_to_markdown(doc)
        else:
            md = pymupdf4llm.to_markdown(doc)
    finally:
        doc.close()

    return _postprocess_markdown(md), use_ocr


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in a PDF."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count


def ocr_available() -> bool:
    """Return True when both pytesseract + Pillow are importable and the
    Tesseract binary is reachable on PATH."""
    if not _OCR_LIBS_AVAILABLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def convert_pdf_to_markdown(pdf_path: str) -> str:
    """Convert a local PDF file to Markdown (text extraction only)."""
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
