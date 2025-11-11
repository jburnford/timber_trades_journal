#!/usr/bin/env python3
"""
Merge timeout records with existing complete records.
"""
import csv
import sys
from pathlib import Path

# Increase CSV field size limit to handle large fields
csv.field_size_limit(sys.maxsize)

def merge_final_records():
    """Merge timeout records with existing ttj_shipments_complete.csv."""

    output_dir = Path("/home/jic823/TTJ Forest of Numbers/parsed_output")

    existing_file = output_dir / "ttj_shipments_complete.csv"
    timeout_file = output_dir / "timeout_all_records.csv"
    final_file = output_dir / "ttj_shipments_final.csv"

    print("=" * 80)
    print("MERGING RECORDS")
    print("=" * 80)

    # Complete fieldnames from both files
    # Existing CSV has: format_type, confidence
    # Timeout CSV does not have these fields
    fieldnames = [
        'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
        'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
        'publication_day', 'publication_month', 'publication_year',
        'is_steamship', 'format_type', 'confidence', 'raw_line'
    ]

    existing_count = 0
    timeout_count = 0

    # Write merged file
    with open(final_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        # Copy existing records
        print(f"\nReading existing records from: {existing_file.name}")
        if existing_file.exists():
            with open(existing_file, 'r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    writer.writerow(row)
                    existing_count += 1

            print(f"  Copied {existing_count:,} existing records")
        else:
            print(f"  WARNING: {existing_file.name} not found!")

        # Add timeout records
        print(f"\nAdding timeout records from: {timeout_file.name}")
        if timeout_file.exists():
            with open(timeout_file, 'r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    # Add missing fields with default values
                    if 'format_type' not in row:
                        row['format_type'] = ''
                    if 'confidence' not in row:
                        row['confidence'] = ''
                    writer.writerow(row)
                    timeout_count += 1

            print(f"  Added {timeout_count:,} timeout records")
        else:
            print(f"  WARNING: {timeout_file.name} not found!")

    total_count = existing_count + timeout_count

    print("\n" + "=" * 80)
    print("MERGE RESULTS")
    print("=" * 80)
    print(f"Existing records:  {existing_count:>8,}")
    print(f"Timeout records:   {timeout_count:>8,}")
    print(f"                   {'-'*10}")
    print(f"Total records:     {total_count:>8,}")
    print("=" * 80)
    print(f"\nFinal output: {final_file}")
    print("=" * 80)

    # Expected totals
    expected_existing = 145058
    expected_timeout = 7927
    expected_total = expected_existing + expected_timeout

    if existing_count == expected_existing and timeout_count == expected_timeout:
        print(f"\n✓ All record counts match expected values!")
        print(f"  Existing: {expected_existing:,} ✓")
        print(f"  Timeout:  {expected_timeout:,} ✓")
        print(f"  Total:    {expected_total:,} ✓")
    else:
        if existing_count != expected_existing:
            print(f"\n⚠ Existing records mismatch: got {existing_count:,}, expected {expected_existing:,}")
        if timeout_count != expected_timeout:
            print(f"⚠ Timeout records mismatch: got {timeout_count:,}, expected {expected_timeout:,}")

    return total_count

if __name__ == '__main__':
    merge_final_records()
