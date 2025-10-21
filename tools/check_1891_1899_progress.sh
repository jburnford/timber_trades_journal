#!/bin/bash
# Monitor progress of TTJ 1891-1899 batch processing

echo "================================================================================"
echo "TTJ 1891-1899 BATCH PROCESSING PROGRESS"
echo "================================================================================"
echo ""

# Check if process is running
if pgrep -f "process_1891_1899_batch.sh" > /dev/null; then
    echo "Status: PROCESSING (script is running)"
else
    echo "Status: COMPLETED or NOT RUNNING"
fi
echo ""

# Count extracted PDFs
EXTRACTED_COUNT=$(find "/home/jic823/TTJ Forest of Numbers/extracted_1891_1899" -name "*.pdf" ! -name "._*" 2>/dev/null | wc -l)
echo "Extracted PDFs: $EXTRACTED_COUNT"

# Count OCR-ready images by year
echo ""
echo "OCR-ready images by year:"
for YEAR in 1891 1893 1895 1899; do
    YEAR_DIR="/home/jic823/TTJ Forest of Numbers/ocr_ready/$YEAR"
    if [ -d "$YEAR_DIR" ]; then
        IMG_COUNT=$(find "$YEAR_DIR" -name "*.png" 2>/dev/null | wc -l)
        echo "  $YEAR: $IMG_COUNT images"
    else
        echo "  $YEAR: 0 images (not started)"
    fi
done

# Total OCR-ready images
TOTAL_IMAGES=$(find "/home/jic823/TTJ Forest of Numbers/ocr_ready" -name "*.png" -path "*/189[1359]/*" -o -name "*.png" -path "*/1899/*" 2>/dev/null | wc -l)
echo ""
echo "Total OCR-ready images (1891-1899): $TOTAL_IMAGES"

# Show last 20 lines of log
echo ""
echo "================================================================================"
echo "RECENT LOG OUTPUT (last 20 lines):"
echo "================================================================================"
tail -20 /tmp/ttj_batch_processing.log 2>/dev/null || echo "No log file found"

echo ""
echo "================================================================================"
echo "To monitor live: tail -f /tmp/ttj_batch_processing.log"
echo "================================================================================"
