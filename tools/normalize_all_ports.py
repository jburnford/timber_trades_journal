#!/usr/bin/env python3
"""Normalize both origin and destination port names"""

import pandas as pd
import json
import sys

print("="*80)
print("PORT NAME NORMALIZATION")
print("="*80)

# Load shipments
print("\n1. Loading shipments...")
df = pd.read_csv('../final_output/ttj_shipments.csv')
print(f"   Total shipments: {len(df):,}")

# Load origin normalization rules
print("\n2. Loading origin normalization rules...")
with open('../reference_data/manual_port_matches.json', 'r') as f:
    data = json.load(f)
    origin_rules = data.get('matches', data)  # Handle both formats
print(f"   Origin rules loaded: {len(origin_rules)}")

# Load destination normalization rules
print("\n3. Loading destination normalization rules...")
with open('../reference_data/british_port_manual_mappings_final.json', 'r') as f:
    data = json.load(f)
    dest_rules = data.get('matches', data)
print(f"   Destination manual rules: {len(dest_rules)}")

# Load fuzzy matches
print("\n4. Loading fuzzy match rules...")
with open('../reference_data/british_ports_case_fuzzy_matches.json', 'r') as f:
    data = json.load(f)
    fuzzy_rules = data.get('matches', data)
print(f"   Fuzzy rules loaded: {len(fuzzy_rules)}")

# Combine destination rules (fuzzy matches override manual if there's conflict)
dest_rules.update(fuzzy_rules)
print(f"   Total destination rules: {len(dest_rules)}")

# Apply origin normalization
print("\n5. Normalizing origin ports...")
df['origin_port_original'] = df['origin_port']
df['origin_port_normalized'] = False

origin_count = 0
origin_changes = []

for variant, canonical in origin_rules.items():
    mask = df['origin_port'] == variant
    if mask.any():
        count = mask.sum()
        df.loc[mask, 'origin_port'] = canonical
        df.loc[mask, 'origin_port_normalized'] = True
        origin_count += count
        origin_changes.append((variant, canonical, count))

# Sort and show top changes
origin_changes.sort(key=lambda x: x[2], reverse=True)
print(f"\n   Top 10 origin normalizations:")
for variant, canonical, count in origin_changes[:10]:
    print(f"      {variant:30} → {canonical:30} {count:>7,} ships")

# Apply destination normalization
print("\n6. Normalizing destination ports...")
df['destination_port_original'] = df['destination_port']
df['destination_port_normalized'] = False

dest_count = 0
dest_changes = []

for variant, canonical in dest_rules.items():
    mask = df['destination_port'] == variant
    if mask.any():
        count = mask.sum()
        df.loc[mask, 'destination_port'] = canonical
        df.loc[mask, 'destination_port_normalized'] = True
        dest_count += count
        dest_changes.append((variant, canonical, count))

# Sort and show top changes
dest_changes.sort(key=lambda x: x[2], reverse=True)
print(f"\n   Top 10 destination normalizations:")
for variant, canonical, count in dest_changes[:10]:
    print(f"      {variant:30} → {canonical:30} {count:>7,} ships")

# Save normalized data
output_file = '../parsed_output/ttj_shipments_normalized.csv'
print(f"\n7. Saving normalized data...")
df.to_csv(output_file, index=False)

# Generate report
report_file = '../parsed_output/port_normalization_report.txt'
print(f"\n8. Generating report...")

with open(report_file, 'w') as f:
    f.write("="*80 + "\n")
    f.write("PORT NORMALIZATION REPORT\n")
    f.write("="*80 + "\n\n")

    f.write(f"Total shipments processed: {len(df):,}\n\n")

    f.write("ORIGIN PORT NORMALIZATION\n")
    f.write("-"*80 + "\n")
    f.write(f"Total origin ports normalized: {origin_count:,} ships ({origin_count/len(df)*100:.1f}%)\n")
    f.write(f"Normalization rules applied: {len([x for x in origin_changes if x[2] > 0])}\n\n")

    f.write("Top origin port normalizations:\n")
    for variant, canonical, count in origin_changes[:20]:
        f.write(f"  {variant:35} → {canonical:35} {count:>7,} ships\n")

    f.write("\n" + "="*80 + "\n")
    f.write("DESTINATION PORT NORMALIZATION\n")
    f.write("-"*80 + "\n")
    f.write(f"Total destination ports normalized: {dest_count:,} ships ({dest_count/len(df)*100:.1f}%)\n")
    f.write(f"Normalization rules applied: {len([x for x in dest_changes if x[2] > 0])}\n\n")

    f.write("Top destination port normalizations:\n")
    for variant, canonical, count in dest_changes[:20]:
        f.write(f"  {variant:35} → {canonical:35} {count:>7,} ships\n")

# Print summary
print("\n" + "="*80)
print("NORMALIZATION SUMMARY")
print("="*80)
print(f"Total shipments:              {len(df):>10,}")
print(f"\nOrigin ports normalized:      {origin_count:>10,} ships ({origin_count/len(df)*100:.1f}%)")
print(f"  Rules triggered:            {len([x for x in origin_changes if x[2] > 0]):>10}")
print(f"\nDestination ports normalized: {dest_count:>10,} ships ({dest_count/len(df)*100:.1f}%)")
print(f"  Rules triggered:            {len([x for x in dest_changes if x[2] > 0]):>10}")
print(f"\n✅ Saved normalized data to: {output_file}")
print(f"✅ Saved report to: {report_file}")
print("="*80)
