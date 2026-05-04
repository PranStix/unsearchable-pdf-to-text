#!/bin/bash
set -e

echo "🔧 Setting up high-quality PDF extraction..."
echo ""

# Check for system dependencies
echo "📋 Checking system dependencies..."

if ! command -v tesseract &> /dev/null; then
    echo "⚠️  Tesseract not found. Installing..."
    sudo apt update
    sudo apt install -y tesseract-ocr
fi

if ! command -v gs &> /dev/null; then
    echo "⚠️  Ghostscript not found. Installing..."
    sudo apt install -y ghostscript
fi

# Check for Python dependencies
echo "📦 Installing Python dependencies..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔍 Starting high-quality PDF extraction..."
echo ""

# Run extraction with high-quality settings
# Using:
# --force-ocr: Always run OCR for best quality
# --dpi 400: High DPI rendering (standard high quality)
# --psm 3: Auto page segmentation
# --quality-mode ultra: Ultra-high quality preprocessing
python3 extract_pdf_text.py \
    --input-dir imports \
    --output-dir exports \
    --force-ocr \
    --dpi 400 \
    --psm 3 \
    --quality-mode ultra

echo ""
echo "✨ Extraction complete! Check the 'exports' folder for results."
