#!/usr/bin/env python3
"""
Phase 3: Parse hybrid OCR recovery files.
Flattens hybrid directory and runs batch parser on all recovered dates.
"""
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Import the batch parser
sys.path.insert(0, str(Path(__file__).parent))
from batch_parse_multipage import process_all_files

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    hybrid_dir = base_dir / "ocr_results" / "hybrid_recovery"
    flat_dir = base_dir / "ocr_results" / "hybrid_recovery_flat"
    output_dir = base_dir / "parsed_output" / "polaris_recovery"

    print("=" * 80)
    print("PHASE 3: PARSE HYBRID RECOVERY FILES")
    print("=" * 80)
    print()

    # Create flat directory
    print("Creating flat OCR directory...")
    if flat_dir.exists():
        print(f"  Removing existing: {flat_dir}")
        shutil.rmtree(flat_dir)

    flat_dir.mkdir(parents=True)
    print(f"  Created: {flat_dir}")
    print()

    # Copy all OCR files to flat directory
    print("Flattening hybrid directory structure...")
    file_count = 0
    date_count = 0

    for date_dir in sorted(hybrid_dir.iterdir()):
        if date_dir.is_dir():
            date_count += 1
            for ocr_file in date_dir.glob("*.txt"):
                dest_file = flat_dir / ocr_file.name
                shutil.copy2(ocr_file, dest_file)
                file_count += 1

    print(f"  Copied {file_count} OCR files from {date_count} date directories")
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("RUNNING BATCH PARSER")
    print("=" * 80)
    print(f"OCR directory: {flat_dir}")
    print(f"Output directory: {output_dir}")
    print()
    print("This may take several minutes...")
    print()

    # Run batch parser on flat directory
    start_time = datetime.now()
    process_all_files(flat_dir, output_dir)
    elapsed_time = (datetime.now() - start_time).total_seconds()

    print()
    print("=" * 80)
    print("PHASE 3 COMPLETE")
    print("=" * 80)
    print()
    print(f"Total parsing time: {elapsed_time/60:.1f} minutes")
    print()
    print("Output files:")
    print(f"  Parsed CSV: {output_dir / 'ttj_shipments_multipage.csv'}")
    print(f"  Summary: {output_dir / 'processing_summary_multipage.json'}")
    print()
    print("Ready for Phase 4: Intelligent merge with deduplication")

if __name__ == '__main__':
    main()
