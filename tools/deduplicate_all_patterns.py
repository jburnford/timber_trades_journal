#!/usr/bin/env python3
"""
Remove all duplicate patterns from dataset caused by LLM OCR hallucinations.
Keeps first occurrence of each unique (ship + port + date) combination.
Preserves legitimate repeat voyages (same ship on different dates).
"""

import csv
from pathlib import Path
from collections import defaultdict


def deduplicate_dataset(input_csv: Path, output_csv: Path):
    """
    Remove duplicate records caused by OCR repetition errors.

    Deduplication logic:
    - Signature: (ship_name, origin_port, destination_port, day, month, year)
    - Keep: First occurrence of each signature
    - Remove: Subsequent occurrences
    - Preserve: Same ship on different dates (legitimate repeat voyages)
    """

    csv.field_size_limit(1000000)

    print("=" * 80)
    print("OCR DUPLICATION REMOVAL")
    print("=" * 80)
    print("Removing LLM hallucination duplicates while preserving repeat voyages")
    print()

    # Read all records
    all_records = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            all_records.append(row)

    print(f"Total records before deduplication: {len(all_records):,}")

    # Group by signature
    signatures = defaultdict(list)
    for idx, rec in enumerate(all_records):
        sig = (
            rec['ship_name'],
            rec['origin_port'],
            rec['destination_port'],
            rec['arrival_day'],
            rec['arrival_month'],
            rec['arrival_year']
        )
        signatures[sig].append((idx, rec))

    # Analyze duplication patterns
    exact_dupes = {sig: recs for sig, recs in signatures.items() if len(recs) > 1}

    print(f"Unique ship/port/date combinations: {len(signatures):,}")
    print(f"Patterns with duplicates: {len(exact_dupes):,}")

    # Report major duplication issues
    print("\nMajor duplication patterns (≥50 duplicates):")
    major_issues = sorted(
        [(sig, recs) for sig, recs in exact_dupes.items() if len(recs) >= 50],
        key=lambda x: len(x[1]),
        reverse=True
    )

    for sig, recs in major_issues[:20]:
        ship, origin, dest, day, month, year = sig
        source_files = set(r[1]['source_file'] for r in recs)
        print(f"  {len(recs):4} × {ship:30} {origin} → {dest} ({month} {day}, {year})")
        if len(source_files) == 1:
            print(f"       Source: {list(source_files)[0][:60]}...")

    if len(major_issues) > 20:
        print(f"  ... and {len(major_issues) - 20} more major patterns")

    # Keep first occurrence of each signature
    records_to_keep = []
    duplicates_removed = 0

    # Sort signatures to maintain chronological order
    for sig in sorted(signatures.keys(), key=lambda s: (s[5] or '9999', s[4] or 'ZZZ', s[3] or '99')):
        recs = signatures[sig]
        # Keep first record (lowest index)
        first_rec = min(recs, key=lambda x: x[0])
        records_to_keep.append(first_rec[1])
        duplicates_removed += len(recs) - 1

    print(f"\nTotal records after deduplication: {len(records_to_keep):,}")
    print(f"Duplicates removed: {duplicates_removed:,}")
    print(f"Reduction: {100*duplicates_removed/len(all_records):.1f}%")

    # Write deduplicated data
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records_to_keep)

    print(f"\n✓ Saved deduplicated shipments to: {output_csv}")

    # Also deduplicate cargo details
    cargo_input = input_csv.parent / 'ttj_cargo_details.csv'
    cargo_output = output_csv.parent / 'ttj_cargo_details_deduped.csv'

    if cargo_input.exists():
        print("\nDeduplicating cargo details...")

        # Get record_ids to keep
        record_ids_to_keep = set(rec['record_id'] for rec in records_to_keep)

        cargo_kept = 0
        cargo_removed = 0

        with open(cargo_input, 'r', encoding='utf-8') as f_in, \
             open(cargo_output, 'w', newline='', encoding='utf-8') as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                if row['record_id'] in record_ids_to_keep:
                    writer.writerow(row)
                    cargo_kept += 1
                else:
                    cargo_removed += 1

        print(f"  Cargo records kept: {cargo_kept:,}")
        print(f"  Cargo records removed: {cargo_removed:,}")
        print(f"  ✓ Saved to: {cargo_output}")

    # Generate verification stats
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    # Re-check for any remaining duplicates
    final_sigs = defaultdict(int)
    for rec in records_to_keep:
        sig = (
            rec['ship_name'],
            rec['origin_port'],
            rec['destination_port'],
            rec['arrival_day'],
            rec['arrival_month'],
            rec['arrival_year']
        )
        final_sigs[sig] += 1

    remaining_dupes = sum(1 for count in final_sigs.values() if count > 1)

    if remaining_dupes == 0:
        print("✓ No duplicate signatures remain")
    else:
        print(f"⚠ WARNING: {remaining_dupes} duplicate signatures still present")

    print(f"\nFinal dataset statistics:")
    print(f"  Unique ship/port/date combinations: {len(final_sigs):,}")
    print(f"  Total ship records: {len(records_to_keep):,}")
    print(f"  Total cargo records: {cargo_kept:,}")

    print("\n" + "=" * 80)
    print("DEDUPLICATION COMPLETE")
    print("=" * 80)
    print("\nDocumentation: See final_output/OCR_DUPLICATION_ISSUES.md")
    print("Next: Use deduped/ directory for all analysis")
    print("=" * 80)

    return {
        'original_count': len(all_records),
        'final_count': len(records_to_keep),
        'duplicates_removed': duplicates_removed,
        'major_patterns': len(major_issues),
        'verification_passed': remaining_dupes == 0
    }


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    input_dir = base_dir / "final_output"
    output_dir = base_dir / "final_output" / "deduped"
    output_dir.mkdir(exist_ok=True)

    input_csv = input_dir / "ttj_shipments.csv"
    output_csv = output_dir / "ttj_shipments_deduped.csv"

    stats = deduplicate_dataset(input_csv, output_csv)

    # Save stats
    import json
    stats_file = output_dir / "deduplication_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\n✓ Saved statistics to: {stats_file}")


if __name__ == '__main__':
    main()
