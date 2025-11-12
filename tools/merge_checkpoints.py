#!/usr/bin/env python3
"""
Merge checkpoint CSV files with proper field size limit handling.
"""
import csv
import sys
from pathlib import Path

# MUST set this before any CSV operations
csv.field_size_limit(10000000)  # 10MB limit

def merge_checkpoints(output_dir: Path):
    """Merge all checkpoint files into final output."""
    checkpoint_files = sorted(output_dir.glob("ttj_shipments_checkpoint_*.csv"))

    if not checkpoint_files:
        print("No checkpoint files found!")
        return

    csv_file = output_dir / "ttj_shipments_multipage.csv"

    print(f"Merging {len(checkpoint_files)} checkpoint files...")

    with open(csv_file, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'format_type', 'confidence', 'raw_line'
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        total_records = 0
        for i, checkpoint_file in enumerate(checkpoint_files, 1):
            print(f"  [{i}/{len(checkpoint_files)}] Merging {checkpoint_file.name}...")
            file_records = 0
            try:
                with open(checkpoint_file, 'r', newline='', encoding='utf-8') as infile:
                    reader = csv.DictReader(infile)
                    for row in reader:
                        writer.writerow(row)
                        file_records += 1
                        total_records += 1
                print(f"      Added {file_records:,} records")
            except Exception as e:
                print(f"      ERROR: {e}")
                continue

    print(f"\n✓ Merged {total_records:,} total records into: {csv_file}")
    print(f"  File size: {csv_file.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/parsed_output")
    merge_checkpoints(output_dir)
