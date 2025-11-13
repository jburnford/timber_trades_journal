#!/usr/bin/env python3
"""
Match GeoJSON port locations with normalized port names from v4.3 database.

Identifies:
1. Perfect matches (ports in both GeoJSON and database)
2. Fuzzy matches (similar names that may need review)
3. Database ports missing geocoding (in database but not in GeoJSON)
4. Unused GeoJSON ports (in GeoJSON but not in database)
"""

import json
import csv
from collections import Counter
from pathlib import Path
from difflib import SequenceMatcher

csv.field_size_limit(1000000)

def normalize_port_name(port_name):
    """Normalize port name for matching."""
    if not port_name:
        return ""

    # Remove parenthetical suffixes for matching
    # e.g., "London (Victoria Dock)" -> "London"
    base_name = port_name.split('(')[0].strip()

    # Lowercase for case-insensitive matching
    return base_name.lower()

def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()

def load_geojson_ports(geojson_path):
    """Load port names and coordinates from GeoJSON."""
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ports = {}
    for feature in data['features']:
        if feature['properties']['Name'] == 'Delete':
            continue

        port_name = feature['properties']['Name']
        coords = feature['geometry']['coordinates']

        ports[port_name] = {
            'longitude': coords[0],
            'latitude': coords[1],
            'properties': feature['properties']
        }

    return ports

def load_database_ports(csv_path):
    """Load normalized destination ports from v4.3 database."""
    destination_counts = Counter()
    origin_counts = Counter()

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dest = row['destination_port_normalized'].strip()
            origin = row['origin_port_normalized'].strip()

            if dest:
                destination_counts[dest] += 1
            if origin:
                origin_counts[origin] += 1

    return destination_counts, origin_counts

def match_ports(geojson_ports, db_destinations, db_origins):
    """Match GeoJSON ports with database ports."""

    # Create normalized lookup for GeoJSON
    geo_normalized = {normalize_port_name(name): name for name in geojson_ports.keys()}

    matches = {
        'perfect_destinations': [],
        'perfect_origins': [],
        'fuzzy_destinations': [],
        'fuzzy_origins': [],
        'missing_destinations': [],
        'missing_origins': [],
        'unused_geojson': []
    }

    matched_geo_ports = set()

    # Match destinations
    for db_port, count in db_destinations.most_common():
        db_normalized = normalize_port_name(db_port)

        if db_normalized in geo_normalized:
            # Perfect match
            geo_port = geo_normalized[db_normalized]
            matches['perfect_destinations'].append({
                'db_port': db_port,
                'geo_port': geo_port,
                'count': count,
                'coords': geojson_ports[geo_port]
            })
            matched_geo_ports.add(geo_port)
        else:
            # Check for fuzzy matches
            best_match = None
            best_ratio = 0

            for geo_norm, geo_name in geo_normalized.items():
                ratio = similarity(db_normalized, geo_norm)
                if ratio > best_ratio and ratio >= 0.75:
                    best_ratio = ratio
                    best_match = geo_name

            if best_match:
                matches['fuzzy_destinations'].append({
                    'db_port': db_port,
                    'geo_port': best_match,
                    'count': count,
                    'similarity': best_ratio,
                    'coords': geojson_ports[best_match]
                })
                matched_geo_ports.add(best_match)
            else:
                matches['missing_destinations'].append({
                    'db_port': db_port,
                    'count': count
                })

    # Match origins
    for db_port, count in db_origins.most_common():
        db_normalized = normalize_port_name(db_port)

        if db_normalized in geo_normalized:
            geo_port = geo_normalized[db_normalized]
            matches['perfect_origins'].append({
                'db_port': db_port,
                'geo_port': geo_port,
                'count': count,
                'coords': geojson_ports[geo_port]
            })
            matched_geo_ports.add(geo_port)
        else:
            best_match = None
            best_ratio = 0

            for geo_norm, geo_name in geo_normalized.items():
                ratio = similarity(db_normalized, geo_norm)
                if ratio > best_ratio and ratio >= 0.75:
                    best_ratio = ratio
                    best_match = geo_name

            if best_match:
                matches['fuzzy_origins'].append({
                    'db_port': db_port,
                    'geo_port': best_match,
                    'count': count,
                    'similarity': best_ratio,
                    'coords': geojson_ports[best_match]
                })
                matched_geo_ports.add(best_match)
            else:
                matches['missing_origins'].append({
                    'db_port': db_port,
                    'count': count
                })

    # Find unused GeoJSON ports
    for geo_port in geojson_ports.keys():
        if geo_port not in matched_geo_ports:
            matches['unused_geojson'].append({
                'geo_port': geo_port,
                'coords': geojson_ports[geo_port]
            })

    return matches

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    print("=" * 80)
    print("GEOJSON PORT MATCHING ANALYSIS")
    print("=" * 80)

    # Load data
    print("\nLoading GeoJSON ports...")
    geojson_ports = load_geojson_ports(base_dir / "Ports_Master.geojson")
    print(f"  Loaded {len(geojson_ports)} ports from GeoJSON")

    print("\nLoading database ports...")
    db_destinations, db_origins = load_database_ports(
        base_dir / "parsed_output" / "ttj_shipments_normalized_v4.3.csv"
    )
    print(f"  Loaded {len(db_destinations)} unique destination ports")
    print(f"  Loaded {len(db_origins)} unique origin ports")

    # Match ports
    print("\nMatching ports...")
    matches = match_ports(geojson_ports, db_destinations, db_origins)

    # Report results
    print("\n" + "=" * 80)
    print("MATCHING RESULTS")
    print("=" * 80)

    print(f"\n1. DESTINATION PORTS")
    print(f"   Perfect matches: {len(matches['perfect_destinations'])}")
    print(f"   Fuzzy matches: {len(matches['fuzzy_destinations'])}")
    print(f"   Missing geocoding: {len(matches['missing_destinations'])}")

    print(f"\n2. ORIGIN PORTS")
    print(f"   Perfect matches: {len(matches['perfect_origins'])}")
    print(f"   Fuzzy matches: {len(matches['fuzzy_origins'])}")
    print(f"   Missing geocoding: {len(matches['missing_origins'])}")

    print(f"\n3. UNUSED GEOJSON PORTS")
    print(f"   Ports in GeoJSON but not in database: {len(matches['unused_geojson'])}")

    # Show top missing destinations
    print(f"\n" + "=" * 80)
    print("TOP 20 DESTINATION PORTS MISSING GEOCODING")
    print("=" * 80)
    for i, item in enumerate(matches['missing_destinations'][:20], 1):
        print(f"{i:2}. {item['db_port']:40} ({item['count']:,} ships)")

    # Show top missing origins
    print(f"\n" + "=" * 80)
    print("TOP 20 ORIGIN PORTS MISSING GEOCODING")
    print("=" * 80)
    for i, item in enumerate(matches['missing_origins'][:20], 1):
        print(f"{i:2}. {item['db_port']:40} ({item['count']:,} ships)")

    # Show fuzzy matches for review
    print(f"\n" + "=" * 80)
    print("FUZZY MATCHES FOR REVIEW (Destinations)")
    print("=" * 80)
    for item in matches['fuzzy_destinations'][:20]:
        print(f"DB: {item['db_port']:30} <-> GEO: {item['geo_port']:30} "
              f"({item['similarity']:.2f} similarity, {item['count']:,} ships)")

    print(f"\n" + "=" * 80)
    print("FUZZY MATCHES FOR REVIEW (Origins)")
    print("=" * 80)
    for item in matches['fuzzy_origins'][:20]:
        print(f"DB: {item['db_port']:30} <-> GEO: {item['geo_port']:30} "
              f"({item['similarity']:.2f} similarity, {item['count']:,} ships)")

    # Save detailed results to JSON
    output_path = base_dir / "analysis" / "port_geocoding_matches.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Detailed results saved to: {output_path}")

    # Calculate coverage
    total_dest_ships = sum(db_destinations.values())
    matched_dest_ships = sum(m['count'] for m in matches['perfect_destinations'])
    matched_dest_ships += sum(m['count'] for m in matches['fuzzy_destinations'])

    print(f"\n" + "=" * 80)
    print("GEOCODING COVERAGE")
    print("=" * 80)
    print(f"Destination ships with geocoding: {matched_dest_ships:,} / {total_dest_ships:,} "
          f"({100*matched_dest_ships/total_dest_ships:.1f}%)")

    total_origin_ships = sum(db_origins.values())
    matched_origin_ships = sum(m['count'] for m in matches['perfect_origins'])
    matched_origin_ships += sum(m['count'] for m in matches['fuzzy_origins'])

    print(f"Origin ships with geocoding: {matched_origin_ships:,} / {total_origin_ships:,} "
          f"({100*matched_origin_ships/total_origin_ships:.1f}%)")

if __name__ == '__main__':
    main()
