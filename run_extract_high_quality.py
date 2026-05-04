#!/usr/bin/env python3
"""
High-quality PDF extraction runner with automatic dependency setup.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, shell=True):
    """Run a shell command with error handling."""
    try:
        result = subprocess.run(
            cmd, 
            shell=shell, 
            check=False, 
            text=True, 
            capture_output=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

def run_command_silent(cmd, shell=True):
    """Run a command silently and return True if successful."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=False,
            text=True,
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_and_install_deps():
    """Check for required system and Python dependencies."""
    print("🔧 Setting up high-quality PDF extraction...")
    print()
    
    # Check tesseract
    if not run_command_silent("which tesseract"):
        print("⚠️  Tesseract not found. Installing...")
        run_command("sudo apt update && sudo apt install -y tesseract-ocr", shell=True)
    else:
        print("✓ Tesseract found")
    
    # Check ghostscript
    if not run_command_silent("which gs"):
        print("⚠️  Ghostscript not found. Installing...")
        run_command("sudo apt install -y ghostscript", shell=True)
    else:
        print("✓ Ghostscript found")
    
    # Setup Python venv and dependencies  
    print("📦 Installing Python dependencies...")
    
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("  Creating virtual environment...")
        run_command("python3 -m venv .venv", shell=True)
    
    # Determine the correct python path in venv
    python_path = ".venv/bin/python3"
    pip_path = ".venv/bin/pip"
    
    print("  Installing packages...")
    run_command(f"{pip_path} install -q -r requirements.txt", shell=True)
    
    print("✅ Setup complete!")
    return python_path

def extract_pdfs(python_path):
    """Run high-quality PDF extraction."""
    print()
    print("🔍 Starting high-quality PDF extraction...")
    print("📊 Settings: force-ocr, 400 DPI, ultra-quality preprocessing")
    print()
    
    cmd = (
        f"{python_path} extract_pdf_text.py "
        "--input-dir imports "
        "--output-dir exports "
        "--force-ocr "
        "--dpi 400 "
        "--psm 3 "
        "--quality-mode ultra"
    )
    
    success = run_command(cmd, shell=True)
    
    if success:
        print()
        print("✨ Extraction complete!")
        print()
        print("📁 Check the 'exports' folder for extracted text:")
        exports_path = Path("exports")
        if exports_path.exists():
            txt_files = list(exports_path.glob("*.txt"))
            if txt_files:
                for txt_file in sorted(txt_files):
                    size = txt_file.stat().st_size
                    print(f"  ✓ {txt_file.name} ({size:,} bytes)")
            else:
                print("  (No text files generated yet)")
    else:
        print()
        print("❌ Extraction failed. Check error messages above.")
        return False
    
    return True

if __name__ == "__main__":
    try:
        python_env = check_and_install_deps()
        success = extract_pdfs(python_env)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Extraction cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

