#!/usr/bin/env python3
"""
Match automated cargo records to human ground truth.

Matching strategy:
- Primary key: Date + Origin Port + Commodity (fuzzy)
- Handles 1:1, 1:many, many:1 relationships
- Uses fuzzy string matching for OCR tolerance
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set
from difflib import SequenceMatcher


def normalize_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD format."""
    if not date_str:
        return ''

    # Already in YYYY-MM-DD format
    if isinstance(date_str, str) and len(date_str) == 10 and date_str[4] == '-':
        return date_str

    # Try to parse other formats
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except:
        pass

    return date_str


def fuzzy_match_score(str1: str, str2: str) -> float:
    """
    Calculate fuzzy match score between two strings (0-1).
    Uses SequenceMatcher for similarity.
    """
    if not str1 or not str2:
        return 0.0

    # Normalize: lowercase, strip
    s1 = str1.lower().strip()
    s2 = str2.lower().strip()

    if s1 == s2:
        return 1.0

    return SequenceMatcher(None, s1, s2).ratio()


def create_match_key(date: str, port: str, commodity: str, fuzzy: bool = False) -> Tuple:
    """
    Create matching key from record fields.

    Args:
        date: YYYY-MM-DD format
        port: Origin port name
        commodity: Commodity/product name
        fuzzy: If True, normalize more aggressively for fuzzy matching

    Returns:
        Tuple for use as dict key (exact) or comparison (fuzzy)
    """
    if fuzzy:
        # Normalize for fuzzy matching
        date_norm = date.strip() if date else ''
        port_norm = port.lower().strip() if port else ''
        commodity_norm = commodity.lower().strip() if commodity else ''
        return (date_norm, port_norm, commodity_norm)
    else:
        # Exact matching (case-insensitive)
        return (
            date.strip() if date else '',
            port.lower().strip() if port else '',
            commodity.lower().strip() if commodity else ''
        )


def match_records(human_csv: Path, auto_csv: Path, output_csv: Path,
                 port_threshold: float = 0.85, commodity_threshold: float = 0.80,
                 date_window_days: int = 14):
    """
    Match automated records to human ground truth.

    Args:
        human_csv: Ground truth CSV
        auto_csv: Automated OCR CSV
        output_csv: Matched pairs output
        port_threshold: Minimum similarity for port matching
        commodity_threshold: Minimum similarity for commodity matching
        date_window_days: Number of days +/- to consider for date matching
    """
    csv.field_size_limit(1000000)

    print("Loading human ground truth...")
    human_records = []
    with open(human_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            row['human_id'] = i
            human_records.append(row)

    print(f"  Loaded {len(human_records):,} human records")

    print("\nLoading automated records...")
    auto_records = []
    with open(auto_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            row['auto_id'] = i
            auto_records.append(row)

    print(f"  Loaded {len(auto_records):,} automated records")

    print("\nMatching records...")
    print(f"  Port similarity threshold: {port_threshold:.0%}")
    print(f"  Commodity similarity threshold: {commodity_threshold:.0%}")
    print(f"  Date window: ±{date_window_days} days")

    matches = []
    matched_human_ids = set()
    matched_auto_ids = set()

    # Try to match each automated record to human records
    for auto_rec in auto_records:
        auto_date = normalize_date(auto_rec.get('hybrid_arrival_date', ''))
        auto_port = auto_rec.get('origin_port', '')
        auto_commodity = auto_rec.get('commodity', '')

        # Find candidates within date window
        candidates = []
        for human_rec in human_records:
            human_date = normalize_date(human_rec.get('date', ''))

            # Check if dates are within window
            if auto_date and human_date:
                try:
                    from datetime import datetime
                    auto_dt = datetime.strptime(auto_date, '%Y-%m-%d')
                    human_dt = datetime.strptime(human_date, '%Y-%m-%d')
                    date_diff = abs((auto_dt - human_dt).days)

                    if date_diff > date_window_days:
                        continue
                except:
                    # If date parsing fails, skip
                    continue
            elif auto_date != human_date:
                # If either date is missing, require exact match
                continue

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
                    'total_score': total_score,
                    'date_diff': date_diff
                })

        # Determine match type and create match record(s)
        if len(candidates) == 0:
            # Unmatched automated record
            matches.append({
                'match_type': 'unmatched_auto',
                'auto_id': auto_rec['auto_id'],
                'human_id': None,
                'auto_date': auto_date,
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
                'total_score': 0.0,
                'date_diff_days': 999
            })

        elif len(candidates) == 1:
            # 1:1 match
            candidate = candidates[0]
            human_rec = candidate['human_rec']

            matches.append({
                'match_type': '1:1',
                'auto_id': auto_rec['auto_id'],
                'human_id': human_rec['human_id'],
                'auto_date': auto_date,
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
                'total_score': candidate['total_score'],
                'date_diff_days': candidate['date_diff']
            })
            matched_human_ids.add(human_rec['human_id'])
            matched_auto_ids.add(auto_rec['auto_id'])

        else:
            # 1:many match - automated matched multiple human records
            # Take best match but flag as ambiguous
            best = max(candidates, key=lambda x: x['total_score'])
            human_rec = best['human_rec']

            matches.append({
                'match_type': f'1:many (best of {len(candidates)})',
                'auto_id': auto_rec['auto_id'],
                'human_id': human_rec['human_id'],
                'auto_date': auto_date,
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
                'total_score': best['total_score'],
                'date_diff_days': best['date_diff']
            })
            matched_human_ids.add(human_rec['human_id'])
            matched_auto_ids.add(auto_rec['auto_id'])

    # Find unmatched human records
    for human_rec in human_records:
        if human_rec['human_id'] not in matched_human_ids:
            matches.append({
                'match_type': 'unmatched_human',
                'auto_id': None,
                'human_id': human_rec['human_id'],
                'auto_date': '',
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
                'total_score': 0.0,
                'date_diff_days': 999
            })

    # Write matched pairs to CSV
    print(f"\nWriting {len(matches):,} matched pairs...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'match_type', 'auto_id', 'human_id',
            'auto_date', 'human_date', 'date_diff_days',
            'auto_port', 'human_port', 'port_score',
            'auto_commodity', 'human_product', 'commodity_score',
            'auto_quantity', 'human_quantity',
            'auto_unit', 'human_unit',
            'total_score'
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
    print("CARGO RECORD MATCHING - 1883 LONDON")
    print("=" * 80)

    base_dir = Path("/home/jic823/TTJ Forest of Numbers/validation")

    human_csv = base_dir / "ground_truth_1883_london_filtered.csv"
    auto_csv = base_dir / "automated_1883_london_fixed.csv"
    output_csv = base_dir / "matched_pairs_1883_fixed.csv"

    print(f"\nInputs:")
    print(f"  Human ground truth: {human_csv}")
    print(f"  Automated OCR:      {auto_csv}")
    print(f"\nOutput:")
    print(f"  Matched pairs:      {output_csv}")
    print()

    match_records(
        human_csv,
        auto_csv,
        output_csv,
        port_threshold=0.85,
        commodity_threshold=0.80,
        date_window_days=14
    )


if __name__ == '__main__':
    main()
