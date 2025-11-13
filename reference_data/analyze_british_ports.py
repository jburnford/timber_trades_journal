#!/usr/bin/env python3
"""Analyze British destination ports - find missing ports and suggest mappings"""

import pandas as pd
import json
from difflib import SequenceMatcher
from collections import Counter

def fuzzy_match_score(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Load shipments data
print("Loading shipments data...")
df = pd.read_csv('../final_output/ttj_shipments.csv')

# Get all destination ports and their counts
print("Analyzing destination ports...")
dest_ports = df['destination_port'].dropna()
dest_port_counts = Counter(dest_ports)

print(f"\nTotal unique destination ports: {len(dest_port_counts)}")
print(f"Total shipments: {len(df)}")

# Load GeoJSON to get existing British port names
print("\nLoading GeoJSON...")
with open('../Ports_Master.geojson', 'r', encoding='utf-8') as f:
    geojson = json.load(f)

geojson_ports = set()
for feature in geojson['features']:
    port_name = feature['properties'].get('Name', '')
    if port_name:
        geojson_ports.add(port_name)

print(f"Total ports in GeoJSON: {len(geojson_ports)}")

# Find missing ports
missing_ports = []
found_ports = []

for port, count in dest_port_counts.items():
    if port not in geojson_ports:
        missing_ports.append((port, count))
    else:
        found_ports.append((port, count))

missing_ports.sort(key=lambda x: x[1], reverse=True)
found_ports.sort(key=lambda x: x[1], reverse=True)

print(f"\n✅ Destination ports already in GeoJSON: {len(found_ports)}")
print(f"❌ Destination ports MISSING from GeoJSON: {len(missing_ports)}")

# Calculate ship counts
missing_ship_count = sum(count for _, count in missing_ports)
found_ship_count = sum(count for _, count in found_ports)
print(f"\nShips with mapped destinations: {found_ship_count:,}")
print(f"Ships with MISSING destinations: {missing_ship_count:,}")
print(f"Destination coverage: {found_ship_count / len(df) * 100:.1f}%")

# Find fuzzy matches for missing ports
print("\n" + "="*80)
print("FUZZY MATCHING ANALYSIS")
print("="*80)

fuzzy_matches = []
no_matches = []

for port, count in missing_ports:
    best_match = None
    best_score = 0

    for geojson_port in geojson_ports:
        score = fuzzy_match_score(port, geojson_port)
        if score > best_score:
            best_score = score
            best_match = geojson_port

    if best_score >= 0.85:
        fuzzy_matches.append({
            'missing': port,
            'match': best_match,
            'score': best_score,
            'ships': count
        })
    else:
        no_matches.append((port, count, best_match, best_score))

# Sort by ship count
fuzzy_matches.sort(key=lambda x: x['ships'], reverse=True)
no_matches.sort(key=lambda x: x[1], reverse=True)

print(f"\n✅ High-confidence fuzzy matches (>=85% similarity): {len(fuzzy_matches)}")
if fuzzy_matches:
    print("\nSuggested mappings for manual_port_matches.json:")
    print("-" * 80)
    for match in fuzzy_matches:
        print(f"{match['missing']:30} → {match['match']:30} ({match['score']:.1%}, {match['ships']:,} ships)")

print(f"\n❌ Ports needing coordinate research: {len(no_matches)}")
print("\nTop 30 missing British ports by ship count:")
print("-" * 80)
print(f"{'Port Name':40} {'Ships':>10} {'Best Match':30} {'Score':>8}")
print("-" * 80)

for i, (port, count, best_match, score) in enumerate(no_matches[:30], 1):
    print(f"{port:40} {count:>10,} {best_match[:28]:30} {score:>7.1%}")

# Save results to CSV
results_df = pd.DataFrame([
    {'port_name': port, 'ship_count': count, 'best_fuzzy_match': match, 'similarity': score}
    for port, count, match, score in no_matches
])
results_df.to_csv('british_ports_missing.csv', index=False)
print(f"\n💾 Saved full list to: british_ports_missing.csv")

# Save fuzzy matches to JSON format
if fuzzy_matches:
    fuzzy_dict = {match['missing']: match['match'] for match in fuzzy_matches}
    with open('british_ports_fuzzy_matches.json', 'w', encoding='utf-8') as f:
        json.dump(fuzzy_dict, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved fuzzy matches to: british_ports_fuzzy_matches.json")

    ships_fixed = sum(match['ships'] for match in fuzzy_matches)
    print(f"\n📊 Summary:")
    print(f"   - Fuzzy matches: {len(fuzzy_matches)} ports, {ships_fixed:,} ships")
    print(f"   - Need coordinates: {len(no_matches)} ports, {sum(x[1] for x in no_matches):,} ships")
