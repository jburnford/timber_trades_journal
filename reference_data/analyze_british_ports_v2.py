#!/usr/bin/env python3
"""Analyze British destination ports with case-insensitive matching"""

import pandas as pd
import json
from difflib import SequenceMatcher
from collections import Counter
import re

def fuzzy_match_score(a, b):
    """Calculate similarity ratio between two strings (case-insensitive)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def is_parsing_error(port_name):
    """Identify likely parsing errors vs real ports"""
    error_patterns = [
        r'.*PITWOOD.*',
        r'.*REDWOOD.*',
        r'.*SOUND LIST.*',
        r'.*BUILDING.*',
        r'.*CREDITOR.*',
        r'.*SECURED.*',
        r'.*NEWS.*',
        r'.*OTHER.*',
        r'.*WHARVES.*',
        r'.*ADVERTISE.*',
        r'.*EXPECTED.*',
        r'.*ARRIVED.*',
        r'.*SAILING.*',
    ]

    for pattern in error_patterns:
        if re.match(pattern, port_name, re.IGNORECASE):
            return True
    return False

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

geojson_ports = {}  # lowercase -> original name mapping
for feature in geojson['features']:
    port_name = feature['properties'].get('Name', '')
    if port_name:
        geojson_ports[port_name.lower()] = port_name

print(f"Total ports in GeoJSON: {len(geojson_ports)}")

# Categorize ports
exact_matches = []  # Case-insensitive exact matches
fuzzy_matches = []  # High similarity matches
parsing_errors = []  # Obvious errors
missing_ports = []  # Real ports needing coordinates

for port, count in dest_port_counts.items():
    # Check for parsing errors first
    if is_parsing_error(port):
        parsing_errors.append((port, count))
        continue

    port_lower = port.lower()

    # Check for exact match (case-insensitive)
    if port_lower in geojson_ports:
        exact_matches.append((port, geojson_ports[port_lower], count))
        continue

    # Try fuzzy matching
    best_match = None
    best_score = 0

    for geojson_lower, geojson_original in geojson_ports.items():
        score = fuzzy_match_score(port, geojson_original)
        if score > best_score:
            best_score = score
            best_match = geojson_original

    if best_score >= 0.85:
        fuzzy_matches.append({
            'db_port': port,
            'match': best_match,
            'score': best_score,
            'ships': count
        })
    else:
        missing_ports.append((port, count, best_match, best_score))

# Sort all lists
exact_matches.sort(key=lambda x: x[2], reverse=True)
fuzzy_matches.sort(key=lambda x: x['ships'], reverse=True)
parsing_errors.sort(key=lambda x: x[1], reverse=True)
missing_ports.sort(key=lambda x: x[1], reverse=True)

# Print summary
print("\n" + "="*80)
print("DESTINATION PORT ANALYSIS SUMMARY")
print("="*80)

exact_ships = sum(x[2] for x in exact_matches)
fuzzy_ships = sum(x['ships'] for x in fuzzy_matches)
error_ships = sum(x[1] for x in parsing_errors)
missing_ships = sum(x[1] for x in missing_ports)

print(f"\n✅ Exact matches (case-insensitive): {len(exact_matches)} ports, {exact_ships:,} ships")
print(f"🔄 Fuzzy matches (>=85% similarity): {len(fuzzy_matches)} ports, {fuzzy_ships:,} ships")
print(f"⚠️  Parsing errors: {len(parsing_errors)} ports, {error_ships:,} ships")
print(f"❌ Missing (need coordinates): {len(missing_ports)} ports, {missing_ships:,} ships")

total_mapped = exact_ships + fuzzy_ships
print(f"\n📊 Coverage: {total_mapped:,} / {len(df):,} ships ({total_mapped/len(df)*100:.1f}%)")

# Show top exact matches
print("\n" + "="*80)
print("TOP 20 EXACT MATCHES (case differences only)")
print("="*80)
for i, (db_port, geo_port, count) in enumerate(exact_matches[:20], 1):
    if db_port != geo_port:
        print(f"{i:2}. {db_port:35} → {geo_port:35} {count:>7,} ships")

# Show fuzzy matches needing normalization
if fuzzy_matches:
    print("\n" + "="*80)
    print("FUZZY MATCHES - ADD TO manual_port_matches.json")
    print("="*80)
    for match in fuzzy_matches:
        print(f'"{match["db_port"]}": "{match["match"]}",'
              f'  # {match["score"]:.1%} similarity, {match["ships"]:,} ships')

    # Save to JSON
    fuzzy_dict = {m['db_port']: m['match'] for m in fuzzy_matches}
    with open('british_ports_case_fuzzy_matches.json', 'w') as f:
        json.dump({"matches": fuzzy_dict}, f, indent=2)
    print(f"\n💾 Saved to: british_ports_case_fuzzy_matches.json")

# Show parsing errors
print("\n" + "="*80)
print("PARSING ERRORS (not real ports)")
print("="*80)
for port, count in parsing_errors[:20]:
    print(f"{port:50} {count:>7,} ships")

# Show missing ports
print("\n" + "="*80)
print("TOP 50 MISSING BRITISH PORTS (need coordinates or mapping)")
print("="*80)
print(f"{'Port Name':45} {'Ships':>10} {'Best Match':30} {'Score':>8}")
print("-" * 80)

for i, (port, count, match, score) in enumerate(missing_ports[:50], 1):
    print(f"{port:45} {count:>10,} {match[:28]:30} {score:>7.1%}")

# Save missing ports to CSV
results_df = pd.DataFrame([
    {
        'port_name': port,
        'ship_count': count,
        'best_fuzzy_match': match,
        'similarity': f"{score:.1%}",
        'needs_research': 'Yes' if score < 0.75 else 'Maybe'
    }
    for port, count, match, score in missing_ports
])
results_df.to_csv('british_ports_missing_v2.csv', index=False)
print(f"\n💾 Saved full list to: british_ports_missing_v2.csv")

# Create suggested normalization rules
print("\n" + "="*80)
print("SUGGESTED MANUAL MAPPINGS FOR TOP MISSING PORTS")
print("="*80)

# Manually suggest obvious ones
suggestions = [
    ("TYNE", "Tyne Ports", 10113),
    ("LYNN", "Lynn (King's Lynn)", 2586),
    ("BO'NESS", "Borrowstounness (Bo'Ness)", 2122),
    ("BORROWSTOUNNESS", "Borrowstounness (Bo'Ness)", 2591),
    ("STOCKTON", "Stockton-on-Tees", 1952),
    ("LONDON (TILBURY DOCKS)", "Tilbury Docks", 1321),
    ("KING'S LYNN", "Lynn (King's Lynn)", 1195),
    ("BERWICK", "Berwick-upon-Tweed", 607),
    ("LONDON (TILBURY DOCK)", "Tilbury Docks", 516),
    ("MILFORD", "Milford Haven", 263),
    ("LERWICK", "Lerwick", 252),
    ("QUEBEC", "Quebec City", 160),
]

for db_port, suggested, count in suggestions:
    print(f'"{db_port}": "{suggested}",  # {count:,} ships')

print("\n" + "="*80)
print(f"TOTAL IMPROVEMENTS POSSIBLE:")
print(f"  - Exact + Fuzzy matches: {total_mapped:,} ships")
print(f"  - With suggested mappings: +{sum(x[2] for x in suggestions):,} ships")
print(f"  - Potential coverage: ~{(total_mapped + sum(x[2] for x in suggestions))/len(df)*100:.1f}%")
print("="*80)
