#!/usr/bin/env python3
"""
Detailed analysis of quantity extraction accuracy using matched pairs.

This script analyzes the 1,769 matched cargo records to assess:
1. Exact quantity matches
2. Percentage differences for non-exact matches
3. Common error patterns (OCR digit errors, off-by-factor errors)
4. Unit consistency
5. Overall reliability of automated numerical extraction
"""

import csv
import re
from pathlib import Path
from collections import defaultdict, Counter


def parse_quantity(qty_str):
    """Extract numeric value from quantity string."""
    if not qty_str:
        return None
    qty_str = str(qty_str).replace(',', '').strip()
    match = re.search(r'(\d+(?:\.\d+)?)', qty_str)
    if match:
        return float(match.group(1))
    return None


def categorize_error(auto_qty, human_qty):
    """Categorize the type of quantity error."""
    if auto_qty == human_qty:
        return 'exact'

    ratio = auto_qty / human_qty if human_qty > 0 else 999

    # Check for digit confusion (e.g., 9 vs 93, 624 vs 54)
    if abs(auto_qty - human_qty * 10) < 5:
        return 'missing_digit_human'
    if abs(auto_qty * 10 - human_qty) < 5:
        return 'missing_digit_auto'

    # Check for factor-of-10 errors
    if 9.5 <= ratio <= 10.5:
        return '10x_auto_high'
    if 0.095 <= ratio <= 0.105:
        return '10x_auto_low'

    # Check for close matches
    diff_pct = abs(auto_qty - human_qty) / max(auto_qty, human_qty) * 100
    if diff_pct <= 5:
        return 'close_5pct'
    elif diff_pct <= 10:
        return 'close_10pct'
    elif diff_pct <= 25:
        return 'moderate_diff'
    else:
        return 'large_diff'


def analyze_quantities(matched_csv: Path):
    """Analyze quantity accuracy in matched pairs."""

    stats = {
        'total_matches': 0,
        'missing_data': 0,
        'exact_matches': 0,
        'error_categories': Counter(),
        'by_commodity': defaultdict(lambda: {'exact': 0, 'total': 0, 'errors': []}),
        'by_port': defaultdict(lambda: {'exact': 0, 'total': 0, 'errors': []}),
        'examples': defaultdict(list)
    }

    with open(matched_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row['match_type'].startswith('1:'):
                continue

            stats['total_matches'] += 1

            auto_qty = parse_quantity(row['auto_quantity'])
            human_qty = parse_quantity(row['human_quantity'])

            if auto_qty is None or human_qty is None:
                stats['missing_data'] += 1
                continue

            # Categorize error
            error_cat = categorize_error(auto_qty, human_qty)
            stats['error_categories'][error_cat] += 1

            if error_cat == 'exact':
                stats['exact_matches'] += 1

            # Track by commodity
            commodity = row['auto_commodity'][:20]  # Truncate for display
            stats['by_commodity'][commodity]['total'] += 1
            if error_cat == 'exact':
                stats['by_commodity'][commodity]['exact'] += 1
            else:
                stats['by_commodity'][commodity]['errors'].append(
                    abs(auto_qty - human_qty) / max(auto_qty, human_qty) * 100
                )

            # Track by port
            port = row['auto_port'][:20]
            stats['by_port'][port]['total'] += 1
            if error_cat == 'exact':
                stats['by_port'][port]['exact'] += 1
            else:
                stats['by_port'][port]['errors'].append(
                    abs(auto_qty - human_qty) / max(auto_qty, human_qty) * 100
                )

            # Collect examples
            if len(stats['examples'][error_cat]) < 3:
                stats['examples'][error_cat].append({
                    'auto_qty': auto_qty,
                    'human_qty': human_qty,
                    'auto_unit': row['auto_unit'],
                    'human_unit': row['human_unit'],
                    'commodity': row['auto_commodity'],
                    'port': row['auto_port'],
                    'date': row['auto_date']
                })

    return stats


def print_report(stats):
    """Print detailed analysis report."""

    print("=" * 80)
    print("QUANTITY EXTRACTION ACCURACY ANALYSIS")
    print("=" * 80)

    total = stats['total_matches']
    with_data = total - stats['missing_data']

    print(f"\nDataset: {total:,} matched pairs")
    print(f"  With quantity data: {with_data:,} ({100*with_data/total:.1f}%)")
    print(f"  Missing data: {stats['missing_data']}")

    print(f"\n{'=' * 80}")
    print("OVERALL ACCURACY")
    print("=" * 80)

    for cat in ['exact', 'close_5pct', 'close_10pct', 'moderate_diff', 'large_diff',
                'missing_digit_human', 'missing_digit_auto', '10x_auto_high', '10x_auto_low']:
        count = stats['error_categories'][cat]
        if count > 0:
            pct = 100 * count / with_data
            print(f"  {cat:25s}: {count:5,} ({pct:5.1f}%)")

    # Cumulative accuracy
    exact = stats['error_categories']['exact']
    close5 = exact + stats['error_categories']['close_5pct']
    close10 = close5 + stats['error_categories']['close_10pct']

    print(f"\nCumulative Accuracy:")
    print(f"  Exact: {exact:,} ({100*exact/with_data:.1f}%)")
    print(f"  Within 5%: {close5:,} ({100*close5/with_data:.1f}%)")
    print(f"  Within 10%: {close10:,} ({100*close10/with_data:.1f}%)")

    print(f"\n{'=' * 80}")
    print("ACCURACY BY COMMODITY (Top 10)")
    print("=" * 80)

    # Sort by total count
    sorted_commodities = sorted(
        stats['by_commodity'].items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )[:10]

    print(f"{'Commodity':<20} {'Total':>8} {'Exact':>8} {'Accuracy':>10}")
    print("-" * 80)
    for commodity, data in sorted_commodities:
        accuracy = 100 * data['exact'] / data['total'] if data['total'] > 0 else 0
        print(f"{commodity:<20} {data['total']:8,} {data['exact']:8,} {accuracy:9.1f}%")

    print(f"\n{'=' * 80}")
    print("ACCURACY BY PORT (Top 10)")
    print("=" * 80)

    sorted_ports = sorted(
        stats['by_port'].items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )[:10]

    print(f"{'Port':<20} {'Total':>8} {'Exact':>8} {'Accuracy':>10}")
    print("-" * 80)
    for port, data in sorted_ports:
        accuracy = 100 * data['exact'] / data['total'] if data['total'] > 0 else 0
        print(f"{port:<20} {data['total']:8,} {data['exact']:8,} {accuracy:9.1f}%")

    print(f"\n{'=' * 80}")
    print("ERROR EXAMPLES")
    print("=" * 80)

    for cat in ['exact', '10x_auto_high', 'missing_digit_auto', 'large_diff']:
        examples = stats['examples'].get(cat, [])
        if examples:
            print(f"\n{cat}:")
            for ex in examples[:2]:
                diff_pct = abs(ex['auto_qty'] - ex['human_qty']) / max(ex['auto_qty'], ex['human_qty']) * 100 if ex['auto_qty'] != ex['human_qty'] else 0
                print(f"  Auto: {ex['auto_qty']} {ex['auto_unit']} | Human: {ex['human_qty']} {ex['human_unit']} | Diff: {diff_pct:.0f}%")
                print(f"    {ex['port']} - {ex['commodity']} ({ex['date']})")

    print(f"\n{'=' * 80}")
    print("CONCLUSION")
    print("=" * 80)

    exact_pct = 100 * exact / with_data
    within10_pct = 100 * close10 / with_data

    if exact_pct >= 35:
        reliability = "GOOD"
    elif exact_pct >= 25:
        reliability = "MODERATE"
    else:
        reliability = "POOR"

    print(f"\nQuantity Extraction Reliability: {reliability}")
    print(f"  Exact matches: {exact_pct:.1f}%")
    print(f"  Within 10%: {within10_pct:.1f}%")
    print(f"\nRecommendation:")
    if reliability == "GOOD":
        print("  ✓ Automated quantities are sufficiently reliable for analysis")
        print("  ✓ Expect ~35-40% exact matches, ~45% within 10%")
        print("  ⚠ Manual verification recommended for critical applications")
    elif reliability == "MODERATE":
        print("  ⚠ Automated quantities require careful validation")
        print("  ⚠ Consider manual review for quantitative analysis")
    else:
        print("  ✗ Automated quantities not reliable enough for quantitative analysis")
        print("  ✗ Manual transcription recommended for quantity-dependent research")


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers/validation")
    matched_csv = base_dir / "matched_pairs_1883_fixed.csv"

    print(f"Analyzing: {matched_csv}\n")

    stats = analyze_quantities(matched_csv)
    print_report(stats)

    print(f"\n{'=' * 80}")


if __name__ == '__main__':
    main()
