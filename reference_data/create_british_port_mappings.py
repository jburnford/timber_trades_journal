#!/usr/bin/env python3
"""Create comprehensive British port mappings from missing ports list"""

import pandas as pd
import json
import re

# Load missing ports
df = pd.read_csv('british_ports_missing_v2.csv')

# Load GeoJSON to check what ports exist
with open('../Ports_Master.geojson', 'r') as f:
    geojson = json.load(f)

geojson_ports = set()
for feature in geojson['features']:
    port_name = feature['properties'].get('Name', '')
    if port_name:
        geojson_ports.add(port_name)

# Manual mappings based on analysis
manual_mappings = {}
parsing_errors = []
needs_coordinates = []

for idx, row in df.iterrows():
    port = row['port_name']
    count = row['ship_count']

    # === PARSING ERRORS (not real ports) ===
    error_keywords = [
        'REGISTERED', 'CURRENT PRICES', 'PETITION', 'IMPORTERS OF', 'TENDERS',
        'CORRESPONDENCE', 'RESULTS', 'LIMITED', 'TIMBER TRADES JOURNAL',
        'JOINERY', 'CONTENTS', 'DIVIDENDS', 'LUMBER PROSPECTS', 'DOORS',
        'REVIEW', 'CEMENT', 'TRUST', 'WOOD', 'BROS', 'SEPTEMBER', 'CESSIO',
        'COLLINSON', 'LOCK', 'FILES', 'VIGERS', 'BROWN', 'NOTICE', 'MEETING',
        'CREDITOR', 'UNSECURED', 'SECURED', 'NEWS', 'BUILDING', 'SOCIETY',
        'ADVERTISE', 'EXPECTED', 'ARRIVED', 'SAILING', 'DESCRIPTION'
    ]

    # Single letter or 2-3 letter fragments
    if len(port) <= 3 and port not in ['AYR', 'RYE', 'SDD', 'WMW']:
        parsing_errors.append((port, count))
        continue

    # Check for error keywords
    is_error = any(keyword in port for keyword in error_keywords)
    if is_error:
        parsing_errors.append((port, count))
        continue

    # === OBVIOUS MAPPINGS ===

    # Dock-specific entries should map to city
    if 'LIVERPOOL (' in port and ')' in port:
        manual_mappings[port] = 'Liverpool'
    elif 'LONDON (' in port and ')' in port:
        dock_name = port.replace('LONDON (', '').replace(')', '')
        if 'TILBURY' in dock_name:
            manual_mappings[port] = 'Tilbury Docks'
        elif 'SURREY' in dock_name:
            manual_mappings[port] = 'Surrey Commercial Docks'
        else:
            manual_mappings[port] = 'London'
    elif 'GRIMSBY (' in port and ')' in port:
        manual_mappings[port] = 'Grimsby'
    elif 'GOOLE (' in port and ')' in port:
        manual_mappings[port] = 'Goole'
    elif 'NEWPORT (MON' in port:
        manual_mappings[port] = 'Newport'

    # Standalone dock names
    elif port in ['NELSON DOCK', 'COBURG DOCK', 'BRUNSWICK DOCK', 'QUEEN\'S DOCK',
                   'PRINCE\'S DOCK', 'TOWER DOCK', 'WELLINGTON DOCK', 'CANADA DOCK']:
        manual_mappings[port] = 'Liverpool'
    elif port in ['LONDON DOCKS', 'VICTORIA DOCK', 'ALBERT DOCK', 'MILLWALL DOCKS',
                   'MILLWALL DOCK', 'WEST INDIA DOCKS', 'UNION DOCK', 'ALEXANDRA DOCK']:
        manual_mappings[port] = 'London'

    # Known British ports
    elif port == 'TYNE':
        manual_mappings[port] = 'Tyne Ports'
    elif port in ['BORROWSTOUNNESS', 'BORROWSTOUNESS', 'BO\'NESS']:
        manual_mappings[port] = 'Borrowstounness (Bo\'Ness)'
    elif port in ['LYNN', 'KING\'S LYNN']:
        manual_mappings[port] = 'Lynn (King\'s Lynn)'
    elif port == 'STOCKTON':
        manual_mappings[port] = 'Stockton-on-Tees'
    elif port == 'BERWICK':
        manual_mappings[port] = 'Berwick-upon-Tweed'
    elif port == 'MILFORD':
        manual_mappings[port] = 'Milford Haven'
    elif port in ['HARTLEPOOL (WEST)', 'HARTLEPOOL (EAST)']:
        manual_mappings[port] = 'Hartlepool'
    elif port == 'BARROW':
        manual_mappings[port] = 'Barrow-in-Furness'
    elif port == 'MIDDLESBRO\'':
        manual_mappings[port] = 'Middlesbrough'
    elif port == 'QUEENBORO\'':
        manual_mappings[port] = 'Queenborough'
    elif port == 'RUNCORN DOCK':
        manual_mappings[port] = 'Runcorn'
    elif port == '...GOOLE':
        manual_mappings[port] = 'Goole'
    elif port == 'TILBURY':
        manual_mappings[port] = 'Tilbury Docks'

    # Quebec (Canadian destination)
    elif port == 'QUEBEC':
        manual_mappings[port] = 'Quebec City'

    # French ports (not British but in the data)
    elif port == 'HAVRE':
        manual_mappings[port] = 'Le Havre'

    # London districts/docks that exist in GeoJSON
    elif port == 'DEPTFORD' or port == 'DEPTFORD BUOYS':
        if 'Deptford' in geojson_ports:
            manual_mappings[port] = 'Deptford'
        else:
            needs_coordinates.append((port, count, 'London Thames dock area'))
    elif port == 'SILVERTOWN':
        if 'Silvertown' in geojson_ports:
            manual_mappings[port] = 'Silvertown'
        else:
            needs_coordinates.append((port, count, 'London Thames dock area'))
    elif port == 'PURFLEET':
        if 'Purfleet' in geojson_ports:
            manual_mappings[port] = 'Purfleet'
        else:
            needs_coordinates.append((port, count, 'Thames Estuary'))

    # Scottish ports
    elif port == 'GRANTON':
        if 'Granton' in geojson_ports:
            manual_mappings[port] = 'Granton'
        else:
            needs_coordinates.append((port, count, 'Edinburgh port'))
    elif port == 'LERWICK':
        if 'Lerwick' in geojson_ports:
            manual_mappings[port] = 'Lerwick'
        else:
            needs_coordinates.append((port, count, 'Shetland Islands'))

    # English ports
    elif port == 'SHOREHAM':
        if 'Shoreham-by-Sea' in geojson_ports:
            manual_mappings[port] = 'Shoreham-by-Sea'
        else:
            needs_coordinates.append((port, count, 'Sussex'))
    elif port == 'CLIFFE CREEK':
        needs_coordinates.append((port, count, 'Cliffe, Kent'))

    # Irish ports
    elif port == 'SKIBBEREEN':
        needs_coordinates.append((port, count, 'County Cork, Ireland'))

    # Uncertain / other
    elif port == 'BORDEN':
        needs_coordinates.append((port, count, 'Possibly Borden, Kent'))
    elif port == 'FIFE':
        needs_coordinates.append((port, count, 'Possibly Methil or other Fife port'))
    elif port in ['WMW', 'SDD', 'ION']:
        needs_coordinates.append((port, count, 'Abbreviation - unclear'))
    else:
        # Everything else needs manual review
        pass

# Print results
print("="*80)
print(f"BRITISH PORT MAPPINGS ANALYSIS")
print("="*80)
print(f"\n✅ Manual mappings created: {len(manual_mappings)}")
print(f"⚠️  Parsing errors identified: {len(parsing_errors)}")
print(f"❓ Need coordinates/research: {len(needs_coordinates)}")

# Calculate ships covered
mapped_ships = sum(row['ship_count'] for idx, row in df.iterrows()
                   if row['port_name'] in manual_mappings)
error_ships = sum(x[1] for x in parsing_errors)
research_ships = sum(x[1] for x in needs_coordinates)

print(f"\n📊 Ship counts:")
print(f"   Mapped: {mapped_ships:,} ships")
print(f"   Errors: {error_ships:,} ships")
print(f"   Research: {research_ships:,} ships")

# Save manual mappings to JSON
output = {
    "description": "British destination port mappings for TTJ shipments data",
    "matches": manual_mappings
}

with open('british_port_manual_mappings.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n💾 Saved mappings to: british_port_manual_mappings.json")

# Print top mappings
print("\n" + "="*80)
print("TOP 30 MANUAL MAPPINGS")
print("="*80)

mapped_with_counts = []
for idx, row in df.iterrows():
    port = row['port_name']
    if port in manual_mappings:
        mapped_with_counts.append((port, manual_mappings[port], row['ship_count']))

mapped_with_counts.sort(key=lambda x: x[2], reverse=True)

for port, mapping, count in mapped_with_counts[:30]:
    print(f'"{port}": "{mapping}",  # {count:,} ships')

# Print ports needing research
if needs_coordinates:
    print("\n" + "="*80)
    print("PORTS NEEDING COORDINATE RESEARCH")
    print("="*80)
    needs_coordinates.sort(key=lambda x: x[1], reverse=True)

    for port, count, note in needs_coordinates[:20]:
        print(f"{port:40} {count:>7,} ships  ({note})")
