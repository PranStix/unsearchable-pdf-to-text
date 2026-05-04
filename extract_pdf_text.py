#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


LANG_ALIASES = {
    "en": "eng",
    "hi": "hin",
    "es": "spa",
    "fr": "fra",
    "de": "deu",
    "pt": "por",
    "it": "ita",
    "nl": "nld",
    "ru": "rus",
    "ja": "jpn",
    "ko": "kor",
    "zh": "chi_sim",
    "ar": "ara",
}


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


def get_tesseract_languages(tesseract_path: str) -> set[str]:
    result = run_command([tesseract_path, "--list-langs"])
    if result.returncode != 0:
        return set()
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return set(lines[1:]) if len(lines) > 1 else set()


def normalize_lang(lang: str) -> str:
    key = lang.strip().lower()
    return LANG_ALIASES.get(key, key)


def tesseract_install_hint() -> str:
    if sys.platform.startswith("linux"):
        return "Install it with: sudo apt update && sudo apt install -y tesseract-ocr"
    if sys.platform == "darwin":
        return "Install it with: brew install tesseract"
    if sys.platform.startswith("win"):
        return "Install Tesseract from UB Mannheim package and add the install folder to PATH"
    return "Install Tesseract OCR and ensure the 'tesseract' command is on PATH"


def preprocess_image_for_ocr(image_path: Path, output_path: Path, quality_mode: str = "balanced") -> Path:
    """
    Preprocess image for OCR with multiple quality modes.
    
    quality_mode:
      - "balanced": Default balanced preprocessing
      - "ultra": Ultra-high quality with advanced denoising
    """
    with Image.open(image_path) as image:
        gray = image.convert("L")
        auto = ImageOps.autocontrast(gray, cutoff=2)
        
        if quality_mode == "ultra":
            # Advanced preprocessing for ultra-high quality
            # Use multi-pass filtering for enhanced noise reduction
            denoised = auto.filter(ImageFilter.MedianFilter(size=3))
            denoised = denoised.filter(ImageFilter.SMOOTH_MORE)
            denoised = denoised.filter(ImageFilter.SMOOTH_MORE)
            # Adaptive threshold: use median-based approach
            bw = denoised.point(lambda px: 255 if px > 160 else 0, mode="1")
        else:
            # Standard balanced preprocessing
            denoised = auto.filter(ImageFilter.MedianFilter(size=3))
            bw = denoised.point(lambda px: 255 if px > 170 else 0, mode="1")
        
        bw.save(output_path, dpi=(300, 300))
    return output_path


def render_pdf_pages(pdf_path: Path, tmp: Path, dpi: int, gs_path: str | None) -> list[Path]:
    out_pattern = tmp / "page-%04d.png"

    if gs_path:
        gs_cmd = [
            gs_path,
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pnggray",
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
        return image_paths

    try:
        import pypdfium2 as pdfium  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Ghostscript executable 'gs' was not found in PATH and pypdfium2 is not available. "
            "Install Ghostscript system package or install Python package pypdfium2."
        ) from exc

    doc = pdfium.PdfDocument(str(pdf_path))
    scale = max(dpi, 72) / 72.0
    image_paths: list[Path] = []
    for page_idx in range(len(doc)):
        page = doc.get_page(page_idx)
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        out_path = tmp / f"page-{page_idx + 1:04d}.png"
        pil_image.save(out_path)
        image_paths.append(out_path)
        page.close()

    if not image_paths:
        raise RuntimeError("No page images were produced by pypdfium2")
    return image_paths


def clean_ocr_text(text: str) -> str:
    """Clean up OCR output by removing common OCR artifacts."""
    lines = []
    for line in text.splitlines():
        # Remove excessive spaces
        line = " ".join(line.split())
        # Fix common OCR errors (heuristic fixes)
        line = line.replace("l ", "I ").replace("O ", "0 ") if len(line.split()) <= 3 else line
        if line.strip():
            lines.append(line)
    return "\n".join(lines)


def extract_with_ocr(pdf_path: Path, lang: str, dpi: int, psm: int, oem: int, quality_mode: str = "balanced") -> str:
    """Render PDF pages to images with Ghostscript and OCR them with Tesseract."""
    gs_path = shutil.which("gs")
    tesseract_path = shutil.which("tesseract")
    if not tesseract_path:
        raise RuntimeError(
            "Tesseract executable 'tesseract' was not found in PATH. "
            f"{tesseract_install_hint()}"
        )

    resolved_lang = normalize_lang(lang)
    available_langs = get_tesseract_languages(tesseract_path)
    if available_langs and resolved_lang not in available_langs:
        preview = ", ".join(sorted(available_langs)[:12])
        raise RuntimeError(
            f"Tesseract language '{lang}' resolved to '{resolved_lang}', but it is not installed. "
            f"Installed examples: {preview}"
        )

    with tempfile.TemporaryDirectory(prefix="pdf_ocr_") as tmpdir:
        tmp = Path(tmpdir)
        image_paths = render_pdf_pages(pdf_path, tmp=tmp, dpi=dpi, gs_path=gs_path)

        page_texts: list[str] = []
        for idx, image_path in enumerate(image_paths, start=1):
            processed_path = tmp / f"ocr-{image_path.name}"
            preprocess_image_for_ocr(image_path, processed_path, quality_mode=quality_mode)
            tesseract_cmd = [
                tesseract_path,
                str(processed_path),
                "stdout",
                "-l",
                resolved_lang,
                "--oem",
                str(oem),
                "--psm",
                str(psm),
                "-c",
                "preserve_interword_spaces=1",
            ]
            ocr_result = run_command(tesseract_cmd)
            if ocr_result.returncode != 0:
                raise RuntimeError(
                    f"Tesseract failed on {image_path.name}:\n"
                    f"STDOUT:\n{ocr_result.stdout}\nSTDERR:\n{ocr_result.stderr}"
                )
            cleaned = clean_ocr_text(ocr_result.stdout.strip())
            page_texts.append(f"\n\n=== Page {idx} ===\n{cleaned}")

        return "".join(page_texts).strip()


def has_usable_text(text: str) -> bool:
    body_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("=== Page ")
    ]
    if not body_lines:
        return False

    compact = "".join(body_lines).replace(" ", "")
    if len(compact) < 150:
        return False

    unique_lines = {line.lower() for line in body_lines}
    unique_line_ratio = len(unique_lines) / max(len(body_lines), 1)
    if unique_line_ratio < 0.5:
        return False

    words = [word.strip(".,;:!?()[]{}\"'`).-_").lower() for line in body_lines for word in line.split()]
    words = [word for word in words if word]
    unique_word_count = len(set(words))
    if unique_word_count < 15:
        return False

    alnum_ratio = sum(ch.isalnum() for ch in compact) / max(len(compact), 1)
    bad_char_ratio = compact.count("�") / max(len(compact), 1)
    return alnum_ratio >= 0.55 and bad_char_ratio < 0.05


def process_pdf(
    pdf_path: Path,
    output_dir: Path,
    lang: str,
    dpi: int,
    psm: int,
    oem: int,
    force_ocr: bool,
    quality_mode: str = "balanced",
) -> tuple[bool, str, int]:
    output_path = output_dir / f"{pdf_path.stem}.txt"

    direct_text = extract_with_pypdf(pdf_path)
    used_method = "embedded-text"
    final_text = direct_text

    if force_ocr or not has_usable_text(direct_text):
        final_text = extract_with_ocr(pdf_path, lang=lang, dpi=dpi, psm=psm, oem=oem, quality_mode=quality_mode)
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
        default=400,
        help="Render DPI for OCR images (default: 400)",
    )
    parser.add_argument(
        "--psm",
        type=int,
        default=3,
        help="Tesseract page segmentation mode (default: 3)",
    )
    parser.add_argument(
        "--oem",
        type=int,
        default=1,
        help="Tesseract OCR engine mode (default: 1)",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Always run OCR even if embedded text is found",
    )
    parser.add_argument(
        "--quality-mode",
        default="balanced",
        choices=["balanced", "ultra"],
        help="OCR quality mode (default: balanced)",
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
                psm=args.psm,
                oem=args.oem,
                force_ocr=args.force_ocr,
                quality_mode=args.quality_mode,
            )
            success_count += 1
            print(f"OK: {pdf_path.name} -> {method}, {char_count} characters")
        except Exception as exc:
            print(f"FAIL: {pdf_path.name} -> {exc}", file=sys.stderr)

    print(f"Completed: {success_count}/{len(pdf_paths)} file(s) processed")
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
