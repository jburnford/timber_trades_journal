#!/usr/bin/env python3
"""
Match automated cargo records to human ground truth by publication issue.

Matching strategy:
- Group by publication issue (weekly TTJ edition)
- Within each issue, match on Origin Port + Commodity (fuzzy)
- This eliminates the date granularity problem
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from difflib import SequenceMatcher
from collections import defaultdict


def fuzzy_match_score(str1: str, str2: str) -> float:
    """Calculate fuzzy match score between two strings (0-1)."""
    if not str1 or not str2:
        return 0.0

    s1 = str1.lower().strip()
    s2 = str2.lower().strip()

    if s1 == s2:
        return 1.0

    return SequenceMatcher(None, s1, s2).ratio()


def match_by_issue(human_csv: Path, auto_csv: Path, output_csv: Path,
                   port_threshold: float = 0.85, commodity_threshold: float = 0.80):
    """
    Match automated records to human ground truth by publication issue.

    Args:
        human_csv: Ground truth CSV
        auto_csv: Automated OCR CSV
        output_csv: Matched pairs output
        port_threshold: Minimum similarity for port matching
        commodity_threshold: Minimum similarity for commodity matching
    """
    csv.field_size_limit(1000000)

    print("Loading automated records...")
    auto_by_issue = defaultdict(list)
    auto_records = []

    with open(auto_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            row['auto_id'] = i
            auto_records.append(row)
            # Group by issue (YYYYMMDD from source_file)
            issue = row['source_file'][:8]
            auto_by_issue[issue].append(row)

    print(f"  Loaded {len(auto_records):,} automated records")
    print(f"  Grouped into {len(auto_by_issue)} issues")

    print("\nLoading human ground truth...")
    human_records = []

    with open(human_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            row['human_id'] = i
            human_records.append(row)

    print(f"  Loaded {len(human_records):,} human records")

    # Map human dates to publication issues
    print("\nMapping human dates to publication issues...")

    # Get publication dates from automated data
    pub_dates = {}
    for issue, records in auto_by_issue.items():
        if records:
            issue_date = datetime.strptime(issue, '%Y%m%d')
            pub_dates[issue] = issue_date

    # Assign human records to issues (within 14 days)
    human_by_issue = defaultdict(list)

    for row in human_records:
        try:
            human_date = datetime.strptime(row['date'], '%Y-%m-%d')

            # Find closest publication issue
            closest_issue = None
            min_diff = 999

            for issue, pub_date in pub_dates.items():
                diff = abs((human_date - pub_date).days)
                if diff < min_diff:
                    min_diff = diff
                    closest_issue = issue

            # Only assign if within 14 days
            if min_diff <= 14:
                row['assigned_issue'] = closest_issue
                row['days_from_issue'] = min_diff
                human_by_issue[closest_issue].append(row)
        except:
            pass

    print(f"  Assigned {sum(len(recs) for recs in human_by_issue.values()):,} human records to issues")

    # Match within each issue
    print(f"\nMatching records by issue...")
    print(f"  Port similarity threshold: {port_threshold:.0%}")
    print(f"  Commodity similarity threshold: {commodity_threshold:.0%}")

    matches = []
    matched_human_ids = set()
    matched_auto_ids = set()

    issues_processed = 0

    for issue in sorted(auto_by_issue.keys()):
        auto_recs = auto_by_issue[issue]
        human_recs = human_by_issue.get(issue, [])

        if not human_recs:
            # No human data for this issue - mark all auto as unmatched
            for auto_rec in auto_recs:
                matches.append({
                    'match_type': 'unmatched_auto',
                    'issue': issue,
                    'auto_id': auto_rec['auto_id'],
                    'human_id': None,
                    'auto_port': auto_rec.get('origin_port', ''),
                    'auto_commodity': auto_rec.get('commodity', ''),
                    'auto_quantity': auto_rec.get('quantity', ''),
                    'auto_unit': auto_rec.get('unit', ''),
                    'human_date': '',
                    'human_port': '',
                    'human_product': '',
                    'human_quantity': '',
                    'human_unit': '',
                    'port_score': 0.0,
                    'commodity_score': 0.0,
                    'total_score': 0.0
                })
            continue

        issues_processed += 1

        # Match within this issue
        for auto_rec in auto_recs:
            auto_port = auto_rec.get('origin_port', '')
            auto_commodity = auto_rec.get('commodity', '')

            # Find candidates
            candidates = []
            for human_rec in human_recs:
                if human_rec['human_id'] in matched_human_ids:
                    continue  # Already matched

                human_port = human_rec.get('origin_port', '')
                human_product = human_rec.get('product', '')

                # Calculate similarity scores
                port_score = fuzzy_match_score(auto_port, human_port)
                commodity_score = fuzzy_match_score(auto_commodity, human_product)

                # Check thresholds
                if port_score >= port_threshold and commodity_score >= commodity_threshold:
                    total_score = (port_score + commodity_score) / 2
                    candidates.append({
                        'human_rec': human_rec,
                        'port_score': port_score,
                        'commodity_score': commodity_score,
                        'total_score': total_score
                    })

            # Create match record
            if len(candidates) == 0:
                # Unmatched automated record
                matches.append({
                    'match_type': 'unmatched_auto',
                    'issue': issue,
                    'auto_id': auto_rec['auto_id'],
                    'human_id': None,
                    'auto_port': auto_port,
                    'auto_commodity': auto_commodity,
                    'auto_quantity': auto_rec.get('quantity', ''),
                    'auto_unit': auto_rec.get('unit', ''),
                    'human_date': '',
                    'human_port': '',
                    'human_product': '',
                    'human_quantity': '',
                    'human_unit': '',
                    'port_score': 0.0,
                    'commodity_score': 0.0,
                    'total_score': 0.0
                })

            elif len(candidates) == 1:
                # 1:1 match
                candidate = candidates[0]
                human_rec = candidate['human_rec']

                matches.append({
                    'match_type': '1:1',
                    'issue': issue,
                    'auto_id': auto_rec['auto_id'],
                    'human_id': human_rec['human_id'],
                    'auto_port': auto_port,
                    'auto_commodity': auto_commodity,
                    'auto_quantity': auto_rec.get('quantity', ''),
                    'auto_unit': auto_rec.get('unit', ''),
                    'human_date': human_rec.get('date', ''),
                    'human_port': human_rec.get('origin_port', ''),
                    'human_product': human_rec.get('product', ''),
                    'human_quantity': human_rec.get('quantity', ''),
                    'human_unit': human_rec.get('unit', ''),
                    'port_score': candidate['port_score'],
                    'commodity_score': candidate['commodity_score'],
                    'total_score': candidate['total_score']
                })
                matched_human_ids.add(human_rec['human_id'])
                matched_auto_ids.add(auto_rec['auto_id'])

            else:
                # 1:many match - take best
                best = max(candidates, key=lambda x: x['total_score'])
                human_rec = best['human_rec']

                matches.append({
                    'match_type': f'1:many (best of {len(candidates)})',
                    'issue': issue,
                    'auto_id': auto_rec['auto_id'],
                    'human_id': human_rec['human_id'],
                    'auto_port': auto_port,
                    'auto_commodity': auto_commodity,
                    'auto_quantity': auto_rec.get('quantity', ''),
                    'auto_unit': auto_rec.get('unit', ''),
                    'human_date': human_rec.get('date', ''),
                    'human_port': human_rec.get('origin_port', ''),
                    'human_product': human_rec.get('product', ''),
                    'human_quantity': human_rec.get('quantity', ''),
                    'human_unit': human_rec.get('unit', ''),
                    'port_score': best['port_score'],
                    'commodity_score': best['commodity_score'],
                    'total_score': best['total_score']
                })
                matched_human_ids.add(human_rec['human_id'])
                matched_auto_ids.add(auto_rec['auto_id'])

    # Find unmatched human records
    for human_rec in human_records:
        if human_rec['human_id'] not in matched_human_ids:
            issue = human_rec.get('assigned_issue', 'unknown')
            matches.append({
                'match_type': 'unmatched_human',
                'issue': issue,
                'auto_id': None,
                'human_id': human_rec['human_id'],
                'auto_port': '',
                'auto_commodity': '',
                'auto_quantity': '',
                'auto_unit': '',
                'human_date': human_rec.get('date', ''),
                'human_port': human_rec.get('origin_port', ''),
                'human_product': human_rec.get('product', ''),
                'human_quantity': human_rec.get('quantity', ''),
                'human_unit': human_rec.get('unit', ''),
                'port_score': 0.0,
                'commodity_score': 0.0,
                'total_score': 0.0
            })

    # Write matched pairs to CSV
    print(f"\nWriting {len(matches):,} matched pairs...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'match_type', 'issue', 'auto_id', 'human_id',
            'auto_port', 'human_port', 'port_score',
            'auto_commodity', 'human_product', 'commodity_score',
            'auto_quantity', 'human_quantity',
            'auto_unit', 'human_unit',
            'human_date', 'total_score'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

    # Statistics
    match_types = {}
    for m in matches:
        mt = m['match_type']
        match_types[mt] = match_types.get(mt, 0) + 1

    print("\n" + "=" * 80)
    print("MATCHING COMPLETE")
    print("=" * 80)
    print(f"\nTotal matched pairs: {len(matches):,}")
    print(f"Issues processed: {issues_processed}")
    print("\nMatch types:")
    for match_type in sorted(match_types.keys()):
        count = match_types[match_type]
        pct = 100 * count / len(matches)
        print(f"  {match_type:30s}: {count:6,} ({pct:5.1f}%)")

    # Calculate precision and recall
    true_positives = sum(1 for m in matches if m['match_type'].startswith('1:'))
    auto_total = len(auto_records)
    human_total = len(human_records)

    precision = 100 * true_positives / auto_total if auto_total > 0 else 0
    recall = 100 * true_positives / human_total if human_total > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print("\nMatching Performance:")
    print(f"  Precision: {precision:.1f}% ({true_positives}/{auto_total})")
    print(f"  Recall:    {recall:.1f}% ({true_positives}/{human_total})")
    print(f"  F1 Score:  {f1:.1f}")

    print(f"\nOutput: {output_csv}")
    print("=" * 80)


def main():
    print("=" * 80)
    print("CARGO RECORD MATCHING BY ISSUE - 1883 LONDON")
    print("=" * 80)

    base_dir = Path("/home/jic823/TTJ Forest of Numbers/validation")

    human_csv = base_dir / "ground_truth_1883_london_filtered.csv"
    auto_csv = base_dir / "automated_1883_london_fixed.csv"
    output_csv = base_dir / "matched_pairs_1883_by_issue.csv"

    print(f"\nInputs:")
    print(f"  Human ground truth: {human_csv}")
    print(f"  Automated OCR:      {auto_csv}")
    print(f"\nOutput:")
    print(f"  Matched pairs:      {output_csv}")
    print()

    match_by_issue(
        human_csv,
        auto_csv,
        output_csv,
        port_threshold=0.85,
        commodity_threshold=0.80
    )


if __name__ == '__main__':
    main()
