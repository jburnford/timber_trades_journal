#!/bin/bash
# Run OCR test on British Library newspaper collection

# Convert Windows paths to WSL paths
PDF_DIR="/home/jic823/ocr_bldata/25439023/BLN600/pdf"
GT_DIR="/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth"
OUTPUT_DIR="./bl_ocr_test_results"

echo "========================================================================"
echo "British Library Newspaper OCR Test"
echo "========================================================================"
echo ""
echo "PDF Directory: $PDF_DIR"
echo "Ground Truth Directory: $GT_DIR"
echo "Output Directory: $OUTPUT_DIR"
echo ""

# Check dependencies
echo "Checking dependencies..."
python3 -c "import google.generativeai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Missing google-generativeai, installing..."
    python3 -m pip install --break-system-packages google-generativeai
fi

python3 -c "import fitz" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Missing PyMuPDF, installing..."
    python3 -m pip install --break-system-packages pymupdf
fi

echo ""
echo "========================================================================"
echo "Starting test (this will take several minutes)..."
echo "========================================================================"
echo ""

# Run test - start with 10 samples to test the pipeline
python3 tools/test_bl_newspaper_ocr.py \
    --pdf-dir "$PDF_DIR" \
    --gt-dir "$GT_DIR" \
    --output "$OUTPUT_DIR" \
    --sample-size 10 \
    --delay 2.0 \
    --debug

echo ""
echo "========================================================================"
echo "Test complete! Check results in: $OUTPUT_DIR"
echo "========================================================================"
