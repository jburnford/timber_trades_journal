#!/usr/bin/env python3
"""
Create annual port statistics for mapping:
1. Export ports per year with coordinates
2. Import ports per year with coordinates
3. Export-import pairs per year with coordinates
"""

import pandas as pd
import sys

print("="*80)
print("CREATING ANNUAL PORT STATISTICS")
print("="*80)

# Load geocoded database
print("\n1. Loading geocoded database...")
df = pd.read_csv('../final_output/ttj_shipments.csv')
print(f"   Total shipments: {len(df):,}")

# Use arrival_year directly
print("\n2. Extracting year from arrival_year...")
df['year'] = pd.to_numeric(df['arrival_year'], errors='coerce')
df = df[df['year'].notna()]  # Remove records without valid years
print(f"   Records with valid years: {len(df):,}")
print(f"   Year range: {int(df['year'].min())} - {int(df['year'].max())}")

# ============================================================================
# 1. EXPORT PORTS PER YEAR
# ============================================================================
print("\n3. Creating export ports per year...")

# Filter to records with origin coordinates
export_df = df[
    (df['origin_latitude'].notna()) &
    (df['origin_latitude'] != '') &
    (df['origin_longitude'].notna()) &
    (df['origin_longitude'] != '')
].copy()

print(f"   Records with origin coordinates: {len(export_df):,}")

# Convert coordinates to numeric
export_df['origin_latitude'] = pd.to_numeric(export_df['origin_latitude'], errors='coerce')
export_df['origin_longitude'] = pd.to_numeric(export_df['origin_longitude'], errors='coerce')

# Remove any that failed conversion
export_df = export_df[
    (export_df['origin_latitude'].notna()) &
    (export_df['origin_longitude'].notna())
]

# Normalize port names to UPPERCASE to consolidate case variants
export_df['port_normalized'] = export_df['origin_port'].str.upper()

# Group by year and normalized port
export_stats = export_df.groupby(['year', 'port_normalized']).agg({
    'origin_port': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'origin_latitude': 'first',
    'origin_longitude': 'first',
    'ship_name': 'count'
}).reset_index()

export_stats.columns = ['year', 'port_normalized', 'port_name', 'latitude', 'longitude', 'ship_count']
export_stats = export_stats.drop(columns=['port_normalized'])

# Convert year to int
export_stats['year'] = export_stats['year'].astype(int)

# Sort by year and ship count
export_stats = export_stats.sort_values(['year', 'ship_count'], ascending=[True, False])

# Save to CSV
export_file = '../analysis/annual_port_statistics/export_ports_per_year.csv'
export_stats.to_csv(export_file, index=False)
print(f"   ✅ Saved: {export_file}")
print(f"   Total records: {len(export_stats):,}")
print(f"   Unique ports: {export_stats['port_name'].nunique():,}")
print(f"   Years covered: {int(export_stats['year'].min())} - {int(export_stats['year'].max())}")

# ============================================================================
# 2. IMPORT PORTS PER YEAR
# ============================================================================
print("\n4. Creating import ports per year...")

# Filter to records with destination coordinates
import_df = df[
    (df['destination_latitude'].notna()) &
    (df['destination_latitude'] != '') &
    (df['destination_longitude'].notna()) &
    (df['destination_longitude'] != '')
].copy()

print(f"   Records with destination coordinates: {len(import_df):,}")

# Convert coordinates to numeric
import_df['destination_latitude'] = pd.to_numeric(import_df['destination_latitude'], errors='coerce')
import_df['destination_longitude'] = pd.to_numeric(import_df['destination_longitude'], errors='coerce')

# Remove any that failed conversion
import_df = import_df[
    (import_df['destination_latitude'].notna()) &
    (import_df['destination_longitude'].notna())
]

# Normalize port names to UPPERCASE to consolidate case variants
import_df['port_normalized'] = import_df['destination_port'].str.upper()

# Group by year and normalized port
import_stats = import_df.groupby(['year', 'port_normalized']).agg({
    'destination_port': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'destination_latitude': 'first',
    'destination_longitude': 'first',
    'ship_name': 'count'
}).reset_index()

import_stats.columns = ['year', 'port_normalized', 'port_name', 'latitude', 'longitude', 'ship_count']
import_stats = import_stats.drop(columns=['port_normalized'])

# Convert year to int
import_stats['year'] = import_stats['year'].astype(int)

# Sort by year and ship count
import_stats = import_stats.sort_values(['year', 'ship_count'], ascending=[True, False])

# Save to CSV
import_file = '../analysis/annual_port_statistics/import_ports_per_year.csv'
import_stats.to_csv(import_file, index=False)
print(f"   ✅ Saved: {import_file}")
print(f"   Total records: {len(import_stats):,}")
print(f"   Unique ports: {import_stats['port_name'].nunique():,}")
print(f"   Years covered: {int(import_stats['year'].min())} - {int(import_stats['year'].max())}")

# ============================================================================
# 3. EXPORT-IMPORT PAIRS PER YEAR
# ============================================================================
print("\n5. Creating export-import pairs per year...")

# Filter to records with both coordinates
pairs_df = df[
    (df['origin_latitude'].notna()) &
    (df['origin_latitude'] != '') &
    (df['origin_longitude'].notna()) &
    (df['origin_longitude'] != '') &
    (df['destination_latitude'].notna()) &
    (df['destination_latitude'] != '') &
    (df['destination_longitude'].notna()) &
    (df['destination_longitude'] != '')
].copy()

print(f"   Records with both coordinates: {len(pairs_df):,}")

# Convert coordinates to numeric
pairs_df['origin_latitude'] = pd.to_numeric(pairs_df['origin_latitude'], errors='coerce')
pairs_df['origin_longitude'] = pd.to_numeric(pairs_df['origin_longitude'], errors='coerce')
pairs_df['destination_latitude'] = pd.to_numeric(pairs_df['destination_latitude'], errors='coerce')
pairs_df['destination_longitude'] = pd.to_numeric(pairs_df['destination_longitude'], errors='coerce')

# Remove any that failed conversion
pairs_df = pairs_df[
    (pairs_df['origin_latitude'].notna()) &
    (pairs_df['origin_longitude'].notna()) &
    (pairs_df['destination_latitude'].notna()) &
    (pairs_df['destination_longitude'].notna())
]

# Normalize port names to UPPERCASE to consolidate case variants
pairs_df['origin_normalized'] = pairs_df['origin_port'].str.upper()
pairs_df['destination_normalized'] = pairs_df['destination_port'].str.upper()

# Group by year and normalized port pair
pairs_stats = pairs_df.groupby([
    'year',
    'origin_normalized',
    'destination_normalized'
]).agg({
    'origin_port': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'origin_latitude': 'first',
    'origin_longitude': 'first',
    'destination_port': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'destination_latitude': 'first',
    'destination_longitude': 'first',
    'ship_name': 'count'
}).reset_index()

pairs_stats.columns = [
    'year',
    'origin_normalized',
    'destination_normalized',
    'origin_port',
    'origin_latitude',
    'origin_longitude',
    'destination_port',
    'destination_latitude',
    'destination_longitude',
    'ship_count'
]

# Drop normalized columns and reorder
pairs_stats = pairs_stats.drop(columns=['origin_normalized', 'destination_normalized'])
pairs_stats = pairs_stats[[
    'year',
    'origin_port',
    'origin_latitude',
    'origin_longitude',
    'destination_port',
    'destination_latitude',
    'destination_longitude',
    'ship_count'
]]

# Convert year to int
pairs_stats['year'] = pairs_stats['year'].astype(int)

# Sort by year and ship count
pairs_stats = pairs_stats.sort_values(['year', 'ship_count'], ascending=[True, False])

# Save to CSV
pairs_file = '../analysis/annual_port_statistics/export_import_pairs_per_year.csv'
pairs_stats.to_csv(pairs_file, index=False)
print(f"   ✅ Saved: {pairs_file}")
print(f"   Total records: {len(pairs_stats):,}")
print(f"   Unique origin ports: {pairs_stats['origin_port'].nunique():,}")
print(f"   Unique destination ports: {pairs_stats['destination_port'].nunique():,}")
print(f"   Years covered: {int(pairs_stats['year'].min())} - {int(pairs_stats['year'].max())}")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

print("\nEXPORT PORTS (Origins):")
print(f"  Total port-year combinations: {len(export_stats):,}")
print(f"  Unique ports: {export_stats['port_name'].nunique():,}")
print(f"  Total ships: {export_stats['ship_count'].sum():,}")

print("\nIMPORT PORTS (Destinations):")
print(f"  Total port-year combinations: {len(import_stats):,}")
print(f"  Unique ports: {import_stats['port_name'].nunique():,}")
print(f"  Total ships: {import_stats['ship_count'].sum():,}")

print("\nEXPORT-IMPORT PAIRS:")
print(f"  Total pair-year combinations: {len(pairs_stats):,}")
print(f"  Unique origin-destination pairs: {len(pairs_stats[['origin_port', 'destination_port']].drop_duplicates()):,}")
print(f"  Total ships in complete routes: {pairs_stats['ship_count'].sum():,}")

# Top 10 busiest export ports (all years combined)
print("\n" + "-"*80)
print("TOP 10 BUSIEST EXPORT PORTS (All Years Combined)")
print("-"*80)
top_exports = export_stats.groupby('port_name')['ship_count'].sum().sort_values(ascending=False).head(10)
for i, (port, count) in enumerate(top_exports.items(), 1):
    print(f"  {i:2d}. {port:40} {count:>7,} ships")

# Top 10 busiest import ports (all years combined)
print("\n" + "-"*80)
print("TOP 10 BUSIEST IMPORT PORTS (All Years Combined)")
print("-"*80)
top_imports = import_stats.groupby('port_name')['ship_count'].sum().sort_values(ascending=False).head(10)
for i, (port, count) in enumerate(top_imports.items(), 1):
    print(f"  {i:2d}. {port:40} {count:>7,} ships")

# Top 10 busiest routes (all years combined)
print("\n" + "-"*80)
print("TOP 10 BUSIEST ROUTES (All Years Combined)")
print("-"*80)
top_routes = pairs_stats.groupby(['origin_port', 'destination_port'])['ship_count'].sum().sort_values(ascending=False).head(10)
for i, ((origin, dest), count) in enumerate(top_routes.items(), 1):
    print(f"  {i:2d}. {origin:20} → {dest:20} {count:>7,} ships")

print("\n" + "="*80)
print("ALL FILES SAVED SUCCESSFULLY")
print("="*80)
