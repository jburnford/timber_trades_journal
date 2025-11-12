#!/usr/bin/env python3
"""
Reparse only 1874-1875 files with improved multi-ship parser.
Then replace those records in the existing database.
"""

import csv
import sys
from pathlib import Path
from ttj_parser_v3 import TTJContextParser, extract_publication_date_from_filename

csv.field_size_limit(1000000)


def parse_1874_1875_files(ocr_dir: Path):
    """Parse only 1874-1875 OCR files."""
    parser = TTJContextParser()

    # Find all 1874-1875 files
    all_files = sorted(ocr_dir.glob("*.txt"))
    target_files = []

    for file_path in all_files:
        year, _, _ = extract_publication_date_from_filename(file_path.name)
        if year in (1874, 1875):
            target_files.append(file_path)

    print(f"Found {len(target_files)} files from 1874-1875")
    print()

    all_records = []

    for i, file_path in enumerate(target_files, 1):
        print(f"[{i}/{len(target_files)}] Parsing {file_path.name[:60]}...")

        try:
            records = parser.parse_file(file_path)

            # Convert to dict format
            for record in records:
                all_records.append({
                    'source_file': file_path.name,
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

            print(f"  → {len(records)} records")

        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    print()
    print(f"Total new records: {len(all_records):,}")

    return all_records


def compare_and_replace(new_records, existing_db: Path, output_db: Path):
    """Compare new vs old records and create updated database."""

    # Read existing database
    print(f"Reading existing database: {existing_db}")
    with open(existing_db, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing_records = list(reader)

    print(f"  Existing total: {len(existing_records):,} records")

    # Count existing 1874-1875 records
    old_1874_1875 = [r for r in existing_records
                     if r['publication_year'] in ('1874', '1875')]

    print(f"  Existing 1874-1875: {len(old_1874_1875):,} records")
    print()

    # Filter out old 1874-1875 records
    other_records = [r for r in existing_records
                    if r['publication_year'] not in ('1874', '1875')]

    print(f"Records from other years: {len(other_records):,}")
    print(f"New 1874-1875 records: {len(new_records):,}")
    print()

    # Show comparison
    print("=" * 60)
    print("COMPARISON:")
    print("=" * 60)
    print(f"Old 1874-1875: {len(old_1874_1875):,} records")
    print(f"New 1874-1875: {len(new_records):,} records")
    print(f"Difference: {len(new_records) - len(old_1874_1875):+,} records")
    print()

    # Calculate improvement percentage
    if len(old_1874_1875) > 0:
        pct_change = ((len(new_records) - len(old_1874_1875)) / len(old_1874_1875)) * 100
        print(f"Change: {pct_change:+.1f}%")
    print()

    # Combine records
    combined_records = other_records + new_records
    combined_records.sort(key=lambda x: (x['publication_year'], x['publication_month'],
                                         x['publication_day'], x['source_file'],
                                         x['line_number']))

    print(f"Final database size: {len(combined_records):,} records")
    print()

    # Write new database
    print(f"Writing updated database to: {output_db}")
    with open(output_db, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'format_type', 'confidence', 'raw_line'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined_records)

    print("✓ Done!")
    print()

    return len(old_1874_1875), len(new_records), len(combined_records)


def main():
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    existing_db = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final_v2.csv")
    output_db = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final_v3_1874_1875_fixed.csv")

    print("=" * 80)
    print("REPARSE 1874-1875 WITH IMPROVED MULTI-SHIP PARSER")
    print("=" * 80)
    print()

    # Step 1: Parse 1874-1875 files
    new_records = parse_1874_1875_files(ocr_dir)

    if not new_records:
        print("ERROR: No records parsed!")
        return 1

    # Step 2: Compare and replace
    old_count, new_count, final_count = compare_and_replace(
        new_records, existing_db, output_db
    )

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Old 1874-1875 records: {old_count:,}")
    print(f"New 1874-1875 records: {new_count:,}")
    print(f"Improvement: {new_count - old_count:+,} records ({((new_count - old_count) / old_count * 100):+.1f}%)")
    print()
    print(f"Final database: {final_count:,} records")
    print(f"Output: {output_db}")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
