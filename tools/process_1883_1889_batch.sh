#!/bin/bash
# Process TTJ 1883-1889 batch for OCR
# This script extracts PDFs from zip files and processes them to ocr_ready format

set -e  # Exit on error

BASE_DIR="/home/jic823/TTJ Forest of Numbers"
BATCH_DIR="$BASE_DIR/TTJ 1883-1889"
EXTRACT_DIR="$BASE_DIR/extracted_1883_1889"
OUTPUT_DIR="$BASE_DIR/ocr_ready"

echo "=================================================================="
echo "TTJ 1883-1889 (+ 1897) BATCH PROCESSING PIPELINE"
echo "=================================================================="
echo ""
echo "This script will:"
echo "  1. Extract PDFs from zip files"
echo "  2. Process pages (300 DPI)"
echo "  3. Detect and correct rotation"
echo "  4. Apply OCR enhancements"
echo ""
echo "Input directory: $BATCH_DIR"
echo "Extract directory: $EXTRACT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Years: 1883, 1889, 1897"
echo ""
echo "=================================================================="
echo ""

# Step 1: Extract zip files
echo "Step 1: Extracting ZIP files..."
echo ""

mkdir -p "$EXTRACT_DIR"

cd "$BATCH_DIR"
for zipfile in *.zip; do
    # Skip Zone.Identifier files
    if [[ "$zipfile" == *":Zone.Identifier" ]]; then
        continue
    fi

    # Extract year from filename
    if [[ "$zipfile" =~ ([0-9]{4}) ]]; then
        YEAR="${BASH_REMATCH[1]}"
        YEAR_DIR="$EXTRACT_DIR/$YEAR"

        echo "Extracting: $zipfile -> $YEAR"
        mkdir -p "$YEAR_DIR"

        # Extract to year directory
        unzip -q -o "$zipfile" -d "$YEAR_DIR"

        # Count PDFs extracted
        PDF_COUNT=$(find "$YEAR_DIR" -name "*.pdf" ! -name "._*" 2>/dev/null | wc -l)
        echo "  Extracted $PDF_COUNT PDFs"
        echo ""
    fi
done

echo ""
echo "=================================================================="
echo "Step 2: Processing PDFs to OCR-ready format..."
echo "=================================================================="
echo ""

# Step 2: Process each year directory
for YEAR in 1883 1889 1897; do
    YEAR_DIR="$EXTRACT_DIR/$YEAR"
    YEAR_OUTPUT="$OUTPUT_DIR/$YEAR"

    if [ ! -d "$YEAR_DIR" ]; then
        echo "Skipping $YEAR (directory not found)"
        continue
    fi

    PDF_COUNT=$(find "$YEAR_DIR" -name "*.pdf" ! -name "._*" 2>/dev/null | wc -l)

    if [ $PDF_COUNT -eq 0 ]; then
        echo "Skipping $YEAR (no PDF files found)"
        continue
    fi

    echo "=================================================================="
    echo "Processing Year: $YEAR ($PDF_COUNT PDFs)"
    echo "=================================================================="

    # Create year output directory
    mkdir -p "$YEAR_OUTPUT"

    # Remove macOS metadata files
    find "$YEAR_DIR" -name "._*" -delete
    find "$YEAR_DIR" -name ".DS_Store" -delete
    find "$YEAR_DIR" -type d -name "__MACOSX" -exec rm -rf {} + 2>/dev/null || true

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
for YEAR in 1883 1889 1897; do
    YEAR_OUTPUT="$OUTPUT_DIR/$YEAR"
    if [ -d "$YEAR_OUTPUT" ]; then
        IMG_COUNT=$(find "$YEAR_OUTPUT" -name "*.png" 2>/dev/null | wc -l)
        echo "  $YEAR: $IMG_COUNT images"
    fi
done

TOTAL_IMAGES=$(find "$OUTPUT_DIR" -name "*.png" \( -path "*/1883/*" -o -path "*/1889/*" -o -path "*/1897/*" \) 2>/dev/null | wc -l)
echo ""
echo "Total OCR-ready images (1883-1889 batch): $TOTAL_IMAGES"
echo ""
echo "=================================================================="
echo "Next steps:"
echo "  1. Review sample images for quality"
echo "  2. WAIT FOR APPROVAL: Gemini API budget"
echo "  3. Run OCR with Gemini: gemini_ocr_processor.py"
echo "  4. Parse and extract data tables"
echo "=================================================================="
