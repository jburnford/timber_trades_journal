#!/usr/bin/env python3
"""
Port Name Normalization Script
===============================
Applies manual port matching rules to normalize port names before geocoding.
This ensures one canonical label per port, enabling consistent grouping by
normalized names or coordinates.

Usage:
    python3 tools/normalize_port_names.py

Input:
    - parsed_output/ttj_shipments_final.csv
    - reference_data/manual_port_matches.json

Output:
    - parsed_output/ttj_shipments_normalized.csv (with normalized port names)
    - Creates backup of original file
"""

import pandas as pd
import json
import shutil
from pathlib import Path
from datetime import datetime

def load_normalization_rules(json_path):
    """Load port normalization rules from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['matches']

def normalize_port_names(df, normalization_rules):
    """
    Apply normalization rules to port names.

    Args:
        df: DataFrame with origin_port column
        normalization_rules: Dict mapping variant names to canonical names

    Returns:
        DataFrame with normalized port names and tracking columns
    """
    # Create a copy to avoid modifying original
    df_normalized = df.copy()

    # Add column to track which ports were normalized
    df_normalized['origin_port_original'] = df_normalized['origin_port']
    df_normalized['origin_port_normalized'] = False

    # Apply normalization rules
    normalized_count = 0
    for variant, canonical in normalization_rules.items():
        mask = df_normalized['origin_port'] == variant
        if mask.any():
            count = mask.sum()
            df_normalized.loc[mask, 'origin_port'] = canonical
            df_normalized.loc[mask, 'origin_port_normalized'] = True
            normalized_count += count
            print(f"  {variant:40s} → {canonical:40s} ({count:5d} ships)")

    return df_normalized, normalized_count

def generate_normalization_report(df_original, df_normalized, normalization_rules):
    """Generate a summary report of normalization changes."""

    # Count ships affected
    normalized_ships = df_normalized['origin_port_normalized'].sum()
    total_ships = len(df_normalized)

    # Count unique ports before/after
    unique_before = df_original['origin_port'].nunique()
    unique_after = df_normalized['origin_port'].nunique()

    # Count how many normalization rules were actually used
    rules_used = 0
    for variant in normalization_rules.keys():
        if (df_original['origin_port'] == variant).any():
            rules_used += 1

    report = f"""
PORT NAME NORMALIZATION REPORT
{'=' * 80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY STATISTICS
{'-' * 80}
Total ships in dataset:           {total_ships:>10,}
Ships with normalized ports:      {normalized_ships:>10,} ({normalized_ships/total_ships*100:.1f}%)
Ships with unchanged ports:       {total_ships - normalized_ships:>10,} ({(total_ships - normalized_ships)/total_ships*100:.1f}%)

Unique ports before normalization: {unique_before:>10,}
Unique ports after normalization:  {unique_after:>10,}
Reduction in unique port names:    {unique_before - unique_after:>10,}

Normalization rules defined:       {len(normalization_rules):>10,}
Normalization rules applied:       {rules_used:>10,}

TOP 10 NORMALIZED PORTS (by ship count)
{'-' * 80}
"""

    # Find top normalized ports
    normalized_only = df_normalized[df_normalized['origin_port_normalized']]
    top_normalized = normalized_only.groupby(['origin_port_original', 'origin_port']).size().reset_index(name='ship_count')
    top_normalized = top_normalized.sort_values('ship_count', ascending=False).head(10)

    for _, row in top_normalized.iterrows():
        report += f"{row['origin_port_original']:40s} → {row['origin_port']:40s} ({row['ship_count']:5,} ships)\n"

    report += f"\n{'=' * 80}\n"

    return report

def main():
    print("\nPORT NAME NORMALIZATION")
    print("=" * 80)

    # Define paths
    input_file = Path('parsed_output/ttj_shipments_final.csv')
    output_file = Path('parsed_output/ttj_shipments_normalized.csv')
    rules_file = Path('reference_data/manual_port_matches.json')
    report_file = Path('parsed_output/port_normalization_report.txt')

    # Backup original file if output would overwrite a different file
    if output_file.exists():
        backup_file = Path(f'parsed_output/ttj_shipments_normalized.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        print(f"\nBacking up existing file: {backup_file}")
        shutil.copy(output_file, backup_file)

    # Load data
    print(f"\nLoading shipments from: {input_file}")
    df = pd.read_csv(input_file)
    print(f"  Loaded {len(df):,} shipment records")

    # Load normalization rules
    print(f"\nLoading normalization rules from: {rules_file}")
    normalization_rules = load_normalization_rules(rules_file)
    print(f"  Loaded {len(normalization_rules)} normalization rules")

    # Apply normalization
    print(f"\nApplying port name normalization:")
    df_normalized, normalized_count = normalize_port_names(df, normalization_rules)
    print(f"\n  Total ships normalized: {normalized_count:,}")

    # Generate report
    print(f"\nGenerating normalization report...")
    report = generate_normalization_report(df, df_normalized, normalization_rules)

    # Save normalized data
    print(f"\nSaving normalized data to: {output_file}")
    df_normalized.to_csv(output_file, index=False)
    print(f"  Saved {len(df_normalized):,} records")

    # Save report
    print(f"\nSaving report to: {report_file}")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    # Print report
    print(report)

    print("\n✓ Port name normalization complete!")
    print(f"\nNext steps:")
    print(f"  1. Review report: {report_file}")
    print(f"  2. Use normalized file for geocoding: {output_file}")
    print(f"  3. Run: python3 tools/create_geocoded_database.py (with normalized file)")
    print()

if __name__ == '__main__':
    main()
