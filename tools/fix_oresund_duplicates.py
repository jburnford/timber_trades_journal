#!/usr/bin/env python3
"""
Fix Oresund duplication issue: keep 2 original records, remove 1407 duplicates.
"""

import csv
from pathlib import Path


def fix_oresund_duplicates(input_csv: Path, output_csv: Path):
    """Remove duplicate Oresund records, keeping only the first 2."""

    csv.field_size_limit(1000000)

    print("=" * 80)
    print("FIXING ORESUND DUPLICATION ISSUE")
    print("=" * 80)

    # Read all records
    all_records = []
    oresund_records = []

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            if row['origin_port'].strip() == 'Oresund':
                oresund_records.append(row)
            else:
                all_records.append(row)

    print(f"Total records: {len(all_records) + len(oresund_records):,}")
    print(f"Oresund records found: {len(oresund_records):,}")

    # Identify the unique patterns in Oresund records
    # Lines 12 & 13: the two distinct shipments
    unique_patterns = {}
    for rec in oresund_records:
        # Create signature from cargo and dates
        key = (rec['arrival_day'], rec['arrival_month'], rec.get('merchant', ''))
        if key not in unique_patterns:
            unique_patterns[key] = []
        unique_patterns[key].append(rec)

    print(f"Unique Oresund shipment patterns: {len(unique_patterns)}")

    # Keep first occurrence of each pattern
    oresund_to_keep = []
    oresund_removed = 0

    for pattern, records in unique_patterns.items():
        oresund_to_keep.append(records[0])  # Keep first
        oresund_removed += len(records) - 1  # Count rest as duplicates
        if len(records) > 1:
            print(f"  Pattern {pattern}: keeping 1, removing {len(records)-1} duplicates")

    print(f"\nOresund records to keep: {len(oresund_to_keep)}")
    print(f"Oresund duplicates to remove: {oresund_removed}")

    # Combine all records
    final_records = all_records + oresund_to_keep
    print(f"\nFinal record count: {len(final_records):,} (was {len(all_records) + len(oresund_records):,})")
    print(f"Records removed: {oresund_removed:,}")

    # Write cleaned data
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_records)

    print(f"\n✓ Saved cleaned data to: {output_csv}")

    # Also fix cargo details if needed
    cargo_input = input_csv.parent / 'ttj_cargo_details.csv'
    cargo_output = output_csv.parent / 'ttj_cargo_details_cleaned.csv'

    if cargo_input.exists():
        print("\nChecking cargo details for Oresund duplicates...")
        # Get record_ids to remove
        oresund_record_ids_to_remove = set()
        for pattern, records in unique_patterns.items():
            for rec in records[1:]:  # Skip first, remove rest
                oresund_record_ids_to_remove.add(rec['record_id'])

        # Filter cargo
        cargo_kept = 0
        cargo_removed = 0

        with open(cargo_input, 'r', encoding='utf-8') as f_in, \
             open(cargo_output, 'w', newline='', encoding='utf-8') as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                if row['record_id'] in oresund_record_ids_to_remove:
                    cargo_removed += 1
                else:
                    writer.writerow(row)
                    cargo_kept += 1

        print(f"  Cargo records kept: {cargo_kept:,}")
        print(f"  Cargo records removed: {cargo_removed:,}")
        print(f"  ✓ Saved to: {cargo_output}")

    print("\n" + "=" * 80)
    print("DUPLICATION FIX COMPLETE")
    print("=" * 80)
    print("\nNext: Update ports_for_review.csv to mark 'Oresund' as ACCEPT")


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    input_dir = base_dir / "final_output"
    output_dir = base_dir / "final_output" / "deduped"
    output_dir.mkdir(exist_ok=True)

    input_csv = input_dir / "ttj_shipments.csv"
    output_csv = output_dir / "ttj_shipments_deduped.csv"

    fix_oresund_duplicates(input_csv, output_csv)


if __name__ == '__main__':
    main()
