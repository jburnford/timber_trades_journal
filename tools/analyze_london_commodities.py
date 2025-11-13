#!/usr/bin/env python3
"""
Analyze London commodity imports with temporal trends.
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("LONDON COMMODITY IMPORT ANALYSIS")
print("="*80)

base_dir = Path("/home/jic823/TTJ Forest of Numbers")

# Load cleaned cargo data
print("\n1. Loading cleaned cargo data...")
df = pd.read_csv(base_dir / "final_output" / "ttj_cargo_details_cleaned.csv")
print(f"   Total cargo records: {len(df):,}")

# Filter for London destinations
print("\n2. Filtering for London imports...")
london = df[df['destination_port'] == 'LONDON'].copy()
print(f"   London cargo records: {len(london):,} ({100*len(london)/len(df):.1f}%)")

# Remove null commodities
london_clean = london[london['commodity'].notna()].copy()
print(f"   London records with valid commodities: {len(london_clean):,}")

# Basic statistics
print("\n3. London import statistics...")
print(f"   Unique commodities: {london_clean['commodity'].nunique():,}")
print(f"   Unique origin ports: {london_clean['origin_port'].nunique():,}")
print(f"   Year range: {int(london_clean['arrival_year'].min())} - {int(london_clean['arrival_year'].max())}")

# Save London-specific dataset
output_file = base_dir / "analysis" / "london_supply_network" / "london_commodities.csv"
output_file.parent.mkdir(parents=True, exist_ok=True)
london_clean.to_csv(output_file, index=False)
print(f"\n✅ Saved London commodity data: {output_file}")

# ============================================================================
# OVERALL COMMODITY ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("TOP 20 COMMODITIES IMPORTED TO LONDON (All Years)")
print("="*80)

top_commodities = london_clean['commodity'].value_counts().head(20)
for i, (commodity, count) in enumerate(top_commodities.items(), 1):
    pct = 100 * count / len(london_clean)
    print(f"  {i:2d}. {commodity:40} {count:>7,} ({pct:>5.1f}%)")

# ============================================================================
# TOP ORIGIN PORTS FOR LONDON
# ============================================================================
print("\n" + "="*80)
print("TOP 20 ORIGIN PORTS SUPPLYING LONDON (All Years)")
print("="*80)

top_origins = london_clean['origin_port'].value_counts().head(20)
for i, (port, count) in enumerate(top_origins.items(), 1):
    pct = 100 * count / len(london_clean)
    print(f"  {i:2d}. {port:40} {count:>7,} ({pct:>5.1f}%)")

# ============================================================================
# TEMPORAL TRENDS
# ============================================================================
print("\n" + "="*80)
print("TEMPORAL TRENDS: TOP 10 COMMODITIES BY YEAR")
print("="*80)

# Get top 10 commodities overall
top_10_commodities = london_clean['commodity'].value_counts().head(10).index.tolist()

# Create annual commodity counts
annual_commodities = london_clean[london_clean['commodity'].isin(top_10_commodities)].groupby(
    ['arrival_year', 'commodity']
).size().reset_index(name='count')

# Pivot for easier reading
annual_pivot = annual_commodities.pivot(
    index='arrival_year', 
    columns='commodity', 
    values='count'
).fillna(0).astype(int)

# Save annual trends
trends_file = base_dir / "analysis" / "london_supply_network" / "london_commodity_trends.csv"
annual_pivot.to_csv(trends_file)
print(f"\n✅ Saved annual trends: {trends_file}")

# Show sample years
print("\nSample years (1874, 1880, 1890, 1899):")
print("-"*80)
sample_years = [1874, 1880, 1890, 1899]
for year in sample_years:
    if year in annual_pivot.index:
        print(f"\n{year}:")
        year_data = annual_pivot.loc[year].sort_values(ascending=False)
        for commodity, count in year_data.head(10).items():
            if count > 0:
                print(f"  {commodity:30} {count:>6,}")

# ============================================================================
# COMMODITY-PORT PAIRS
# ============================================================================
print("\n" + "="*80)
print("TOP COMMODITY-ORIGIN PAIRS FOR LONDON")
print("="*80)

commodity_port = london_clean.groupby(
    ['commodity', 'origin_port']
).size().reset_index(name='count').sort_values('count', ascending=False)

commodity_port_file = base_dir / "analysis" / "london_supply_network" / "london_commodity_origins.csv"
commodity_port.to_csv(commodity_port_file, index=False)
print(f"\n✅ Saved commodity-origin pairs: {commodity_port_file}")

print("\nTop 20 commodity-origin pairs:")
print("-"*80)
for i, row in commodity_port.head(20).iterrows():
    print(f"  {row['commodity']:30} from {row['origin_port']:25} {row['count']:>6,}")

# ============================================================================
# GROWTH/DECLINE ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("COMMODITY GROWTH/DECLINE ANALYSIS")
print("="*80)

# Compare early years (1874-1880) vs late years (1893-1899)
early_years = london_clean[london_clean['arrival_year'].between(1874, 1880)]
late_years = london_clean[london_clean['arrival_year'].between(1893, 1899)]

early_counts = early_years['commodity'].value_counts()
late_counts = late_years['commodity'].value_counts()

# Calculate growth for top commodities
growth_data = []
for commodity in top_10_commodities:
    early = early_counts.get(commodity, 0)
    late = late_counts.get(commodity, 0)
    if early > 0:
        growth_pct = ((late - early) / early) * 100
    else:
        growth_pct = 0 if late == 0 else 999
    growth_data.append({
        'commodity': commodity,
        'early_period': early,
        'late_period': late,
        'change': late - early,
        'growth_pct': growth_pct
    })

growth_df = pd.DataFrame(growth_data).sort_values('growth_pct', ascending=False)

print("\nCommodity changes (1874-1880 vs 1893-1899):")
print("-"*80)
print(f"{'Commodity':30} {'Early':>8} {'Late':>8} {'Change':>8} {'Growth':>8}")
print("-"*80)
for _, row in growth_df.iterrows():
    print(f"{row['commodity']:30} {row['early_period']:>8,} {row['late_period']:>8,} {row['change']:>8,} {row['growth_pct']:>7.0f}%")

# Save growth analysis
growth_file = base_dir / "analysis" / "london_supply_network" / "london_commodity_growth.csv"
growth_df.to_csv(growth_file, index=False)
print(f"\n✅ Saved growth analysis: {growth_file}")

# ============================================================================
# GEOGRAPHIC PATTERNS
# ============================================================================
print("\n" + "="*80)
print("GEOGRAPHIC SUPPLY PATTERNS")
print("="*80)

# For top 5 commodities, show top origins
top_5_commodities = london_clean['commodity'].value_counts().head(5).index

for commodity in top_5_commodities:
    commodity_data = london_clean[london_clean['commodity'] == commodity]
    top_origins = commodity_data['origin_port'].value_counts().head(5)
    
    print(f"\n{commodity.upper()}:")
    print("-"*60)
    total = len(commodity_data)
    for port, count in top_origins.items():
        pct = 100 * count / total
        print(f"  {port:40} {count:>6,} ({pct:>5.1f}%)")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print("\nFiles created:")
print("  1. london_commodities.csv - Full London cargo dataset")
print("  2. london_commodity_trends.csv - Annual trends by commodity")
print("  3. london_commodity_origins.csv - Commodity-origin pairs")
print("  4. london_commodity_growth.csv - Growth analysis")
print("="*80)
