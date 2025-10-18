#!/usr/bin/env python3
"""
Detect duplicate record patterns in the dataset.
Identifies OCR/LLM repetition issues like the Oresund case.
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict


def detect_duplicate_patterns(input_csv: Path):
    """Scan for duplicate record patterns."""

    csv.field_size_limit(1000000)

    print("=" * 80)
    print("SCANNING FOR DUPLICATE PATTERNS")
    print("=" * 80)

    all_records = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_records.append(row)

    print(f"Total records: {len(all_records):,}")

    # Strategy 1: Identical ship+port+date combinations
    print("\n" + "-" * 80)
    print("EXACT DUPLICATES (same ship, port, date)")
    print("-" * 80)

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

    exact_dupes = {sig: recs for sig, recs in signatures.items() if len(recs) > 1}

    if exact_dupes:
        print(f"Found {len(exact_dupes)} patterns with exact duplicates:")
        sorted_dupes = sorted(exact_dupes.items(), key=lambda x: len(x[1]), reverse=True)

        for i, (sig, recs) in enumerate(sorted_dupes[:20], 1):
            ship, origin, dest, day, month, year = sig
            print(f"\n{i}. {ship} from {origin} to {dest} on {month} {day}, {year}")
            print(f"   Count: {len(recs)} records")
            print(f"   Source files: {set(r[1]['source_file'] for r in recs)}")
            print(f"   Line numbers: {[r[1]['line_number'] for r in recs[:10]]}")
            if len(recs) > 10:
                print(f"   ... and {len(recs) - 10} more")

        if len(sorted_dupes) > 20:
            print(f"\n... and {len(sorted_dupes) - 20} more duplicate patterns")

        # Count total duplicate records
        total_dupes = sum(len(recs) - 1 for recs in exact_dupes.values())
        print(f"\nTotal duplicate records (keeping 1 of each): {total_dupes:,}")
    else:
        print("✓ No exact duplicates found")

    # Strategy 2: Consecutive repeated lines in same file
    print("\n" + "-" * 80)
    print("CONSECUTIVE REPEATING LINES (same file)")
    print("-" * 80)

    by_file = defaultdict(list)
    for rec in all_records:
        by_file[rec['source_file']].append(rec)

    consecutive_issues = []
    for source_file, recs in by_file.items():
        # Sort by line number
        recs.sort(key=lambda x: int(x['line_number']))

        # Look for repeating patterns
        i = 0
        while i < len(recs) - 1:
            # Check if current record repeats
            current_sig = (recs[i]['ship_name'], recs[i]['origin_port'], recs[i]['arrival_day'])

            # Count consecutive matches
            repeat_count = 1
            j = i + 1
            while j < len(recs):
                next_sig = (recs[j]['ship_name'], recs[j]['origin_port'], recs[j]['arrival_day'])
                if next_sig == current_sig:
                    repeat_count += 1
                    j += 1
                else:
                    break

            if repeat_count >= 3:  # 3+ consecutive repeats
                consecutive_issues.append({
                    'file': source_file,
                    'start_line': recs[i]['line_number'],
                    'end_line': recs[j-1]['line_number'],
                    'count': repeat_count,
                    'ship': recs[i]['ship_name'],
                    'origin': recs[i]['origin_port'],
                    'dest': recs[i]['destination_port']
                })
                i = j
            else:
                i += 1

    if consecutive_issues:
        print(f"Found {len(consecutive_issues)} files with consecutive repeating lines:")
        for i, issue in enumerate(sorted(consecutive_issues, key=lambda x: x['count'], reverse=True)[:20], 1):
            print(f"\n{i}. File: {issue['file']}")
            print(f"   Lines {issue['start_line']}-{issue['end_line']}: {issue['count']} repeats")
            print(f"   Ship: {issue['ship']} from {issue['origin']} to {issue['dest']}")

        if len(consecutive_issues) > 20:
            print(f"\n... and {len(consecutive_issues) - 20} more files with consecutive repeats")
    else:
        print("✓ No consecutive repeating patterns found")

    # Strategy 3: Same ship appearing many times in same source file
    print("\n" + "-" * 80)
    print("HIGH-FREQUENCY SHIPS IN SINGLE FILES")
    print("-" * 80)

    high_freq_ships = []
    for source_file, recs in by_file.items():
        ship_counts = Counter(rec['ship_name'] for rec in recs)
        for ship, count in ship_counts.items():
            if count >= 10:  # Ship appears 10+ times in one file
                high_freq_ships.append({
                    'file': source_file,
                    'ship': ship,
                    'count': count,
                    'total_in_file': len(recs)
                })

    if high_freq_ships:
        print(f"Found {len(high_freq_ships)} ship/file combinations with ≥10 occurrences:")
        for i, issue in enumerate(sorted(high_freq_ships, key=lambda x: x['count'], reverse=True)[:20], 1):
            pct = 100 * issue['count'] / issue['total_in_file']
            print(f"{i:2}. {issue['ship']:30} {issue['count']:4} times ({pct:5.1f}% of file)")
            print(f"    File: {issue['file']}")

        if len(high_freq_ships) > 20:
            print(f"\n... and {len(high_freq_ships) - 20} more high-frequency ships")
    else:
        print("✓ No suspicious high-frequency ships found")

    # Summary recommendations
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)

    if exact_dupes:
        total_to_remove = sum(len(recs) - 1 for recs in exact_dupes.values())
        print(f"✗ Found {len(exact_dupes)} duplicate patterns affecting {total_to_remove:,} records")
        print(f"  Recommendation: Deduplicate by keeping first occurrence of each pattern")
    else:
        print("✓ No exact duplicates found")

    if consecutive_issues:
        print(f"✗ Found {len(consecutive_issues)} files with consecutive repeating lines")
        print(f"  Recommendation: Investigate source OCR files, may indicate LLM hallucination")
    else:
        print("✓ No consecutive repeating patterns")

    if high_freq_ships:
        print(f"⚠ Found {len(high_freq_ships)} unusually high-frequency ships in single files")
        print(f"  Recommendation: Manual review to verify legitimacy")
    else:
        print("✓ No suspicious high-frequency patterns")

    print("=" * 80)

    return {
        'exact_dupes': exact_dupes,
        'consecutive_issues': consecutive_issues,
        'high_freq_ships': high_freq_ships
    }


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    input_csv = base_dir / "final_output" / "ttj_shipments.csv"

    results = detect_duplicate_patterns(input_csv)

    # Save detailed report
    report_file = base_dir / "final_output" / "duplicate_patterns_report.json"
    import json

    # Convert for JSON serialization
    json_results = {
        'exact_dupes_count': len(results['exact_dupes']),
        'exact_dupes_total_records': sum(len(recs) - 1 for recs in results['exact_dupes'].values()),
        'consecutive_issues_count': len(results['consecutive_issues']),
        'high_freq_ships_count': len(results['high_freq_ships']),
        'consecutive_issues': results['consecutive_issues'],
        'high_freq_ships': results['high_freq_ships']
    }

    with open(report_file, 'w') as f:
        json.dump(json_results, f, indent=2)

    print(f"\n✓ Saved detailed report to: {report_file}")


if __name__ == '__main__':
    main()
