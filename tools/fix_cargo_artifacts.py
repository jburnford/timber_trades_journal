#!/usr/bin/env python3
"""
Quick fixes for obvious cargo parsing artifacts.
Focuses on high-impact, low-risk corrections.
"""

import csv
from pathlib import Path

def fix_commodity_artifacts(commodity: str) -> str:
    """
    Fix obvious commodity artifacts.

    Rules:
    1. Strip trailing &, &c (et cetera abbreviation)
    2. Remove standalone & artifacts
    3. Clean merchant bleed (names with &)
    """

    if not commodity:
        return commodity

    original = commodity

    # Rule 1: Strip trailing punctuation artifacts
    # "deals &c" → "deals"
    # "deals &" → "deals"
    commodity = commodity.rstrip('&').strip()
    if commodity.endswith('&c'):
        commodity = commodity[:-2].strip()

    # Rule 2: Standalone & artifacts → ERROR (empty)
    if commodity in ['&', '& co', '&c']:
        return ''

    # Rule 3: Merchant names bleeding in → ERROR
    # Pattern: ends with "& co" or "& son" etc.
    merchant_suffixes = ['& co', '& son', '& sons', '& atkinson', '& sim', '& wood']
    for suffix in merchant_suffixes:
        if commodity.endswith(suffix):
            # This is likely a merchant name, not a commodity
            return ''

    # Rule 4: Starts with & → ERROR
    if commodity.startswith('&'):
        return ''

    return commodity.strip()


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    input_file = base_dir / "final_output/authority_normalized/ttj_cargo_details_commodity_normalized.csv"
    output_file = base_dir / "final_output/authority_normalized/ttj_cargo_details_artifacts_fixed.csv"

    print("=" * 80)
    print("FIXING CARGO ARTIFACTS")
    print("=" * 80)

    stats = {
        'total': 0,
        'fixed': 0,
        'removed': 0,
        'unchanged': 0
    }

    fixes_applied = {}

    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', newline='', encoding='utf-8') as f_out:

        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            stats['total'] += 1

            if row['commodity']:
                original = row['commodity']
                fixed = fix_commodity_artifacts(original)

                if fixed != original:
                    if fixed == '':
                        stats['removed'] += 1
                    else:
                        stats['fixed'] += 1

                    # Track what was fixed
                    key = f"{original} → {fixed if fixed else 'REMOVED'}"
                    fixes_applied[key] = fixes_applied.get(key, 0) + 1

                    row['commodity'] = fixed
                else:
                    stats['unchanged'] += 1

            writer.writerow(row)

            if stats['total'] % 10000 == 0:
                print(f"  Processed {stats['total']:,} records...")

    print(f"\n{'='*80}")
    print("ARTIFACT FIXES COMPLETE")
    print(f"{'='*80}")
    print(f"Total records: {stats['total']:,}")
    print(f"Fixed: {stats['fixed']:,}")
    print(f"Removed (errors): {stats['removed']:,}")
    print(f"Unchanged: {stats['unchanged']:,}")

    if fixes_applied:
        print(f"\nTop 20 fixes applied:")
        print("-" * 80)
        for fix, count in sorted(fixes_applied.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {fix:60} {count:6,}x")

    print(f"\n✓ Output: {output_file}")
    print("=" * 80)


if __name__ == '__main__':
    main()
