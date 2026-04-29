# unsearchable-pdf-to-text

Extract text from PDF files with automatic OCR fallback for scanned or image-only PDFs.

## What this script does

- Tries direct text extraction first (via `pypdf`)
- Falls back to OCR when little/no embedded text is found
- Writes one `.txt` output file per `.pdf` file

## Requirements

### System dependencies

This script uses Ghostscript and Tesseract for OCR.

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y ghostscript tesseract-ocr
```

If Ghostscript is unavailable, the script can fall back to Python renderer `pypdfium2` (included in `requirements.txt`), but `tesseract-ocr` is still required.

Optional language packs (example for Hindi):

```bash
sudo apt install -y tesseract-ocr-hin
```

### Python dependencies

Install from `requirements.txt`.

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Basic usage:

```bash
python3 extract_pdf_text.py --input-dir imports --output-dir exports
```

Use a different OCR language:

```bash
python3 extract_pdf_text.py --input-dir imports --output-dir exports --lang hin
```

English tip: use `--lang eng` (not `en`).

Always force OCR (even when embedded text exists):

```bash
python3 extract_pdf_text.py --input-dir imports --output-dir exports --force-ocr
```

Higher-quality OCR (recommended when text is still poor):

```bash
python3 extract_pdf_text.py --input-dir imports --output-dir exports --force-ocr --lang eng --dpi 400 --psm 3
```

## CLI options

```text
--input-dir   Folder containing PDF files (default: current directory)
--output-dir  Folder where extracted .txt files are written (default: extracted_text)
--lang        Tesseract OCR language code (default: eng)
--dpi         Render DPI for OCR images (default: 400)
--psm         Tesseract page segmentation mode (default: 3)
--oem         Tesseract OCR engine mode (default: 1)
--force-ocr   Always run OCR even if embedded text is found
```

## Troubleshooting poor OCR

- If your PDF is scanned, use `--force-ocr`.
- Use a valid Tesseract language code (`eng`, `hin`, etc.), not two-letter locale codes.
- Make sure the language pack is installed (for example, `tesseract-ocr-hin`).
- Increase `--dpi` to `500` for very low-quality scans.
- Try `--psm 6` if the page is mostly a single text block.

## Troubleshooting missing Tesseract

If you see: `Tesseract executable 'tesseract' was not found in PATH`

Install Tesseract on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y tesseract-ocr
```

Verify it is available:

```bash
tesseract --version
```