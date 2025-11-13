#!/usr/bin/env python3
"""Analyze unmapped origin ports to categorize them"""

import pandas as pd
import re
from collections import Counter

# Load the geocoded database
print("Loading geocoded database...")
df = pd.read_csv('../final_output/ttj_shipments.csv')

# Find unmapped origin ports
print("Finding unmapped origin ports...")
unmapped = df[df['origin_latitude'].isna() | (df['origin_latitude'] == '')]

print(f"\nTotal shipments: {len(df):,}")
print(f"Unmapped origin ports: {len(unmapped):,} ({len(unmapped)/len(df)*100:.1f}%)")

# Count occurrences of each unmapped port
origin_counts = Counter(unmapped['origin_port'])
print(f"Unique unmapped port names: {len(origin_counts)}")

# Sort by frequency
sorted_ports = origin_counts.most_common()

# Categorize ports
def categorize_port(port_name):
    """Categorize a port name as real port, parsing error, or OCR error"""
    # Handle NaN and empty values
    if pd.isna(port_name):
        return 'empty'

    port = str(port_name).strip()

    if not port or port == '' or port == 'nan':
        return 'empty'

    # Parsing errors - these are clearly not ports
    parsing_error_patterns = [
        r'^[0-9]+$',  # Just numbers
        r'^[0-9]+\s*[a-z]?$',  # Numbers with single letter
        r'.*\bprice\b.*',
        r'.*\badvert.*',
        r'.*\btender.*',
        r'.*\bnotice.*',
        r'.*\bcreditor.*',
        r'.*\bsecured.*',
        r'.*\bmeeting.*',
        r'.*\bbuilding.*',
        r'.*\bsociety.*',
        r'.*\bdividend.*',
        r'.*\blist.*',
        r'.*\breport.*',
        r'.*\bcorrespond.*',
        r'^and$|^of$|^the$|^for$|^with$',  # Common words
        r'.*\bimport.*',
        r'.*\bexport.*',
        r'.*\btimber.*',
        r'.*\btrade.*',
        r'.*\bjournal.*',
        r'.*\bwood.*',
        r'.*\bdoor.*',
        r'.*\bjoinery.*',
    ]

    for pattern in parsing_error_patterns:
        if re.match(pattern, port, re.IGNORECASE):
            return 'parsing_error'

    # OCR errors - garbled text
    if len(port) <= 3 and not port.isupper():
        # Very short non-capitalized strings are likely OCR errors
        return 'ocr_error'

    # Check for excessive special characters
    special_char_ratio = sum(1 for c in port if not c.isalnum() and c != ' ') / len(port)
    if special_char_ratio > 0.3:
        return 'ocr_error'

    # Check for mixed case in strange ways (OCR artifact)
    if any(c.islower() and i > 0 and port[i-1].isupper() and port[i+1:i+2].isupper()
           for i, c in enumerate(port) if i < len(port)-1):
        return 'ocr_error'

    # If it looks like a real place name
    # Capitalized words, reasonable length, mostly letters
    if len(port) >= 4 and port[0].isupper() and sum(c.isalpha() for c in port) / len(port) > 0.7:
        return 'likely_real_port'

    # Check for known port-like patterns
    if any(pattern in port.lower() for pattern in ['port', 'bay', 'sound', 'fjord', 'creek', 'river']):
        return 'likely_real_port'

    return 'ambiguous'

# Categorize all unmapped ports
print("\nCategorizing unmapped ports...")
categorized = {}
category_stats = {
    'likely_real_port': {'count': 0, 'ships': 0, 'ports': []},
    'parsing_error': {'count': 0, 'ships': 0, 'ports': []},
    'ocr_error': {'count': 0, 'ships': 0, 'ports': []},
    'ambiguous': {'count': 0, 'ships': 0, 'ports': []},
    'empty': {'count': 0, 'ships': 0, 'ports': []}
}

for port, count in sorted_ports:
    category = categorize_port(port)
    categorized[port] = category
    category_stats[category]['count'] += count
    category_stats[category]['ships'] += count
    if len(category_stats[category]['ports']) < 50:  # Keep top 50 examples
        category_stats[category]['ports'].append((port, count))

# Print summary
print("\n" + "="*80)
print("UNMAPPED ORIGIN PORT ANALYSIS")
print("="*80)

print(f"\nTotal unmapped ships: {len(unmapped):,}")
print(f"Unique unmapped port names: {len(origin_counts):,}\n")

for category, stats in category_stats.items():
    pct = stats['count'] / len(unmapped) * 100 if len(unmapped) > 0 else 0
    print(f"{category.upper().replace('_', ' '):20} {stats['count']:>10,} ships ({pct:>5.1f}%)  "
          f"{len(stats['ports']):>5} unique ports")

# Show examples for each category
print("\n" + "="*80)
print("EXAMPLES BY CATEGORY")
print("="*80)

for category in ['likely_real_port', 'parsing_error', 'ocr_error', 'ambiguous']:
    stats = category_stats[category]
    if stats['ports']:
        print(f"\n{category.upper().replace('_', ' ')}:")
        print("-" * 80)
        print(f"{'Port Name':50} {'Ships':>10}")
        print("-" * 80)
        for port, count in stats['ports'][:30]:
            print(f"{str(port)[:50]:50} {count:>10,}")

# Calculate real port potential
print("\n" + "="*80)
print("POTENTIAL FOR FURTHER IMPROVEMENT")
print("="*80)

real_port_ships = category_stats['likely_real_port']['count']
ambiguous_ships = category_stats['ambiguous']['count']
current_coverage = (len(df) - len(unmapped)) / len(df) * 100
potential_coverage = (len(df) - len(unmapped) + real_port_ships) / len(df) * 100
max_potential = (len(df) - len(unmapped) + real_port_ships + ambiguous_ships) / len(df) * 100

print(f"\nCurrent origin coverage:           {current_coverage:.1f}%")
print(f"If all 'likely real ports' mapped: {potential_coverage:.1f}% (+{potential_coverage - current_coverage:.1f}%)")
print(f"If ambiguous ports also mapped:    {max_potential:.1f}% (+{max_potential - current_coverage:.1f}%)")

print(f"\n{'Category':<20} {'Ships':>10}  {'Research Effort':<30}")
print("-" * 70)
print(f"{'Likely real ports':<20} {real_port_ships:>10,}  {'Medium (2-3 hours)':<30}")
print(f"{'Ambiguous':<20} {ambiguous_ships:>10,}  {'High (4-6 hours)':<30}")
print(f"{'Parsing errors':<20} {category_stats['parsing_error']['count']:>10,}  {'N/A (not ports)':<30}")
print(f"{'OCR errors':<20} {category_stats['ocr_error']['count']:>10,}  {'N/A (not ports)':<30}")

# Save detailed results
print("\n" + "="*80)
print("Saving detailed results...")

results_df = pd.DataFrame([
    {
        'port_name': port,
        'ship_count': count,
        'category': categorized[port],
        'needs_research': categorized[port] in ['likely_real_port', 'ambiguous']
    }
    for port, count in sorted_ports
])

results_df.to_csv('unmapped_origin_ports_analysis.csv', index=False)
print(f"✅ Saved to: unmapped_origin_ports_analysis.csv")

# Summary by research priority
print("\n" + "="*80)
print("RESEARCH PRIORITY SUMMARY")
print("="*80)

high_priority = results_df[
    (results_df['category'] == 'likely_real_port') &
    (results_df['ship_count'] >= 50)
].sort_values('ship_count', ascending=False)

print(f"\nHIGH PRIORITY (likely real ports with 50+ ships): {len(high_priority)} ports, {high_priority['ship_count'].sum():,} ships")
if len(high_priority) > 0:
    print("\nTop candidates for research:")
    print(f"{'Port Name':40} {'Ships':>10}")
    print("-" * 52)
    for idx, row in high_priority.head(20).iterrows():
        print(f"{row['port_name']:40} {row['ship_count']:>10,}")

medium_priority = results_df[
    (results_df['category'] == 'likely_real_port') &
    (results_df['ship_count'] >= 10) &
    (results_df['ship_count'] < 50)
]

print(f"\nMEDIUM PRIORITY (likely real ports with 10-49 ships): {len(medium_priority)} ports, {medium_priority['ship_count'].sum():,} ships")

low_priority = results_df[
    (results_df['category'] == 'likely_real_port') &
    (results_df['ship_count'] < 10)
]

print(f"LOW PRIORITY (likely real ports with <10 ships): {len(low_priority)} ports, {low_priority['ship_count'].sum():,} ships")

print("\n" + "="*80)
