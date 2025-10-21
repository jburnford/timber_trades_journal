#!/bin/bash
# Complete TTJ Data Processing Pipeline
# With improved St. John parsing and UTF-8 encoding fixes

set -e  # Exit on error

cd "/home/jic823/TTJ Forest of Numbers/tools"

echo "================================================================================"
echo "TTJ DATA PROCESSING PIPELINE - COMPLETE RUN"
echo "================================================================================"
echo ""
echo "Improvements in this run:"
echo "  ✓ St. John parsing fix (prevents truncation to 'St')"
echo "  ✓ UTF-8 encoding fix (GÃ¤vle → Gävle, etc.)"
echo ""
echo "================================================================================"
echo ""

# STEP 1: Parse OCR files
echo "STEP 1: Parsing OCR files..."
echo "  Input: ocr_results/gemini_full/*.txt (1,866 files)"
echo "  Output: parsed_output/ttj_shipments_multipage.csv"
python3 batch_parse_multipage.py
echo ""

# STEP 2: Deduplicate records
echo "STEP 2: Deduplicating records..."
echo "  Input: parsed_output/ttj_shipments_multipage.csv"
echo "  Output: final_output/deduped/ttj_shipments_deduped.csv"
python3 deduplicate_all_patterns.py
echo ""

# STEP 3: Apply port normalization
echo "STEP 3: Applying port normalization..."
echo "  Input: final_output/deduped/ttj_shipments_deduped.csv"
echo "  Output: final_output/authority_normalized/ttj_shipments_authority_normalized.csv"
python3 apply_normalization.py
echo ""

# STEP 4: Calculate coverage statistics
echo "STEP 4: Calculating coverage statistics..."
python3 << 'PYTHON'
import csv
import json

# Load canonical ports
with open('../reference_data/canonical_origin_ports.json') as f:
    canonical_origin = set(json.load(f))
with open('../reference_data/canonical_destination_ports.json') as f:
    canonical_dest = set(json.load(f))

# Load normalized data
with open('../final_output/authority_normalized/ttj_shipments_authority_normalized.csv', encoding='utf-8') as f:
    data = list(csv.DictReader(f))

total = len(data)
ships_with_origin = sum(1 for r in data if r['origin_port'])
ships_with_dest = sum(1 for r in data if r['destination_port'])
valid_origin = sum(1 for r in data if r['origin_port'] in canonical_origin)
valid_dest = sum(1 for r in data if r['destination_port'] in canonical_dest)

print(f"\n{'='*80}")
print("FINAL STATISTICS")
print('='*80)
print(f"Total ships: {total:,}")
print(f"Origin coverage: {valid_origin/ships_with_origin*100:.1f}% ({valid_origin:,}/{ships_with_origin:,})")
print(f"Destination coverage: {valid_dest/ships_with_dest*100:.1f}% ({valid_dest:,}/{ships_with_dest:,})")
print('='*80)
PYTHON

echo ""
echo "================================================================================"
echo "PIPELINE COMPLETE"
echo "================================================================================"
echo ""
echo "Output files:"
echo "  - final_output/authority_normalized/ttj_shipments_authority_normalized.csv"
echo "  - final_output/authority_normalized/ttj_cargo_details_authority_normalized.csv"
echo ""
echo "To identify unmapped ports, run:"
echo "  cd tools && python3 analyze_unmapped_ports.py"
echo ""
echo "================================================================================"
