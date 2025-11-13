#!/usr/bin/env python3
"""Process user-provided coordinates for missing British ports"""

import json
import pandas as pd

# User-provided data
new_ports = [
    {'port_name': 'Lerwick', 'latitude': 60.155, 'longitude': -1.145, 'country': 'Scotland',
     'notes': 'Shetland Islands', 'db_ports': ['LERWICK'], 'ships': 252},

    {'port_name': 'Deptford', 'latitude': 51.478, 'longitude': -0.0265, 'country': 'England',
     'notes': 'London Thames dock', 'db_ports': ['DEPTFORD', 'DEPTFORD BUOYS'], 'ships': 293},

    {'port_name': 'Borden', 'latitude': 51.334, 'longitude': 0.703, 'country': 'England',
     'notes': 'Kent', 'db_ports': ['BORDEN'], 'ships': 102},

    {'port_name': 'Cliffe', 'latitude': 51.4619, 'longitude': 0.4975, 'country': 'England',
     'notes': 'Cliffe, Kent on Thames Estuary', 'db_ports': ['CLIFFE CREEK'], 'ships': 77},

    {'port_name': 'Silvertown', 'latitude': 51.5, 'longitude': 0.03, 'country': 'England',
     'notes': 'London Thames docks', 'db_ports': ['SILVERTOWN'], 'ships': 71},

    {'port_name': 'Skibbereen', 'latitude': 51.5486, 'longitude': -9.2636, 'country': 'Ireland',
     'notes': 'County Cork', 'db_ports': ['SKIBBEREEN'], 'ships': 44},

    {'port_name': 'Purfleet', 'latitude': 51.48, 'longitude': 0.25, 'country': 'England',
     'notes': 'Thames Estuary, Essex', 'db_ports': ['PURFLEET'], 'ships': 40}
]

# Ports that map to existing GeoJSON entries
map_to_existing = {
    'GRANTON': 'Granton Harbour',  # 92 ships
    'FIFE': 'Leith'  # 46 ships (Leith is Edinburgh's port)
}

# Load existing corrected mappings
with open('british_port_manual_mappings_corrected.json', 'r') as f:
    mappings_data = json.load(f)

# Add new mappings
for db_port, geo_port in map_to_existing.items():
    mappings_data['matches'][db_port] = geo_port

# Add mappings for new ports
for port in new_ports:
    for db_port in port['db_ports']:
        mappings_data['matches'][db_port] = port['port_name']

# Update notes
mappings_data['notes'].append("Added 9 missing British ports with user-provided coordinates")
mappings_data['notes'].append("GRANTON mapped to existing 'Granton Harbour'")
mappings_data['notes'].append("FIFE mapped to existing 'Leith' (Edinburgh's port)")

# Save updated mappings
with open('british_port_manual_mappings_final.json', 'w') as f:
    json.dump(mappings_data, f, indent=2)

print("="*80)
print("BRITISH PORT MAPPINGS - FINAL UPDATE")
print("="*80)

print(f"\n✅ Total manual mappings: {len(mappings_data['matches'])}")

print("\n📋 Mapped to existing GeoJSON ports:")
for db_port, geo_port in map_to_existing.items():
    print(f"   {db_port} → {geo_port}")

print(f"\n📍 New ports to add to GeoJSON: {len(new_ports)}")
total_new_ships = sum(p['ships'] for p in new_ports)
print(f"   Ships covered: {total_new_ships}")

for port in new_ports:
    db_list = ', '.join(port['db_ports'])
    print(f"   • {port['port_name']:20} ({port['latitude']}, {port['longitude']}) - {port['ships']} ships")
    print(f"     Maps from: {db_list}")

# Create CSV for adding to GeoJSON
df = pd.DataFrame([
    {
        'port_name': p['port_name'],
        'ship_count': p['ships'],
        'latitude': p['latitude'],
        'longitude': p['longitude'],
        'country': p['country'],
        'alternative_names': ', '.join(p['db_ports']),
        'notes': p['notes']
    }
    for p in new_ports
])

df.to_csv('british_new_ports_to_add.csv', index=False)
print(f"\n💾 Saved new ports to: british_new_ports_to_add.csv")
print(f"💾 Saved final mappings to: british_port_manual_mappings_final.json")

# Calculate final coverage
print("\n" + "="*80)
print("FINAL BRITISH DESTINATION PORT COVERAGE")
print("="*80)

# From previous analysis
exact_fuzzy = 112016  # Exact + fuzzy matches
manual_original = 28994  # Original manual mappings
map_existing = 92 + 46  # GRANTON + FIFE
new_ports_ships = total_new_ships
total_british = 150592

total_mapped = exact_fuzzy + manual_original + map_existing + new_ports_ships
coverage = total_mapped / total_british * 100

print(f"\nExact + Fuzzy matches:     {exact_fuzzy:>10,} ships")
print(f"Manual mappings:           {manual_original:>10,} ships")
print(f"Map to existing (new):     {map_existing:>10,} ships")
print(f"New ports added:           {new_ports_ships:>10,} ships")
print(f"{'─'*45}")
print(f"Total mapped:              {total_mapped:>10,} ships")
print(f"Total dataset:             {total_british:>10,} ships")
print(f"\n📊 Coverage: {coverage:.2f}%")

# Calculate remaining
remaining = total_british - total_mapped
print(f"📊 Remaining unmapped: {remaining:,} ships ({remaining/total_british*100:.2f}%)")
