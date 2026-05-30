# PDF to Markdown Converter

A Streamlit web app that converts PDF files into Markdown using [`pymupdf4llm`](https://pypi.org/project/pymupdf4llm/).

PDFs are processed entirely in server memory. No file is stored on the server after conversion. Converted Markdown files are downloaded directly to your computer via the browser.

## Features

- Upload one or more PDF files
- Convert PDFs to Markdown with `pymupdf4llm` (no OCR, no API key required)
- Preview the generated Markdown in the browser
- Download each converted `.md` file to your computer
- Download all files as a ZIP when multiple PDFs are converted
- No API key, database, login, or cloud storage configuration required

## Project structure

```text
pdf_to_markdown_streamlit_app/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
└── converter/
    ├── __init__.py
    └── pdf_to_md.py
```

## Deploy to Streamlit Community Cloud

1. Push this repository to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, select this repository, branch `main`, and set the main file path to `app.py`.
4. Click **Deploy**.

Streamlit Community Cloud installs `requirements.txt` automatically.

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

## Notes and limitations

- This app does not include OCR. Scanned PDFs without embedded text may produce limited Markdown output.
- Future conversion engines (OCR, Docling) can be added inside `converter/pdf_to_md.py` without changing the Streamlit UI.
