#!/usr/bin/env python3
"""Review and fix British port mappings"""

import pandas as pd
import json

# Load the current mappings
with open('british_port_manual_mappings.json', 'r') as f:
    current_mappings = json.load(f)['matches']

# Load missing ports to get ship counts
df = pd.read_csv('british_ports_missing_v2.csv')
port_counts = dict(zip(df['port_name'], df['ship_count']))

# Categorize mappings
suspicious_grimsby = []
liverpool_tilbury = []
non_british = []
correct_mappings = {}

for db_port, mapped_port in current_mappings.items():
    count = port_counts.get(db_port, 0)

    # Check for suspicious Grimsby entries
    if 'GRIMSBY (' in db_port:
        dock_name = db_port.replace('GRIMSBY (', '').replace(')', '')

        # These docks are NOT in Grimsby
        if 'TILBURY' in dock_name:
            suspicious_grimsby.append((db_port, 'Tilbury Docks', count, 'Tilbury is in Essex, not Grimsby'))
        elif 'SURREY' in dock_name:
            suspicious_grimsby.append((db_port, 'Surrey Commercial Docks', count, 'Surrey Docks are in London'))
        elif 'COBURG' in dock_name:
            suspicious_grimsby.append((db_port, 'Liverpool', count, 'Coburg Dock is in Liverpool'))
        elif 'LONDON' in dock_name:
            suspicious_grimsby.append((db_port, 'London', count, 'London Docks are in London'))
        elif 'RUNCORN' in dock_name:
            suspicious_grimsby.append((db_port, 'Runcorn', count, 'Runcorn is separate port'))
        else:
            # These are legitimate Grimsby docks
            correct_mappings[db_port] = mapped_port

    # Check for Liverpool (Tilbury) entries
    elif 'LIVERPOOL (TILBURY' in db_port:
        liverpool_tilbury.append((db_port, 'Tilbury Docks', count, 'Tilbury is NOT in Liverpool'))

    # Check for non-British destinations
    elif mapped_port in ['Le Havre', 'Quebec City']:
        non_british.append((db_port, mapped_port, count))

    else:
        correct_mappings[db_port] = mapped_port

# Print results
print("="*80)
print("BRITISH PORT MAPPINGS REVIEW")
print("="*80)

print(f"\n✅ Correct mappings: {len(correct_mappings)}")
print(f"⚠️  Suspicious Grimsby entries: {len(suspicious_grimsby)}")
print(f"⚠️  Liverpool (Tilbury) entries: {len(liverpool_tilbury)}")
print(f"❌ Non-British destinations: {len(non_british)}")

if suspicious_grimsby:
    print("\n" + "="*80)
    print("SUSPICIOUS GRIMSBY ENTRIES (likely OCR errors)")
    print("="*80)
    print(f"{'Database Port':50} {'Should Map To':30} {'Ships':>8} {'Reason'}")
    print("-"*80)
    for db_port, correct_map, count, reason in suspicious_grimsby:
        print(f"{db_port:50} {correct_map:30} {count:>8,} {reason}")

    grimsby_ships = sum(x[2] for x in suspicious_grimsby)
    print(f"\nTotal ships affected: {grimsby_ships:,}")

if liverpool_tilbury:
    print("\n" + "="*80)
    print("LIVERPOOL (TILBURY) ENTRIES (Tilbury is NOT in Liverpool)")
    print("="*80)
    for db_port, correct_map, count, reason in liverpool_tilbury:
        print(f"{db_port:50} → {correct_map:30} {count:>8,} ships")

    liverpool_tilbury_ships = sum(x[2] for x in liverpool_tilbury)
    print(f"\nTotal ships affected: {liverpool_tilbury_ships:,}")

if non_british:
    print("\n" + "="*80)
    print("NON-BRITISH DESTINATIONS (should be excluded)")
    print("="*80)
    for db_port, mapped_port, count in non_british:
        print(f"{db_port:50} → {mapped_port:30} {count:>8,} ships")

    non_british_ships = sum(x[2] for x in non_british)
    print(f"\nTotal ships affected: {non_british_ships:,}")
    print("\nDECISION: These will be documented but not mapped. Too few ships to justify")
    print("returning to the parser to fix OCR errors.")

# Search for other potential non-British destinations in the full dataset
print("\n" + "="*80)
print("SEARCHING FOR OTHER NON-BRITISH DESTINATIONS")
print("="*80)

# Known non-British ports that might appear
non_british_keywords = [
    'QUEBEC', 'MONTREAL', 'HAVRE', 'BREMEN', 'HAMBURG', 'ANTWERP',
    'ROTTERDAM', 'AMSTERDAM', 'BOULOGNE', 'CALAIS', 'BORDEAUX',
    'MARSEILLE', 'NEW YORK', 'BOSTON', 'PHILADELPHIA', 'BALTIMORE',
    'GENOA', 'VENICE', 'NAPLES', 'TRIESTE', 'FIUME'
]

other_non_british = []
for idx, row in df.iterrows():
    port = row['port_name']
    count = row['ship_count']

    # Skip if already in our lists
    if port in current_mappings:
        continue

    # Check for non-British keywords
    for keyword in non_british_keywords:
        if keyword in port:
            other_non_british.append((port, count))
            break

if other_non_british:
    other_non_british.sort(key=lambda x: x[1], reverse=True)
    print("\nPotential non-British destinations in unmapped ports:")
    for port, count in other_non_british[:20]:
        print(f"{port:50} {count:>8,} ships")

    other_ships = sum(x[1] for x in other_non_british)
    print(f"\nTotal: {len(other_non_british)} ports, {other_ships:,} ships")

# Create corrected mappings
corrected_mappings = dict(correct_mappings)

# Add corrected Grimsby entries
for db_port, correct_map, count, reason in suspicious_grimsby:
    corrected_mappings[db_port] = correct_map

# Add corrected Liverpool (Tilbury) entries
for db_port, correct_map, count, reason in liverpool_tilbury:
    corrected_mappings[db_port] = correct_map

# Save corrected mappings
output = {
    "description": "British destination port mappings for TTJ shipments data (corrected)",
    "notes": [
        "Fixed suspicious Grimsby entries - mapped to actual dock locations",
        "Fixed Liverpool (Tilbury) entries - Tilbury is in Essex, not Liverpool",
        "Non-British destinations (Quebec, Le Havre, etc.) documented but NOT mapped",
        "Decision: Non-British destinations too small to justify parser fixes, will be excluded from geocoding"
    ],
    "matches": corrected_mappings
}

with open('british_port_manual_mappings_corrected.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\n" + "="*80)
print(f"💾 Saved corrected mappings to: british_port_manual_mappings_corrected.json")
print(f"✅ Total mappings: {len(corrected_mappings)}")
print("="*80)

# Calculate impact
total_corrected_ships = sum(port_counts.get(p, 0) for p in corrected_mappings)
print(f"\n📊 Total ships covered by corrected mappings: {total_corrected_ships:,}")
print(f"📊 Ships in non-British destinations (excluded): {non_british_ships:,}")
