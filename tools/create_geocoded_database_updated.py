#!/usr/bin/env python3
"""
Create geocoded database with updated normalization rules.

Uses normalized CSV and applies all manual matches + GeoJSON coordinates.
"""

import json
import csv
from pathlib import Path

csv.field_size_limit(1000000)

def normalize_port_name(port_name):
    """Normalize port name for matching (remove parenthetical suffixes)."""
    if not port_name:
        return ""
    base_name = port_name.split('(')[0].strip()
    return base_name.lower()

def load_geojson_coords(geojson_path):
    """Load port coordinates from GeoJSON with case-insensitive matching."""
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coords = {}
    coords_lower = {}  # For case-insensitive matching

    for feature in data['features']:
        name = feature['properties']['Name']
        if name and name != 'Delete':
            lon, lat = feature['geometry']['coordinates'][:2]

            # Store with exact name
            coords[name] = {'latitude': lat, 'longitude': lon}

            # Also store lowercase version for case-insensitive matching
            coords_lower[name.lower()] = {'latitude': lat, 'longitude': lon}

            # Store normalized version
            norm_name = normalize_port_name(name)
            if norm_name and norm_name not in coords_lower:
                coords_lower[norm_name] = {'latitude': lat, 'longitude': lon}

    return coords, coords_lower

def load_all_manual_matches():
    """Load all manual matching rules (origin + destination)."""
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    all_matches = {}

    # Load origin matches
    print("  Loading origin normalization rules...")
    with open(base_dir / "reference_data" / "manual_port_matches.json", 'r') as f:
        data = json.load(f)
        origin_matches = data.get('matches', data)
        all_matches.update(origin_matches)
        print(f"    Origin rules: {len(origin_matches)}")

    # Load destination manual matches
    print("  Loading destination manual matches...")
    with open(base_dir / "reference_data" / "british_port_manual_mappings_final.json", 'r') as f:
        data = json.load(f)
        dest_matches = data.get('matches', data)
        all_matches.update(dest_matches)
        print(f"    Destination manual: {len(dest_matches)}")

    # Load destination fuzzy matches
    print("  Loading destination fuzzy matches...")
    with open(base_dir / "reference_data" / "british_ports_case_fuzzy_matches.json", 'r') as f:
        data = json.load(f)
        fuzzy_matches = data.get('matches', data)
        all_matches.update(fuzzy_matches)
        print(f"    Destination fuzzy: {len(fuzzy_matches)}")

    return all_matches

def get_coordinates(port_name, manual_matches, geo_coords, geo_coords_lower):
    """Get coordinates for a port, applying manual matches and case-insensitive matching."""
    if not port_name:
        return None, None

    # Try manual match first (these take precedence)
    if port_name in manual_matches:
        matched_name = manual_matches[port_name]

        # Try exact match
        if matched_name in geo_coords:
            coords = geo_coords[matched_name]
            return coords['latitude'], coords['longitude']

        # Try case-insensitive match
        if matched_name.lower() in geo_coords_lower:
            coords = geo_coords_lower[matched_name.lower()]
            return coords['latitude'], coords['longitude']

        # Try normalized
        norm = normalize_port_name(matched_name)
        if norm in geo_coords_lower:
            coords = geo_coords_lower[norm]
            return coords['latitude'], coords['longitude']

    # Try direct exact match
    if port_name in geo_coords:
        coords = geo_coords[port_name]
        return coords['latitude'], coords['longitude']

    # Try case-insensitive match
    if port_name.lower() in geo_coords_lower:
        coords = geo_coords_lower[port_name.lower()]
        return coords['latitude'], coords['longitude']

    # Try normalized match
    norm = normalize_port_name(port_name)
    if norm in geo_coords_lower:
        coords = geo_coords_lower[norm]
        return coords['latitude'], coords['longitude']

    return None, None

def create_geocoded_database(input_csv, output_csv, geo_coords, geo_coords_lower, manual_matches):
    """Create geocoded database with lat/lon columns."""

    stats = {
        'total': 0,
        'dest_matched': 0,
        'origin_matched': 0,
        'both_matched': 0
    }

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)

        # Add new coordinate fields if not present
        new_fields = []
        if 'destination_latitude' not in fieldnames:
            new_fields.extend(['destination_latitude', 'destination_longitude'])
        if 'origin_latitude' not in fieldnames:
            new_fields.extend(['origin_latitude', 'origin_longitude'])

        output_fieldnames = fieldnames + new_fields

        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()

            for row in reader:
                stats['total'] += 1

                # Get destination coordinates
                # The normalization script updated the port names in place
                dest_port = row.get('destination_port', '')
                dest_lat, dest_lon = get_coordinates(dest_port, manual_matches, geo_coords, geo_coords_lower)

                row['destination_latitude'] = dest_lat if dest_lat is not None else ''
                row['destination_longitude'] = dest_lon if dest_lon is not None else ''

                if dest_lat is not None:
                    stats['dest_matched'] += 1

                # Get origin coordinates
                # The normalization script updated the port names in place
                origin_port = row.get('origin_port', '')
                origin_lat, origin_lon = get_coordinates(origin_port, manual_matches, geo_coords, geo_coords_lower)

                row['origin_latitude'] = origin_lat if origin_lat is not None else ''
                row['origin_longitude'] = origin_lon if origin_lon is not None else ''

                if origin_lat is not None:
                    stats['origin_matched'] += 1

                if dest_lat is not None and origin_lat is not None:
                    stats['both_matched'] += 1

                writer.writerow(row)

                if stats['total'] % 10000 == 0:
                    print(f"  Processed {stats['total']:,} records...")

    return stats

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    print("=" * 80)
    print("CREATING GEOCODED DATABASE")
    print("=" * 80)

    # Load resources
    print("\nLoading GeoJSON coordinates...")
    geo_coords, geo_coords_lower = load_geojson_coords(base_dir / "Ports_Master.geojson")
    print(f"  Loaded {len(geo_coords)} port coordinates")

    print("\nLoading manual matching rules...")
    manual_matches = load_all_manual_matches()
    print(f"  Total manual matches: {len(manual_matches)}")

    # Create geocoded database
    input_csv = base_dir / "parsed_output" / "ttj_shipments_normalized.csv"
    output_csv = base_dir / "final_output" / "ttj_shipments.csv"

    print(f"\nGeocoding database...")
    print(f"  Input: {input_csv}")
    print(f"  Output: {output_csv}")

    stats = create_geocoded_database(input_csv, output_csv, geo_coords, geo_coords_lower, manual_matches)

    # Report results
    print("\n" + "=" * 80)
    print("GEOCODING COMPLETE")
    print("=" * 80)

    print(f"\nTotal records: {stats['total']:,}")
    print(f"\nDestination ports geocoded: {stats['dest_matched']:,} / {stats['total']:,} "
          f"({100*stats['dest_matched']/stats['total']:.1f}%)")
    print(f"Origin ports geocoded: {stats['origin_matched']:,} / {stats['total']:,} "
          f"({100*stats['origin_matched']/stats['total']:.1f}%)")
    print(f"Both origin and destination geocoded: {stats['both_matched']:,} / {stats['total']:,} "
          f"({100*stats['both_matched']/stats['total']:.1f}%)")

    print(f"\n✅ Geocoded database saved to: {output_csv}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
