#!/usr/bin/env python3
"""
Create aggregate port statistics for entire period (1874-1899).
Total ships per port and port pairs, with coordinates.
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("CREATING AGGREGATE PORT STATISTICS (1874-1899)")
print("="*80)

base_dir = Path("/home/jic823/TTJ Forest of Numbers")

# Load geocoded database
print("\n1. Loading geocoded database...")
df = pd.read_csv(base_dir / "final_output" / "ttj_shipments.csv")
print(f"   Total shipments: {len(df):,}")

# ============================================================================
# 1. EXPORT PORTS (ORIGINS) - ENTIRE PERIOD
# ============================================================================
print("\n2. Creating export ports aggregate...")

# Filter to records with origin coordinates
export_df = df[
    (df['origin_latitude'].notna()) &
    (df['origin_latitude'] != '') &
    (df['origin_longitude'].notna()) &
    (df['origin_longitude'] != '')
].copy()

# Convert coordinates to numeric
export_df['origin_latitude'] = pd.to_numeric(export_df['origin_latitude'], errors='coerce')
export_df['origin_longitude'] = pd.to_numeric(export_df['origin_longitude'], errors='coerce')

# Remove any that failed conversion
export_df = export_df[
    (export_df['origin_latitude'].notna()) &
    (export_df['origin_longitude'].notna())
]

print(f"   Records with origin coordinates: {len(export_df):,}")

# Normalize port names to UPPERCASE to consolidate case variants
export_df['port_normalized'] = export_df['origin_port'].str.upper()

# For each normalized port, get the most common original case variant and coordinates
export_stats = export_df.groupby('port_normalized').agg({
    'origin_port': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'origin_latitude': 'first',
    'origin_longitude': 'first',
    'ship_name': 'count'
}).reset_index()

export_stats.columns = ['port_normalized', 'port_name', 'latitude', 'longitude', 'ship_count']
export_stats = export_stats.drop(columns=['port_normalized'])

# Sort by ship count descending
export_stats = export_stats.sort_values('ship_count', ascending=False)

# Save
export_file = base_dir / "analysis" / "annual_port_statistics" / "export_ports_total.csv"
export_stats.to_csv(export_file, index=False)
print(f"   ✅ Saved: {export_file}")
print(f"   Total records: {len(export_stats):,}")
print(f"   Unique ports: {export_stats['port_name'].nunique():,}")
print(f"   Total ships: {export_stats['ship_count'].sum():,}")

# ============================================================================
# 2. IMPORT PORTS (DESTINATIONS) - ENTIRE PERIOD
# ============================================================================
print("\n3. Creating import ports aggregate...")

# Filter to records with destination coordinates
import_df = df[
    (df['destination_latitude'].notna()) &
    (df['destination_latitude'] != '') &
    (df['destination_longitude'].notna()) &
    (df['destination_longitude'] != '')
].copy()

# Convert coordinates to numeric
import_df['destination_latitude'] = pd.to_numeric(import_df['destination_latitude'], errors='coerce')
import_df['destination_longitude'] = pd.to_numeric(import_df['destination_longitude'], errors='coerce')

# Remove any that failed conversion
import_df = import_df[
    (import_df['destination_latitude'].notna()) &
    (import_df['destination_longitude'].notna())
]

print(f"   Records with destination coordinates: {len(import_df):,}")

# Normalize port names to UPPERCASE to consolidate case variants
import_df['port_normalized'] = import_df['destination_port'].str.upper()

# For each normalized port, get the most common original case variant and coordinates
import_stats = import_df.groupby('port_normalized').agg({
    'destination_port': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
    'destination_latitude': 'first',
    'destination_longitude': 'first',
    'ship_name': 'count'
}).reset_index()

import_stats.columns = ['port_normalized', 'port_name', 'latitude', 'longitude', 'ship_count']
import_stats = import_stats.drop(columns=['port_normalized'])

# Sort by ship count descending
import_stats = import_stats.sort_values('ship_count', ascending=False)

# Save
import_file = base_dir / "analysis" / "annual_port_statistics" / "import_ports_total.csv"
import_stats.to_csv(import_file, index=False)
print(f"   ✅ Saved: {import_file}")
print(f"   Total records: {len(import_stats):,}")
print(f"   Unique ports: {import_stats['port_name'].nunique():,}")
print(f"   Total ships: {import_stats['ship_count'].sum():,}")

# ============================================================================
# 3. EXPORT-IMPORT PAIRS - ENTIRE PERIOD
# ============================================================================
print("\n4. Creating export-import pairs aggregate...")

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

print(f"   Records with both coordinates: {len(pairs_df):,}")

# Normalize port names to UPPERCASE to consolidate case variants
pairs_df['origin_normalized'] = pairs_df['origin_port'].str.upper()
pairs_df['destination_normalized'] = pairs_df['destination_port'].str.upper()

# Group by normalized port pairs
pairs_stats = pairs_df.groupby([
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

# Drop normalized columns
pairs_stats = pairs_stats.drop(columns=['origin_normalized', 'destination_normalized'])

# Reorder columns
pairs_stats = pairs_stats[[
    'origin_port',
    'origin_latitude',
    'origin_longitude',
    'destination_port',
    'destination_latitude',
    'destination_longitude',
    'ship_count'
]]

# Sort by ship count descending
pairs_stats = pairs_stats.sort_values('ship_count', ascending=False)

# Save
pairs_file = base_dir / "analysis" / "annual_port_statistics" / "export_import_pairs_total.csv"
pairs_stats.to_csv(pairs_file, index=False)
print(f"   ✅ Saved: {pairs_file}")
print(f"   Total records: {len(pairs_stats):,}")
print(f"   Unique origin ports: {pairs_stats['origin_port'].nunique():,}")
print(f"   Unique destination ports: {pairs_stats['destination_port'].nunique():,}")
print(f"   Total ships in complete routes: {pairs_stats['ship_count'].sum():,}")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("\n" + "="*80)
print("SUMMARY STATISTICS (1874-1899)")
print("="*80)

print("\nEXPORT PORTS (Origins):")
print(f"  Unique ports: {len(export_stats):,}")
print(f"  Total ships: {export_stats['ship_count'].sum():,}")
print(f"  Average ships per port: {export_stats['ship_count'].mean():.1f}")
print(f"  Median ships per port: {export_stats['ship_count'].median():.1f}")

print("\nIMPORT PORTS (Destinations):")
print(f"  Unique ports: {len(import_stats):,}")
print(f"  Total ships: {import_stats['ship_count'].sum():,}")
print(f"  Average ships per port: {import_stats['ship_count'].mean():.1f}")
print(f"  Median ships per port: {import_stats['ship_count'].median():.1f}")

print("\nEXPORT-IMPORT PAIRS:")
print(f"  Unique pairs: {len(pairs_stats):,}")
print(f"  Total ships in complete routes: {pairs_stats['ship_count'].sum():,}")
print(f"  Average ships per route: {pairs_stats['ship_count'].mean():.1f}")
print(f"  Median ships per route: {pairs_stats['ship_count'].median():.1f}")

# Top 10 export ports
print("\n" + "-"*80)
print("TOP 10 EXPORT PORTS (1874-1899)")
print("-"*80)
for i, row in export_stats.head(10).iterrows():
    print(f"  {i+1:2d}. {row['port_name']:40} {row['ship_count']:>7,} ships")

# Top 10 import ports
print("\n" + "-"*80)
print("TOP 10 IMPORT PORTS (1874-1899)")
print("-"*80)
for i, row in import_stats.head(10).iterrows():
    print(f"  {i+1:2d}. {row['port_name']:40} {row['ship_count']:>7,} ships")

# Top 10 routes
print("\n" + "-"*80)
print("TOP 10 ROUTES (1874-1899)")
print("-"*80)
for i, row in pairs_stats.head(10).iterrows():
    print(f"  {i+1:2d}. {row['origin_port']:20} → {row['destination_port']:20} {row['ship_count']:>7,} ships")

print("\n" + "="*80)
print("ALL FILES SAVED SUCCESSFULLY")
print("="*80)
