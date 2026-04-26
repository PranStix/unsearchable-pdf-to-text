#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_with_pypdf(pdf_path: Path) -> str:
    """Try extracting embedded text from PDF pages using pypdf if installed."""
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""

    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return ""

    pages: list[str] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""
        if text:
            pages.append(f"\n\n=== Page {idx} ===\n{text}")
    return "".join(pages).strip()


def run_command(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def extract_with_ocr(pdf_path: Path, lang: str, dpi: int) -> str:
    """Render PDF pages to images with Ghostscript and OCR them with Tesseract."""
    gs_path = shutil.which("gs")
    tesseract_path = shutil.which("tesseract")
    if not gs_path:
        raise RuntimeError("Ghostscript executable 'gs' was not found in PATH")
    if not tesseract_path:
        raise RuntimeError("Tesseract executable 'tesseract' was not found in PATH")

    with tempfile.TemporaryDirectory(prefix="pdf_ocr_") as tmpdir:
        tmp = Path(tmpdir)
        out_pattern = tmp / "page-%04d.png"

        gs_cmd = [
            gs_path,
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=png16m",
            f"-r{dpi}",
            "-o",
            str(out_pattern),
            str(pdf_path),
        ]
        gs_result = run_command(gs_cmd)
        if gs_result.returncode != 0:
            raise RuntimeError(
                "Ghostscript failed to render pages:\n"
                f"STDOUT:\n{gs_result.stdout}\nSTDERR:\n{gs_result.stderr}"
            )

        image_paths = sorted(tmp.glob("page-*.png"))
        if not image_paths:
            raise RuntimeError("No page images were produced by Ghostscript")

        page_texts: list[str] = []
        for idx, image_path in enumerate(image_paths, start=1):
            tesseract_cmd = [
                tesseract_path,
                str(image_path),
                "stdout",
                "-l",
                lang,
                "--psm",
                "6",
            ]
            ocr_result = run_command(tesseract_cmd)
            if ocr_result.returncode != 0:
                raise RuntimeError(
                    f"Tesseract failed on {image_path.name}:\n"
                    f"STDOUT:\n{ocr_result.stdout}\nSTDERR:\n{ocr_result.stderr}"
                )
            cleaned = ocr_result.stdout.strip()
            page_texts.append(f"\n\n=== Page {idx} ===\n{cleaned}")

        return "".join(page_texts).strip()


def has_usable_text(text: str) -> bool:
    return len("".join(text.split())) >= 80


def process_pdf(pdf_path: Path, output_dir: Path, lang: str, dpi: int, force_ocr: bool) -> tuple[bool, str, int]:
    output_path = output_dir / f"{pdf_path.stem}.txt"

    direct_text = extract_with_pypdf(pdf_path)
    used_method = "embedded-text"
    final_text = direct_text

    if force_ocr or not has_usable_text(direct_text):
        final_text = extract_with_ocr(pdf_path, lang=lang, dpi=dpi)
        used_method = "ocr"

    output_path.write_text(final_text, encoding="utf-8")
    return True, used_method, len(final_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract text from PDFs, with OCR fallback for scanned files.")
    parser.add_argument(
        "--input-dir",
        default=".",
        help="Folder containing PDF files (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        default="extracted_text",
        help="Folder where extracted .txt files are written (default: extracted_text)",
    )
    parser.add_argument(
        "--lang",
        default="eng",
        help="Tesseract OCR language code (default: eng)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Render DPI for OCR images (default: 300)",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Always run OCR even if embedded text is found",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory does not exist or is not a directory: {input_dir}", file=sys.stderr)
        return 2

    pdf_paths = sorted(input_dir.glob("*.pdf"))
    if not pdf_paths:
        print(f"No PDF files found in {input_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Found {len(pdf_paths)} PDF file(s) in {input_dir}")
    print(f"Writing extracted text to {output_dir}")

    success_count = 0
    for pdf_path in pdf_paths:
        try:
            _, method, char_count = process_pdf(
                pdf_path,
                output_dir=output_dir,
                lang=args.lang,
                dpi=args.dpi,
                force_ocr=args.force_ocr,
            )
            success_count += 1
            print(f"OK: {pdf_path.name} -> {method}, {char_count} characters")
        except Exception as exc:
            print(f"FAIL: {pdf_path.name} -> {exc}", file=sys.stderr)

    print(f"Completed: {success_count}/{len(pdf_paths)} file(s) processed")
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
