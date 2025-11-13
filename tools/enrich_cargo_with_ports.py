#!/usr/bin/env python3
"""
Enrich cargo details with ship names, ports, and coordinates for commodity analysis.
"""

import pandas as pd
from pathlib import Path

print("="*80)
print("ENRICHING CARGO DETAILS WITH SHIP AND PORT INFORMATION")
print("="*80)

base_dir = Path("/home/jic823/TTJ Forest of Numbers")

# Load cargo details
print("\n1. Loading cargo details...")
cargo_df = pd.read_csv(base_dir / "final_output" / "ttj_cargo_details.csv")
print(f"   Total cargo records: {len(cargo_df):,}")

# Load shipments with port information
print("\n2. Loading shipment data...")
shipments_df = pd.read_csv(base_dir / "final_output" / "ttj_shipments.csv")
print(f"   Total shipments: {len(shipments_df):,}")

# Select relevant columns from shipments
ship_cols = [
    'record_id',
    'ship_name',
    'origin_port',
    'destination_port',
    'origin_latitude',
    'origin_longitude',
    'destination_latitude',
    'destination_longitude',
    'arrival_year',
    'arrival_month',
    'arrival_day'
]

shipments_subset = shipments_df[ship_cols].copy()

# Merge cargo with shipment data
print("\n3. Merging cargo details with shipment data...")
enriched_cargo = cargo_df.merge(
    shipments_subset,
    on='record_id',
    how='left'
)

print(f"   Enriched cargo records: {len(enriched_cargo):,}")

# Check merge success
matched = enriched_cargo['ship_name'].notna().sum()
print(f"   Records matched with ship data: {matched:,} ({100*matched/len(enriched_cargo):.1f}%)")

# Reorder columns for better readability
output_cols = [
    'cargo_id',
    'record_id',
    'ship_name',
    'origin_port',
    'origin_latitude',
    'origin_longitude',
    'destination_port',
    'destination_latitude',
    'destination_longitude',
    'arrival_year',
    'arrival_month',
    'arrival_day',
    'commodity',
    'quantity',
    'unit',
    'merchant',
    'source_file',
    'line_number',
    'raw_cargo_segment'
]

enriched_cargo = enriched_cargo[output_cols]

# Save enriched cargo details
output_file = base_dir / "final_output" / "ttj_cargo_details_enriched.csv"
print(f"\n4. Saving enriched cargo details...")
enriched_cargo.to_csv(output_file, index=False)

print(f"   ✅ Saved: {output_file}")

# Generate statistics
print("\n" + "="*80)
print("STATISTICS")
print("="*80)

print(f"\nTotal cargo records: {len(enriched_cargo):,}")
print(f"Unique commodities: {enriched_cargo['commodity'].nunique():,}")
print(f"Unique origin ports: {enriched_cargo['origin_port'].nunique():,}")
print(f"Unique destination ports: {enriched_cargo['destination_port'].nunique():,}")

# Cargo with coordinates
with_origin = enriched_cargo[
    (enriched_cargo['origin_latitude'].notna()) &
    (enriched_cargo['origin_latitude'] != '')
]
with_dest = enriched_cargo[
    (enriched_cargo['destination_latitude'].notna()) &
    (enriched_cargo['destination_latitude'] != '')
]
with_both = enriched_cargo[
    (enriched_cargo['origin_latitude'].notna()) &
    (enriched_cargo['origin_latitude'] != '') &
    (enriched_cargo['destination_latitude'].notna()) &
    (enriched_cargo['destination_latitude'] != '')
]

print(f"\nCargo records with origin coordinates: {len(with_origin):,} ({100*len(with_origin)/len(enriched_cargo):.1f}%)")
print(f"Cargo records with destination coordinates: {len(with_dest):,} ({100*len(with_dest)/len(enriched_cargo):.1f}%)")
print(f"Cargo records with complete routes: {len(with_both):,} ({100*len(with_both)/len(enriched_cargo):.1f}%)")

# Top 10 commodities
print("\n" + "-"*80)
print("TOP 10 COMMODITIES BY CARGO RECORDS")
print("-"*80)
top_commodities = enriched_cargo['commodity'].value_counts().head(10)
for i, (commodity, count) in enumerate(top_commodities.items(), 1):
    print(f"  {i:2d}. {str(commodity):40} {count:>7,} records")

# Top 10 origin ports for cargo
print("\n" + "-"*80)
print("TOP 10 ORIGIN PORTS BY CARGO RECORDS")
print("-"*80)
top_origins = enriched_cargo[enriched_cargo['origin_port'].notna()]['origin_port'].value_counts().head(10)
for i, (port, count) in enumerate(top_origins.items(), 1):
    print(f"  {i:2d}. {str(port):40} {count:>7,} records")

# Top 10 destination ports for cargo
print("\n" + "-"*80)
print("TOP 10 DESTINATION PORTS BY CARGO RECORDS")
print("-"*80)
top_dests = enriched_cargo[enriched_cargo['destination_port'].notna()]['destination_port'].value_counts().head(10)
for i, (port, count) in enumerate(top_dests.items(), 1):
    print(f"  {i:2d}. {str(port):40} {count:>7,} records")

print("\n" + "="*80)
print("ENRICHMENT COMPLETE")
print("="*80)
