#!/bin/bash
# Process all PDF files in the TTJ collection
# Extracts pages, detects rotation, corrects alignment, and enhances for OCR

set -e  # Exit on error

BASE_DIR="/home/jic823/TTJ Forest of Numbers"
OUTPUT_DIR="$BASE_DIR/ocr_ready"

echo "=================================================================="
echo "TTJ OCR-READY IMAGE GENERATION PIPELINE"
echo "=================================================================="
echo ""
echo "This script will process all PDF files in the collection:"
echo "  - Extract pages from PDFs (300 DPI)"
echo "  - Detect and correct rotation"
echo "  - Apply OCR enhancements (denoising, contrast, sharpening)"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Processing years: 1875, 1877, 1879, 1881, 1885, 1887"
echo ""
echo "=================================================================="
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Count total PDFs
TOTAL_PDFS=$(find "$BASE_DIR/1875" "$BASE_DIR/1877" "$BASE_DIR/1879" "$BASE_DIR/1881" "$BASE_DIR/1885" "$BASE_DIR/1887" -name "*.pdf" 2>/dev/null | wc -l)
echo "Found $TOTAL_PDFS PDF files to process"
echo ""

# Process each year directory
for YEAR in 1875 1877 1879 1881 1885 1887; do
    YEAR_DIR="$BASE_DIR/$YEAR"
    YEAR_OUTPUT="$OUTPUT_DIR/$YEAR"

    if [ ! -d "$YEAR_DIR" ]; then
        echo "Skipping $YEAR (directory not found)"
        continue
    fi

    PDF_COUNT=$(find "$YEAR_DIR" -name "*.pdf" 2>/dev/null | wc -l)

    if [ $PDF_COUNT -eq 0 ]; then
        echo "Skipping $YEAR (no PDF files found)"
        continue
    fi

    echo "=================================================================="
    echo "Processing Year: $YEAR ($PDF_COUNT PDFs)"
    echo "=================================================================="

    # Create year output directory
    mkdir -p "$YEAR_OUTPUT"

    # Process all PDFs in this year directory (recursive)
    python3 "$BASE_DIR/tools/process_pdf_for_ocr.py" \
        "$YEAR_DIR" \
        -o "$YEAR_OUTPUT" \
        --dpi 300 \
        --method combined \
        --recursive

    echo ""
done

echo ""
echo "=================================================================="
echo "PROCESSING COMPLETE"
echo "=================================================================="
echo ""
echo "Output location: $OUTPUT_DIR"
echo ""
echo "Summary by year:"
for YEAR in 1875 1877 1879 1881 1885 1887; do
    YEAR_OUTPUT="$OUTPUT_DIR/$YEAR"
    if [ -d "$YEAR_OUTPUT" ]; then
        IMG_COUNT=$(find "$YEAR_OUTPUT" -name "*.png" 2>/dev/null | wc -l)
        echo "  $YEAR: $IMG_COUNT images"
    fi
done

TOTAL_IMAGES=$(find "$OUTPUT_DIR" -name "*.png" 2>/dev/null | wc -l)
echo ""
echo "Total OCR-ready images: $TOTAL_IMAGES"
echo ""
echo "=================================================================="
echo "Next steps:"
echo "  1. Review sample images for quality"
echo "  2. Run OCR with Gemini or other OCR engine"
echo "  3. Extract data tables and text"
echo "=================================================================="
