#!/usr/bin/env python3
"""
High-quality PDF extraction runner with automatic dependency setup.
"""
import subprocess
import sys
from pathlib import Path
import onein

def run_command(cmd, description=""):
    """Run a shell command with error handling."""
    if description:
        print(f"\n{description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

def check_and_install_deps():
    """Check for required system and Python dependencies."""
    print("🔧 Setting up high-quality PDF extraction...")
    print()
    
    # Check tesseract
    if subprocess.run("which tesseract", shell=True, capture_output=True).returncode != 0:
        print("⚠️  Tesseract not found. Installing...")
        run_command("sudo apt update && sudo apt install -y tesseract-ocr", "")
    
    # Check ghostscript
    if subprocess.run("which gs", shell=True, capture_output=True).returncode != 0:
        print("⚠️  Ghostscript not found. Installing...")
        run_command("sudo apt install -y ghostscript", "")
    
    # Setup Python venv and dependencies
    print("📦 Installing Python dependencies...")
    venv_path = Path(".venv")
    if not venv_path.exists():
        run_command("python3 -m venv .venv", "")
    
    # Install requirements - activate venv and pip
    run_command(". .venv/bin/activate && pip install -q -r requirements.txt", "")
    
    print("✅ Setup complete!")

def extract_pdfs():
    """Run high-quality PDF extraction."""
    print()
    print("🔍 Starting high-quality PDF extraction...")
    print("📊 Settings: force-ocr, 400 DPI, ultra-quality preprocessing")
    print()
    
    cmd = (
        ". .venv/bin/activate && python3 extract_pdf_text.py "
        "--input-dir imports "
        "--output-dir exports "
        "--force-ocr "
        "--dpi 400 "
        "--psm 3 "
        "--quality-mode ultra"
    )
    
    run_command(cmd, "")
    
    print()
    print("✨ Extraction complete! Check the 'exports' folder for results.")

if __name__ == "__main__":
    check_and_install_deps()
    extract_pdfs()
