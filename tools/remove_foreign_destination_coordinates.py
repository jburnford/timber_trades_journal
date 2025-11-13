#!/usr/bin/env python3
"""
Remove coordinates from records with non-UK/Ireland destinations.

The Timber Trades Journal documented British timber IMPORTS.
Records with foreign destinations (Boston MA, Bremen, New York, etc.) are parsing errors.
"""

import csv
from pathlib import Path

csv.field_size_limit(1000000)

# UK/Ireland geographic bounds
UK_LAT_MIN, UK_LAT_MAX = 49, 61
UK_LON_MIN, UK_LON_MAX = -11, 2

def is_foreign_destination(dest_lat, dest_lon):
    """Check if destination coordinates are outside UK/Ireland."""
    if not dest_lat or not dest_lon:
        return False

    try:
        lat = float(dest_lat)
        lon = float(dest_lon)

        # Check if outside UK/Ireland bounds
        if not (UK_LAT_MIN <= lat <= UK_LAT_MAX and UK_LON_MIN <= lon <= UK_LON_MAX):
            return True

        return False
    except (ValueError, TypeError):
        return False

def remove_foreign_destination_coordinates(input_csv, output_csv):
    """Remove coordinates from records with foreign destinations."""

    stats = {
        'total': 0,
        'removed': 0,
        'by_destination': {}
    }

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                stats['total'] += 1

                dest = row.get('destination_port', '')
                dest_lat = row.get('destination_latitude', '')
                dest_lon = row.get('destination_longitude', '')

                # Check if destination is outside UK/Ireland
                if is_foreign_destination(dest_lat, dest_lon):
                    # Track which destinations are being removed
                    if dest not in stats['by_destination']:
                        stats['by_destination'][dest] = 0
                    stats['by_destination'][dest] += 1

                    # Clear all coordinates
                    row['destination_latitude'] = ''
                    row['destination_longitude'] = ''
                    row['origin_latitude'] = ''
                    row['origin_longitude'] = ''
                    stats['removed'] += 1

                    if stats['removed'] <= 10:
                        origin = row.get('origin_port', '')
                        print(f"  Removed coords: {origin} → {dest}")
                        print(f"    Coords were: ({dest_lat}, {dest_lon})")

                writer.writerow(row)

                if stats['total'] % 10000 == 0:
                    print(f"  Processed {stats['total']:,} records...")

    return stats

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    print("=" * 80)
    print("REMOVING COORDINATES FROM FOREIGN DESTINATION RECORDS")
    print("=" * 80)

    input_csv = base_dir / "final_output" / "ttj_shipments.csv"
    output_csv = base_dir / "final_output" / "ttj_shipments.csv.tmp"

    print("\nRemoving coordinates from records with non-UK/Ireland destinations...")
    print("(These are likely parsing errors where origin/destination were swapped)\n")

    stats = remove_foreign_destination_coordinates(input_csv, output_csv)

    # Replace original with updated version
    import shutil
    shutil.move(str(output_csv), str(input_csv))

    # Report results
    print("\n" + "=" * 80)
    print("COORDINATE REMOVAL COMPLETE")
    print("=" * 80)

    print(f"\nTotal records: {stats['total']:,}")
    print(f"Coordinates removed: {stats['removed']:,} ({100*stats['removed']/stats['total']:.2f}%)")
    print(f"Records with coordinates: {stats['total'] - stats['removed']:,}")

    print("\n\nBreakdown by destination:")
    print("-" * 60)
    for dest, count in sorted(stats['by_destination'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {dest:40} {count:,} records")

    print(f"\n✓ Updated file: {input_csv}")

if __name__ == '__main__':
    main()
