#!/usr/bin/env python3
"""
Merge all timeout CSV files into one unified file.
"""
import csv
from pathlib import Path

def merge_timeout_csvs():
    """Merge all 7 timeout CSV files into one."""

    output_dir = Path("/home/jic823/TTJ Forest of Numbers/parsed_output")

    timeout_files = [
        "timeout_1889_records.csv",
        "timeout_1891_records.csv",
        "timeout_1893_records.csv",
        "timeout_1895_records.csv",
        "timeout_1897_records.csv",
        "timeout_1899_records.csv",
        "timeout_remaining_records.csv"
    ]

    merged_file = output_dir / "timeout_all_records.csv"

    print("Merging timeout CSV files...")
    print("=" * 80)

    fieldnames = [
        'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
        'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
        'publication_day', 'publication_month', 'publication_year',
        'is_steamship', 'raw_line'
    ]

    total_records = 0
    file_stats = []

    # Write merged file
    with open(merged_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for filename in timeout_files:
            filepath = output_dir / filename

            if not filepath.exists():
                print(f"WARNING: {filename} not found, skipping...")
                continue

            file_count = 0
            with open(filepath, 'r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    writer.writerow(row)
                    file_count += 1
                    total_records += 1

            file_stats.append((filename, file_count))
            print(f"  {filename}: {file_count:,} records")

    print("=" * 80)
    print(f"Merged file: {merged_file.name}")
    print(f"Total records: {total_records:,}")
    print("=" * 80)

    # Verify expected count
    expected_total = 7927
    if total_records == expected_total:
        print(f"✓ Record count matches expected: {expected_total:,}")
    else:
        print(f"⚠ Record count mismatch: got {total_records:,}, expected {expected_total:,}")

    return total_records

if __name__ == '__main__':
    merge_timeout_csvs()
