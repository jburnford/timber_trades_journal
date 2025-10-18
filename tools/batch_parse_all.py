#!/usr/bin/env python3
"""
Batch process all TTJ OCR files and generate CSV/JSON database.
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List
from ttj_parser_v3 import TTJContextParser, ShipRecord, extract_publication_date_from_filename


def process_all_files(ocr_dir: Path, output_dir: Path):
    """
    Process all OCR text files and generate outputs.

    Args:
        ocr_dir: Directory containing OCR .txt files
        output_dir: Directory for output files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all .txt files
    txt_files = sorted(ocr_dir.glob("*.txt"))

    print(f"Found {len(txt_files)} OCR files to process")
    print("=" * 80)

    parser = TTJContextParser()
    all_records = []
    stats = {
        'total_files': len(txt_files),
        'processed': 0,
        'failed': 0,
        'total_records': 0,
        'records_with_port': 0,
        'records_with_date': 0,
    }

    for i, txt_file in enumerate(txt_files, 1):
        try:
            print(f"[{i}/{len(txt_files)}] Processing {txt_file.name[:60]}...")

            # Parse file
            records = parser.parse_file(txt_file)

            # Add source filename to each record
            for record in records:
                all_records.append({
                    'source_file': txt_file.name,
                    'line_number': record.line_number,
                    'ship_name': record.ship_name,
                    'origin_port': record.origin_port,
                    'destination_port': record.destination_port,
                    'cargo': record.cargo,
                    'merchant': record.merchant,
                    'arrival_day': record.day,
                    'arrival_month': record.month,
                    'arrival_year': record.year,
                    'publication_day': record.publication_day,
                    'publication_month': record.publication_month,
                    'publication_year': record.publication_year,
                    'is_steamship': record.is_steamship,
                    'format_type': record.format_type.value,
                    'confidence': record.confidence,
                    'raw_line': record.raw_line
                })

            stats['processed'] += 1
            stats['total_records'] += len(records)
            stats['records_with_port'] += sum(1 for r in records if r.destination_port)
            stats['records_with_date'] += sum(1 for r in records if r.day and r.month)

            if i % 50 == 0:
                print(f"  Progress: {stats['total_records']} records extracted so far...")

        except Exception as e:
            print(f"  ERROR: {e}")
            stats['failed'] += 1
            continue

    # Save to CSV
    csv_file = output_dir / "ttj_shipments_all.csv"
    print(f"\nSaving {len(all_records)} records to CSV...")

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'format_type', 'confidence', 'raw_line'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"✓ CSV saved: {csv_file}")

    # Save summary JSON
    summary_file = output_dir / "processing_summary.json"
    summary = {
        'timestamp': datetime.now().isoformat(),
        'statistics': stats,
        'port_coverage': f"{100 * stats['records_with_port'] / max(1, stats['total_records']):.1f}%",
        'date_coverage': f"{100 * stats['records_with_date'] / max(1, stats['total_records']):.1f}%"
    }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"✓ Summary saved: {summary_file}")

    # Print final statistics
    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Files processed: {stats['processed']}/{stats['total_files']}")
    print(f"Failed: {stats['failed']}")
    print(f"\nTotal ship records: {stats['total_records']:,}")
    print(f"  With destination port: {stats['records_with_port']:,} ({100 * stats['records_with_port'] / max(1, stats['total_records']):.1f}%)")
    print(f"  With arrival date: {stats['records_with_date']:,} ({100 * stats['records_with_date'] / max(1, stats['total_records']):.1f}%)")
    print(f"\nOutput files:")
    print(f"  CSV: {csv_file}")
    print(f"  Summary: {summary_file}")
    print("=" * 80)


def main():
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/parsed_output")

    print("TTJ BATCH PARSER")
    print("=" * 80)
    print(f"OCR directory: {ocr_dir}")
    print(f"Output directory: {output_dir}")
    print()

    process_all_files(ocr_dir, output_dir)


if __name__ == '__main__':
    main()
