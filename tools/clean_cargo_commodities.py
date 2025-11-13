#!/usr/bin/env python3
"""
Clean obvious errors from cargo commodities.
"""

import pandas as pd
import re
from pathlib import Path

print("="*80)
print("CLEANING CARGO COMMODITIES")
print("="*80)

base_dir = Path("/home/jic823/TTJ Forest of Numbers")

# Load enriched cargo
print("\n1. Loading enriched cargo data...")
df = pd.read_csv(base_dir / "final_output" / "ttj_cargo_details_enriched.csv")
print(f"   Total records: {len(df):,}")

original_df = df.copy()

# Track changes
stats = {
    'long_commodities': 0,
    'prices': 0,
    'dates_fragments': 0,
    'merchant_patterns': 0,
    'props_normalized': 0
}

print("\n2. Removing parsing errors...")

# Remove very long commodities (>50 chars) - these are parsing errors
print("   - Long commodities (>50 chars)...")
df['commodity_len'] = df['commodity'].astype(str).str.len()
long_mask = df['commodity_len'] > 50
stats['long_commodities'] = long_mask.sum()
df.loc[long_mask, 'commodity'] = None

# Remove price entries
print("   - Price entries...")
price_pattern = r'^£\d+$|^\d+s\s*\d*d?$'
price_mask = df['commodity'].astype(str).str.match(price_pattern, na=False)
stats['prices'] = price_mask.sum()
df.loc[price_mask, 'commodity'] = None

# Remove date fragments and obvious non-commodities
print("   - Date/fragment entries...")
fragment_patterns = [
    r'.*\b(january|february|march|april|may|june|july|august|september|october|november|december)\b.*',
    r'^\d+th$',
    r'^/\d+$',
    r'^\d+r\s',
]
for pattern in fragment_patterns:
    mask = df['commodity'].astype(str).str.match(pattern, case=False, na=False)
    stats['dates_fragments'] += mask.sum()
    df.loc[mask, 'commodity'] = None

# Remove merchant-like patterns
print("   - Merchant-like patterns...")
merchant_pattern = r'^.*-co\..*$|^.*\bco\.\s*$'
merchant_mask = df['commodity'].astype(str).str.match(merchant_pattern, case=False, na=False)
stats['merchant_patterns'] = merchant_mask.sum()
df.loc[merchant_mask, 'commodity'] = None

print("\n3. Normalizing commodity names...")

# Normalize props variations
print("   - Props variations...")
props_variations = {
    'pit props': 'pit props',
    'pit-props': 'pit props',
    'pitprops': 'pit props',
}

for variant, canonical in props_variations.items():
    mask = df['commodity'].astype(str).str.lower() == variant.lower()
    count = mask.sum()
    if count > 0:
        df.loc[mask, 'commodity'] = canonical
        stats['props_normalized'] += count
        print(f"     '{variant}' → '{canonical}': {count:,} records")

# Drop the temporary length column
df = df.drop('commodity_len', axis=1)

# Save cleaned data
output_file = base_dir / "final_output" / "ttj_cargo_details_cleaned.csv"
print(f"\n4. Saving cleaned data...")
df.to_csv(output_file, index=False)
print(f"   ✅ Saved: {output_file}")

# Report
print("\n" + "="*80)
print("CLEANUP SUMMARY")
print("="*80)

print(f"\nTotal records: {len(df):,}")
print(f"\nRecords cleaned:")
print(f"  Long commodities removed:     {stats['long_commodities']:>7,}")
print(f"  Prices removed:               {stats['prices']:>7,}")
print(f"  Dates/fragments removed:      {stats['dates_fragments']:>7,}")
print(f"  Merchant patterns removed:    {stats['merchant_patterns']:>7,}")
print(f"  Props variations normalized:  {stats['props_normalized']:>7,}")

total_cleaned = sum(stats.values())
print(f"\nTotal changes:                  {total_cleaned:>7,} ({100*total_cleaned/len(df):.2f}%)")

# Before/after commodity counts
print("\n" + "-"*80)
print("TOP 20 COMMODITIES (After Cleaning)")
print("-"*80)
top_20 = df[df['commodity'].notna()]['commodity'].value_counts().head(20)
for i, (commodity, count) in enumerate(top_20.items(), 1):
    print(f"  {i:2d}. {str(commodity):40} {count:>7,} records")

# Check null commodities after cleaning
null_after = df['commodity'].isna().sum()
print(f"\nNull commodities after cleaning: {null_after:,} ({100*null_after/len(df):.2f}%)")

print("\n" + "="*80)
