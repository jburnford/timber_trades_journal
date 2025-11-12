#!/usr/bin/env python3
"""
Analyze rows with high character counts to find missed ships.
"""
import csv
import sys
from pathlib import Path
from collections import Counter

csv.field_size_limit(sys.maxsize)

def analyze_char_counts(csv_file: Path):
    """Analyze character count distribution and high-count examples."""

    char_counts = []
    high_count_examples = []  # Store examples > 300 chars

    print("Reading CSV and analyzing character counts...")

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            char_count = int(row['raw_line_char_count'])
            char_counts.append(char_count)

            # Collect examples with high character counts
            if char_count > 300:
                high_count_examples.append({
                    'source_file': row['source_file'],
                    'ship_name': row['ship_name'],
                    'char_count': char_count,
                    'raw_line': row['raw_line']
                })

    # Statistics
    char_counts.sort()
    total = len(char_counts)

    print("\n" + "="*80)
    print("CHARACTER COUNT DISTRIBUTION")
    print("="*80)
    print(f"Total records: {total:,}")
    print(f"\nPercentiles:")
    print(f"  Min:  {char_counts[0]}")
    print(f"  25%:  {char_counts[int(total * 0.25)]}")
    print(f"  50%:  {char_counts[int(total * 0.50)]}")
    print(f"  75%:  {char_counts[int(total * 0.75)]}")
    print(f"  90%:  {char_counts[int(total * 0.90)]}")
    print(f"  95%:  {char_counts[int(total * 0.95)]}")
    print(f"  99%:  {char_counts[int(total * 0.99)]}")
    print(f"  Max:  {char_counts[-1]}")

    # Count by ranges
    ranges = [
        (0, 100, "0-100"),
        (100, 200, "100-200"),
        (200, 300, "200-300"),
        (300, 400, "300-400"),
        (400, 500, "400-500"),
        (500, 1000, "500-1000"),
        (1000, 10000, "1000+")
    ]

    print(f"\nCount by range:")
    for min_val, max_val, label in ranges:
        count = sum(1 for c in char_counts if min_val <= c < max_val)
        pct = (count / total) * 100
        print(f"  {label:12} : {count:8,} ({pct:5.2f}%)")

    # Show high character count examples
    print("\n" + "="*80)
    print("HIGH CHARACTER COUNT EXAMPLES (>300 chars)")
    print("="*80)

    # Sort by character count descending
    high_count_examples.sort(key=lambda x: x['char_count'], reverse=True)

    print(f"\nFound {len(high_count_examples):,} records with >300 characters")
    print(f"\nTop 20 longest raw_line entries:\n")

    for i, example in enumerate(high_count_examples[:20], 1):
        print(f"\n[{i}] Source: {example['source_file']}")
        print(f"    Ship: {example['ship_name']}")
        print(f"    Chars: {example['char_count']}")
        print(f"    Raw line:")

        # Show raw line with line breaks for readability
        raw = example['raw_line']
        # Count potential ship indicators
        dash_count = raw.count('—')
        at_count = raw.count('@')

        print(f"    >>> Indicators: {dash_count} dashes (—), {at_count} @ symbols")
        print(f"    >>> Text: {raw[:200]}...")
        if len(raw) > 200:
            print(f"    >>> ...{raw[-100:]}")

    # Analyze patterns in high-count lines
    print("\n" + "="*80)
    print("PATTERN ANALYSIS")
    print("="*80)

    # Count indicators in high-count lines
    total_dashes = 0
    total_ats = 0
    total_commas = 0

    for example in high_count_examples:
        raw = example['raw_line']
        total_dashes += raw.count('—')
        total_ats += raw.count('@')
        total_commas += raw.count(',')

    if high_count_examples:
        avg_dashes = total_dashes / len(high_count_examples)
        avg_ats = total_ats / len(high_count_examples)
        avg_commas = total_commas / len(high_count_examples)

        print(f"\nAverage indicators per high-count line:")
        print(f"  Dashes (—):  {avg_dashes:.2f}")
        print(f"  At symbols (@): {avg_ats:.2f}")
        print(f"  Commas (,):  {avg_commas:.2f}")

        print(f"\nEstimated ships per high-count line:")
        # Each ship typically has format: Ship @ Port,—cargo, merchant
        # So 1 @ and 1+ dashes suggest 1 ship
        print(f"  Based on @ symbols: {avg_ats:.2f} potential ships per line")
        print(f"  Total potential missed ships: {int(len(high_count_examples) * (avg_ats - 1))}")

if __name__ == '__main__':
    csv_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final.csv")
    analyze_char_counts(csv_file)
