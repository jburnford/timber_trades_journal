#!/usr/bin/env python3
"""
Remove coordinates from records where British ports appear as origins.

These are likely parsing errors where destination/origin were swapped.
Rather than reparse, we simply remove coordinates so they don't get mapped.
"""

import csv
from pathlib import Path

csv.field_size_limit(1000000)

# British ports that should rarely/never be origins
BRITISH_PORTS = [
    'London', 'Liverpool', 'Greenock', 'Glasgow', 'Dundee', 'Hull',
    'Bristol', 'Cardiff', 'Newcastle upon Tyne', 'Leith', 'Southampton',
    'Plymouth', 'Portsmouth', 'Belfast', 'Dublin', 'Cork', 'Newport',
    'Grimsby', 'Lynn', 'Poole', 'Wick', 'Goole', 'Tyne'
]

def should_remove_coordinates(origin_normalized):
    """Check if this record has a British port as origin (likely error)."""
    if not origin_normalized:
        return False

    # Check if any British port appears in the origin
    for port in BRITISH_PORTS:
        if port in origin_normalized:
            return True

    return False

def remove_swapped_coordinates(input_csv, output_csv):
    """Remove coordinates from records with British ports as origins."""

    stats = {
        'total': 0,
        'removed': 0
    }

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                stats['total'] += 1

                origin = row['origin_port_normalized']

                # Check if this has a British port as origin (likely swap error)
                if should_remove_coordinates(origin):
                    # Clear all coordinates
                    row['destination_latitude'] = ''
                    row['destination_longitude'] = ''
                    row['origin_latitude'] = ''
                    row['origin_longitude'] = ''
                    stats['removed'] += 1

                    if stats['removed'] <= 10:
                        print(f"  Removed coords: {origin} → {row['destination_port_normalized']}")

                writer.writerow(row)

                if stats['total'] % 10000 == 0:
                    print(f"  Processed {stats['total']:,} records...")

    return stats

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    print("=" * 80)
    print("REMOVING COORDINATES FROM LIKELY SWAPPED RECORDS")
    print("=" * 80)

    input_csv = base_dir / "parsed_output" / "ttj_shipments_geocoded.csv"
    output_csv = base_dir / "parsed_output" / "ttj_shipments_geocoded.csv.tmp"

    print("\nRemoving coordinates from records with British ports as origins...")
    print("(These are likely parsing errors where origin/destination were swapped)\n")

    stats = remove_swapped_coordinates(input_csv, output_csv)

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

    print(f"\n✓ Updated file: {input_csv}")

if __name__ == '__main__':
    main()
