#!/usr/bin/env python3
"""
Phase 4: Intelligent merge with deduplication.
1. Load existing database
2. Remove records from affected dates
3. Add recovered records
4. Deduplicate
5. Save as v2
"""
import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Increase CSV field size limit
csv.field_size_limit(10 * 1024 * 1024)

def normalize_date(year, month, day):
    """Convert year, month, day to YYYYMMDD format for matching."""
    if not all([year, month, day]):
        return None
    try:
        return f"{int(year):04d}{int(month):02d}{int(day):02d}"
    except (ValueError, TypeError):
        return None

def deduplicate_records(records, fieldnames):
    """
    Remove duplicate records using signature-based deduplication.
    Keeps first occurrence of each (ship, origin, dest, day, month, year) combination.
    """
    print("Applying deduplication...")
    print(f"  Records before dedup: {len(records):,}")

    # Group by signature
    signatures = defaultdict(list)
    for idx, rec in enumerate(records):
        sig = (
            rec['ship_name'],
            rec['origin_port'],
            rec['destination_port'],
            rec['arrival_day'],
            rec['arrival_month'],
            rec['arrival_year']
        )
        signatures[sig].append((idx, rec))

    # Count duplicates
    exact_dupes = {sig: recs for sig, recs in signatures.items() if len(recs) > 1}
    duplicates_count = sum(len(recs) - 1 for recs in exact_dupes.values())

    print(f"  Unique signatures: {len(signatures):,}")
    print(f"  Signatures with duplicates: {len(exact_dupes):,}")
    print(f"  Duplicate records to remove: {duplicates_count:,}")

    # Keep first occurrence of each signature
    records_to_keep = []
    for sig in sorted(signatures.keys(), key=lambda s: (s[5] or '9999', s[4] or 'ZZZ', s[3] or '99')):
        recs = signatures[sig]
        first_rec = min(recs, key=lambda x: x[0])
        records_to_keep.append(first_rec[1])

    print(f"  Records after dedup: {len(records_to_keep):,}")
    print()

    return records_to_keep, duplicates_count

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    # Input files
    original_csv = base_dir / "parsed_output" / "ttj_shipments_final.csv"
    recovered_csv = base_dir / "parsed_output" / "polaris_recovery" / "ttj_shipments_multipage.csv"
    manifest_path = base_dir / "analysis" / "polaris_ocr_mapping.json"

    # Output files
    output_dir = base_dir / "parsed_output"
    output_csv = output_dir / "ttj_shipments_final_v2.csv"

    print("=" * 80)
    print("PHASE 4: INTELLIGENT MERGE WITH DEDUPLICATION")
    print("=" * 80)
    print()

    # Load affected dates
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    affected_dates = set(manifest['dates'].keys())
    print(f"Affected dates: {len(affected_dates)}")
    print()

    # Load original database
    print("Loading original database...")
    original_records = []
    with open(original_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            original_records.append(row)

    print(f"  Original records: {len(original_records):,}")
    print()

    # Filter out records from affected dates
    print("Filtering out records from affected dates...")
    kept_records = []
    removed_records = []

    for rec in original_records:
        norm_date = normalize_date(
            rec['arrival_year'],
            rec['arrival_month'],
            rec['arrival_day']
        )
        if norm_date and norm_date in affected_dates:
            removed_records.append(rec)
        else:
            kept_records.append(rec)

    print(f"  Records kept (not affected): {len(kept_records):,}")
    print(f"  Records removed (affected dates): {len(removed_records):,}")
    print()

    # Load recovered records
    print("Loading recovered records...")
    recovered_records = []
    with open(recovered_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            recovered_records.append(row)

    print(f"  Recovered records: {len(recovered_records):,}")
    print()

    # Combine datasets
    print("Combining datasets...")
    all_records = kept_records + recovered_records
    print(f"  Combined records (before dedup): {len(all_records):,}")
    print()

    # Deduplicate
    final_records, duplicates_removed = deduplicate_records(all_records, fieldnames)

    # Save final database
    print("Saving final database...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_records)

    print(f"  ✓ Saved to: {output_csv}")
    print()

    # Generate summary
    print("=" * 80)
    print("MERGE SUMMARY")
    print("=" * 80)
    print()
    print(f"Original database:          {len(original_records):,} records")
    print(f"  Removed (affected dates): -{len(removed_records):,} records")
    print(f"  Kept (unaffected):        {len(kept_records):,} records")
    print()
    print(f"Recovered data:             +{len(recovered_records):,} records")
    print()
    print(f"Combined (before dedup):    {len(all_records):,} records")
    print(f"  Duplicates removed:       -{duplicates_removed:,} records")
    print()
    print(f"Final database (v2):        {len(final_records):,} records")
    print()
    print(f"Net change: {len(final_records) - len(original_records):+,} records")
    print(f"Recovery impact: {100 * (len(final_records) - len(original_records)) / len(original_records):+.2f}%")
    print()

    # Save merge report
    report = {
        'generated': datetime.now().isoformat(),
        'original_database': str(original_csv),
        'recovered_database': str(recovered_csv),
        'final_database': str(output_csv),
        'affected_dates': len(affected_dates),
        'statistics': {
            'original_records': len(original_records),
            'removed_from_affected_dates': len(removed_records),
            'kept_unaffected': len(kept_records),
            'recovered_records': len(recovered_records),
            'combined_before_dedup': len(all_records),
            'duplicates_removed': duplicates_removed,
            'final_records': len(final_records),
            'net_change': len(final_records) - len(original_records),
            'percent_change': 100 * (len(final_records) - len(original_records)) / len(original_records)
        }
    }

    report_path = output_dir / "polaris_merge_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✓ Merge report saved to: {report_path}")
    print()

    print("=" * 80)
    print("PHASE 4 COMPLETE")
    print("=" * 80)
    print()
    print("Ready for Phase 5: Validation and recovery report")

    return report

if __name__ == '__main__':
    report = main()
