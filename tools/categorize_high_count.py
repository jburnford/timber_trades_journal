#!/usr/bin/env python3
"""
Phase 1: Categorize high character count records.
Analyzes records >300 chars to determine extraction strategy.
"""
import csv
import sys
from pathlib import Path
from collections import Counter

csv.field_size_limit(sys.maxsize)

def categorize_record(row: dict) -> dict:
    """Categorize a single high-count record."""

    char_count = int(row['raw_line_char_count'])
    raw_line = row['raw_line']

    # Count indicators
    at_count = raw_line.count('@')
    emdash_count = raw_line.count('—')
    hyphen_count = raw_line.count('-')
    semicolon_count = raw_line.count(';')
    period_count = raw_line.count('.')

    # Determine size category
    if char_count >= 10000:
        size_category = 'MEGA'
    elif char_count >= 1000:
        size_category = 'HIGH'
    elif char_count >= 500:
        size_category = 'MEDIUM'
    else:
        size_category = 'LOW'

    # Determine format type
    if at_count == 0 and emdash_count == 0:
        if hyphen_count > 5 and semicolon_count > 3:
            format_type = 'HYPHEN_SEMICOLON'
        else:
            format_type = 'UNKNOWN'
    elif at_count > 0 and emdash_count > 0:
        format_type = 'STANDARD'
    elif at_count > 0 and hyphen_count > emdash_count:
        format_type = 'MIXED_HYPHEN'
    else:
        format_type = 'OTHER'

    # Estimate ships based on @ count (most reliable indicator)
    estimated_ships = max(at_count, 1)  # At least 1 ship (the one we already extracted)

    # Additional ships we missed
    missed_ships = max(0, estimated_ships - 1)

    return {
        'source_file': row['source_file'],
        'line_number': row['line_number'],
        'extracted_ship': row['ship_name'],
        'char_count': char_count,
        'size_category': size_category,
        'format_type': format_type,
        'at_symbols': at_count,
        'emdashes': emdash_count,
        'hyphens': hyphen_count,
        'semicolons': semicolon_count,
        'periods': period_count,
        'estimated_total_ships': estimated_ships,
        'estimated_missed_ships': missed_ships,
        'raw_line_preview': raw_line[:200] + '...' if len(raw_line) > 200 else raw_line
    }

def categorize_high_count_records(input_csv: Path, output_csv: Path):
    """Categorize all records with >300 characters."""

    print("="*80)
    print("PHASE 1: CATEGORIZING HIGH CHARACTER COUNT RECORDS")
    print("="*80)

    high_count_records = []
    total_processed = 0

    print(f"\nReading {input_csv}...")

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_processed += 1
            char_count = int(row['raw_line_char_count'])

            if char_count > 300:
                categorized = categorize_record(row)
                high_count_records.append(categorized)

            if total_processed % 50000 == 0:
                print(f"  Processed {total_processed:,} records...")

    print(f"\nTotal records processed: {total_processed:,}")
    print(f"High-count records found: {len(high_count_records):,}")

    # Write categorized records
    fieldnames = [
        'source_file', 'line_number', 'extracted_ship', 'char_count',
        'size_category', 'format_type', 'at_symbols', 'emdashes', 'hyphens',
        'semicolons', 'periods', 'estimated_total_ships', 'estimated_missed_ships',
        'raw_line_preview'
    ]

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(high_count_records)

    print(f"\nCategorized records written to: {output_csv}")

    # Generate summary statistics
    print("\n" + "="*80)
    print("CATEGORIZATION SUMMARY")
    print("="*80)

    # By size category
    size_counts = Counter(r['size_category'] for r in high_count_records)
    print(f"\nBy Size Category:")
    for category in ['MEGA', 'HIGH', 'MEDIUM', 'LOW']:
        count = size_counts.get(category, 0)
        pct = (count / len(high_count_records)) * 100 if high_count_records else 0
        print(f"  {category:10} : {count:5,} records ({pct:5.2f}%)")

    # By format type
    format_counts = Counter(r['format_type'] for r in high_count_records)
    print(f"\nBy Format Type:")
    for fmt, count in format_counts.most_common():
        pct = (count / len(high_count_records)) * 100
        print(f"  {fmt:20} : {count:5,} records ({pct:5.2f}%)")

    # Recovery estimates
    total_estimated_ships = sum(r['estimated_total_ships'] for r in high_count_records)
    total_missed_ships = sum(r['estimated_missed_ships'] for r in high_count_records)

    print(f"\nRecovery Estimates:")
    print(f"  Total ships in high-count records: {total_estimated_ships:,}")
    print(f"  Already extracted (first ship):    {len(high_count_records):,}")
    print(f"  Estimated missed ships:            {total_missed_ships:,}")

    # By category
    print(f"\nMissed Ships by Category:")
    for category in ['MEGA', 'HIGH', 'MEDIUM', 'LOW']:
        category_records = [r for r in high_count_records if r['size_category'] == category]
        missed = sum(r['estimated_missed_ships'] for r in category_records)
        print(f"  {category:10} : {missed:6,} ships")

    # Top 10 worst offenders
    print(f"\nTop 10 Records with Most Missed Ships:")
    sorted_records = sorted(high_count_records, key=lambda x: x['estimated_missed_ships'], reverse=True)
    for i, rec in enumerate(sorted_records[:10], 1):
        print(f"  [{i:2}] {rec['source_file'][:50]:50} | Missed: {rec['estimated_missed_ships']:4} | Chars: {rec['char_count']:7,}")

    print("\n" + "="*80)
    print(f"Categorization complete! Output: {output_csv}")
    print("="*80)

    return {
        'total_records': len(high_count_records),
        'estimated_missed_ships': total_missed_ships,
        'size_counts': dict(size_counts),
        'format_counts': dict(format_counts)
    }

if __name__ == '__main__':
    input_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final.csv")
    output_csv = Path("/home/jic823/TTJ Forest of Numbers/analysis/high_count_categories.csv")

    categorize_high_count_records(input_csv, output_csv)
