#!/bin/bash
# Test the PDF processing pipeline on a sample PDF

cd "/home/jic823/TTJ Forest of Numbers"

echo "Testing PDF processing pipeline on sample document..."
echo "=================================================================="

python3 tools/process_pdf_for_ocr.py \
    "1875/2. Timber Trades Journal Vol. 3 - 1875/5. p.75-77 - June 26 1875 - Import of Timber, &c. Timber Trades Journal Vol. 3 1875.pdf" \
    -o "work/pdf_pipeline_test" \
    --dpi 300 \
    --method combined \
    --debug

echo ""
echo "=================================================================="
echo "Test complete! Check work/pdf_pipeline_test/ for results"
echo "=================================================================="
