#!/usr/bin/env python3
"""
Create geocoded database by applying manual matches and GeoJSON coordinates.

Outputs a new CSV with latitude/longitude columns for both origin and destination ports.
"""

import json
import csv
from pathlib import Path
from difflib import SequenceMatcher

csv.field_size_limit(1000000)

def normalize_port_name(port_name):
    """Normalize port name for matching (remove parenthetical suffixes)."""
    if not port_name:
        return ""
    base_name = port_name.split('(')[0].strip()
    return base_name.lower()

def load_geojson_coords(geojson_path):
    """Load port coordinates from GeoJSON."""
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # UK/Ireland geographic bounds (for preferring UK ports when there are duplicates)
    UK_LAT_MIN, UK_LAT_MAX = 49, 61
    UK_LON_MIN, UK_LON_MAX = -11, 2

    coords = {}
    for feature in data['features']:
        name = feature['properties']['Name']
        if name and name != 'Delete':
            lon, lat = feature['geometry']['coordinates'][:2]
            this_is_uk = (UK_LAT_MIN <= lat <= UK_LAT_MAX and UK_LON_MIN <= lon <= UK_LON_MAX)

            # Store with full name - prefer UK coordinates if duplicate
            if name in coords:
                existing = coords[name]
                existing_is_uk = (UK_LAT_MIN <= existing['latitude'] <= UK_LAT_MAX and
                                 UK_LON_MIN <= existing['longitude'] <= UK_LON_MAX)
                if this_is_uk and not existing_is_uk:
                    coords[name] = {'latitude': lat, 'longitude': lon}
            else:
                coords[name] = {'latitude': lat, 'longitude': lon}

            # For normalized version, prefer UK/Ireland coordinates if duplicate
            norm_name = normalize_port_name(name)

            # Check if this normalized name already exists
            if norm_name in coords:
                # If existing is NOT UK but this one IS UK, replace it
                existing = coords[norm_name]
                existing_is_uk = (UK_LAT_MIN <= existing['latitude'] <= UK_LAT_MAX and
                                 UK_LON_MIN <= existing['longitude'] <= UK_LON_MAX)

                if this_is_uk and not existing_is_uk:
                    coords[norm_name] = {'latitude': lat, 'longitude': lon}
            else:
                coords[norm_name] = {'latitude': lat, 'longitude': lon}

    return coords

def load_manual_matches(matches_path):
    """Load manual port matching rules."""
    with open(matches_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['matches']

def get_coordinates(port_name, manual_matches, geo_coords):
    """Get coordinates for a port, applying manual matches first."""
    if not port_name:
        return None, None

    # Try manual match first
    if port_name in manual_matches:
        matched_name = manual_matches[port_name]
        if matched_name in geo_coords:
            coords = geo_coords[matched_name]
            return coords['latitude'], coords['longitude']
        # Try normalized version
        norm = normalize_port_name(matched_name)
        if norm in geo_coords:
            coords = geo_coords[norm]
            return coords['latitude'], coords['longitude']

    # Try direct match
    if port_name in geo_coords:
        coords = geo_coords[port_name]
        return coords['latitude'], coords['longitude']

    # Try normalized match
    norm = normalize_port_name(port_name)
    if norm in geo_coords:
        coords = geo_coords[norm]
        return coords['latitude'], coords['longitude']

    return None, None

def create_geocoded_database(input_csv, output_csv, geo_coords, manual_matches):
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

        # Add new coordinate fields
        new_fields = [
            'destination_latitude',
            'destination_longitude',
            'origin_latitude',
            'origin_longitude'
        ]

        output_fieldnames = fieldnames + new_fields

        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()

            for row in reader:
                stats['total'] += 1

                # Get destination coordinates
                dest_port = row['destination_port_normalized']
                dest_lat, dest_lon = get_coordinates(dest_port, manual_matches, geo_coords)

                row['destination_latitude'] = dest_lat if dest_lat is not None else ''
                row['destination_longitude'] = dest_lon if dest_lon is not None else ''

                if dest_lat is not None:
                    stats['dest_matched'] += 1

                # Get origin coordinates
                origin_port = row['origin_port_normalized']
                origin_lat, origin_lon = get_coordinates(origin_port, manual_matches, geo_coords)

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
    geo_coords = load_geojson_coords(base_dir / "Ports_Master.geojson")
    print(f"  Loaded {len(geo_coords)} port coordinates")

    print("\nLoading manual matching rules...")
    manual_matches = load_manual_matches(base_dir / "reference_data" / "manual_port_matches.json")
    print(f"  Loaded {len(manual_matches)} manual matches")

    # Create geocoded database
    input_csv = base_dir / "parsed_output" / "ttj_shipments_normalized_v4.3.csv"
    output_csv = base_dir / "parsed_output" / "ttj_shipments_geocoded.csv"

    print("\nGeocoding database...")
    stats = create_geocoded_database(input_csv, output_csv, geo_coords, manual_matches)

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

    print(f"\n✓ Geocoded database saved to: {output_csv}")

    # Calculate ship-based coverage
    print("\n" + "=" * 80)
    print("COVERAGE BY SHIP COUNT")
    print("=" * 80)

    dest_ships_total = 0
    dest_ships_geocoded = 0
    origin_ships_total = 0
    origin_ships_geocoded = 0
    both_geocoded = 0

    with open(output_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dest_ships_total += 1
            origin_ships_total += 1

            has_dest = row['destination_latitude'] and row['destination_latitude'].strip()
            has_origin = row['origin_latitude'] and row['origin_latitude'].strip()

            if has_dest:
                dest_ships_geocoded += 1
            if has_origin:
                origin_ships_geocoded += 1
            if has_dest and has_origin:
                both_geocoded += 1

    print(f"\nShips with destination coordinates: {dest_ships_geocoded:,} / {dest_ships_total:,} "
          f"({100*dest_ships_geocoded/dest_ships_total:.1f}%)")
    print(f"Ships with origin coordinates: {origin_ships_geocoded:,} / {origin_ships_total:,} "
          f"({100*origin_ships_geocoded/origin_ships_total:.1f}%)")
    print(f"Ships with complete routes (both ports): {both_geocoded:,} / {dest_ships_total:,} "
          f"({100*both_geocoded/dest_ships_total:.1f}%)")

if __name__ == '__main__':
    main()
