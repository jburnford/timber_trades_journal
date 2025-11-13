#!/usr/bin/env python3
"""Add new origin and destination ports to Ports_Master.geojson"""

import json
import pandas as pd

print("="*80)
print("ADDING NEW PORTS TO GEOJSON")
print("="*80)

# Load existing GeoJSON
print("\n1. Loading existing GeoJSON...")
with open('../Ports_Master.geojson', 'r') as f:
    geojson = json.load(f)

original_count = len(geojson['features'])
print(f"   Original ports: {original_count}")

# Load origin ports
print("\n2. Loading new origin ports...")
origin_ports = pd.read_csv('new_ports_truly_unique.csv')
print(f"   Origin ports to add: {len(origin_ports)}")

# Load destination ports
print("\n3. Loading new destination ports...")
dest_ports = pd.read_csv('british_new_ports_to_add.csv')
print(f"   Destination ports to add: {len(dest_ports)}")

# Combine all new ports
all_new_ports = pd.concat([origin_ports, dest_ports], ignore_index=True)
print(f"\n4. Total new ports: {len(all_new_ports)}")

# Add to GeoJSON
print("\n5. Adding ports to GeoJSON...")
added_count = 0

for idx, row in all_new_ports.iterrows():
    feature = {
        "type": "Feature",
        "properties": {
            "Name": row['port_name'],
            "Country": row['country'],
            "AltNames": str(row.get('alternative_names', '')),
            "Notes": str(row.get('notes', '')),
            "ShipCount": int(row['ship_count'])
        },
        "geometry": {
            "type": "Point",
            "coordinates": [float(row['longitude']), float(row['latitude'])]
        }
    }
    geojson['features'].append(feature)
    added_count += 1
    print(f"   Added: {row['port_name']:30} ({row['latitude']:.4f}, {row['longitude']:.4f})")

# Save updated GeoJSON
output_file = '../Ports_Master.geojson'
print(f"\n6. Saving updated GeoJSON to: {output_file}")

with open(output_file, 'w') as f:
    json.dump(geojson, f, indent=2)

final_count = len(geojson['features'])

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Original ports:     {original_count:>6}")
print(f"Ports added:        {added_count:>6}")
print(f"Final total:        {final_count:>6}")
print(f"\n✅ GeoJSON updated successfully!")
print("="*80)
