# PDF to Markdown Converter

A Streamlit web app that converts PDF files into Markdown.

- **Digital PDFs** → converted with [`pymupdf4llm`](https://pypi.org/project/pymupdf4llm/), preserving headings, tables, and lists.
- **Scanned / image-only PDFs** → rendered at 300 DPI and processed with **Tesseract OCR**.
- PDFs are processed entirely in server memory. Nothing is stored on the server after conversion.
- Converted Markdown files are downloaded directly to your computer via the browser.

## Features

- Upload one or more PDF files
- Three conversion modes: **Auto-detect**, **Text extraction**, **OCR**
- Auto-detect chooses the right engine per document automatically
- Preview generated Markdown in the browser before downloading
- Download individual `.md` files or all files as a ZIP
- Per-file stats: page count, engine used (text / OCR), elapsed time
- No API key, database, login, or cloud storage configuration required

## Project structure

```text
pdf_to_markdown_streamlit_app/
├── app.py
├── requirements.txt   # Python dependencies
├── packages.txt       # System dependencies (apt) for Streamlit Cloud
├── README.md
├── .streamlit/
│   └── config.toml    # maxUploadSize = 400 MB
└── converter/
    ├── __init__.py
    └── pdf_to_md.py   # conversion logic — text extraction + OCR
```

## Deploy to Streamlit Community Cloud

1. Push this repository to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, select this repository, branch `main`, main file `app.py`.
4. Click **Deploy**.

Streamlit Community Cloud automatically installs `requirements.txt` (Python packages) and `packages.txt` (system packages — Tesseract OCR).

## Run locally

```bash
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

### OCR on Windows (local)

OCR mode requires the Tesseract binary.

1. Download and install Tesseract from the [UB Mannheim builds](https://github.com/UB-Mannheim/tesseract/wiki).
2. Add the Tesseract folder (e.g. `C:\Program Files\Tesseract-OCR`) to your system PATH.
3. Restart the Streamlit app.

On macOS: `brew install tesseract`  
On Ubuntu/Debian: `sudo apt install tesseract-ocr tesseract-ocr-eng`

If Tesseract is not installed, the app still works for digital PDFs — OCR mode is disabled automatically with a sidebar notice.

## Notes and limitations

- OCR output is plain text grouped by page. It does not reconstruct complex tables or multi-column layouts as reliably as text extraction.
- Only English language data (`tesseract-ocr-eng`) is included. For other languages, add the relevant `tesseract-ocr-<lang>` package to `packages.txt`.
- Scanned PDFs with very low image quality may produce inaccurate OCR output.
- Future conversion engines can be added inside `converter/pdf_to_md.py` without changing the Streamlit UI.
