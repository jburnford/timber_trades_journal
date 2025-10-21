#!/usr/bin/env python3
"""
Final encoding fix for geocoding-ready export.
Fixes UTF-8 double-encoding issues in port names.
"""

import csv
from pathlib import Path

# Define all encoding corrections
ENCODING_FIXES = {
    # Swedish ports
    'GÃ¤vle': 'Gävle',
    'VÃ¤stervik': 'Västervik',
    'MÃ¶nsterÃ¥s': 'Mönsterås',
    'TimrÃ¥': 'Timrå',

    # Spanish ports
    'VilagarcÃ\xada de Arousa': 'Vilagarcía de Arousa',
    'A CoruÃ±a': 'A Coruña',

    # Norwegian ports
    'TÃ¸nsberg': 'Tønsberg',

    # French ports
    'Trois-RiviÃ¨res': 'Trois-Rivières',
    "Pont-l'Abbé": "Pont-l'Abbé",
    'Â\xa0Saint-Brieuc': 'Saint-Brieuc',
    'Â Saint-Brieuc': 'Saint-Brieuc',

    # Any other corrupted patterns
    'GÃ¤': 'Gä',
    'Ã¤': 'ä',
    'Ã¶': 'ö',
    'Ã¥': 'å',
    'Ã¸': 'ø',
    'Ã±': 'ñ',
    'Ã©': 'é',
    'Ã¨': 'è',
    'Ã­': 'í',
}

def fix_encoding(text):
    """Fix double-encoded UTF-8 text."""
    if not text:
        return text

    # Try exact replacements first
    if text in ENCODING_FIXES:
        return ENCODING_FIXES[text]

    # Then try pattern replacements
    fixed = text
    for corrupted, correct in ENCODING_FIXES.items():
        if len(corrupted) <= 3:  # Pattern replacements (like 'Ã¤' -> 'ä')
            fixed = fixed.replace(corrupted, correct)

    return fixed

def fix_shipments_file(input_file, output_file):
    """Fix encoding in shipments CSV."""

    print(f"Reading: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames

        rows = []
        fixed_count = 0

        for row in reader:
            # Fix origin port
            if row['origin_port']:
                original = row['origin_port']
                fixed = fix_encoding(original)
                if fixed != original:
                    row['origin_port'] = fixed
                    fixed_count += 1

            # Fix destination port
            if row['destination_port']:
                original = row['destination_port']
                fixed = fix_encoding(original)
                if fixed != original:
                    row['destination_port'] = fixed
                    fixed_count += 1

            rows.append(row)

    print(f"Fixed {fixed_count:,} encoding issues")

    # Write with proper UTF-8 encoding
    print(f"Writing: {output_file}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Created clean export with proper UTF-8 encoding")

    return fixed_count

def main():
    base_dir = Path(__file__).parent.parent

    print("=" * 80)
    print("FIXING ENCODING FOR GEOCODING EXPORT")
    print("=" * 80)

    # Fix the normalized shipments file
    input_file = base_dir / "final_output" / "authority_normalized" / "ttj_shipments_authority_normalized.csv"
    output_file = base_dir / "final_output" / "authority_normalized" / "ttj_shipments_geocoding_ready.csv"

    fixed_count = fix_shipments_file(input_file, output_file)

    # Also create a unique ports list for geocoding
    print("\nCreating unique ports list for geocoding...")

    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        origin_ports = set()
        dest_ports = set()

        for row in reader:
            if row['origin_port']:
                origin_ports.add(row['origin_port'])
            if row['destination_port']:
                dest_ports.add(row['destination_port'])

    # Export unique ports
    ports_file = base_dir / "final_output" / "authority_normalized" / "unique_ports_for_geocoding.csv"
    with open(ports_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['port_name', 'port_type', 'latitude', 'longitude', 'country', 'notes'])

        for port in sorted(origin_ports):
            writer.writerow([port, 'origin', '', '', '', ''])

        for port in sorted(dest_ports):
            if port not in origin_ports:  # Don't duplicate
                writer.writerow([port, 'destination', '', '', '', ''])

    print(f"✓ Created: {ports_file}")
    print(f"  Origin ports: {len(origin_ports):,}")
    print(f"  Destination ports: {len(dest_ports):,}")
    print(f"  Total unique: {len(origin_ports | dest_ports):,}")

    print("\n" + "=" * 80)
    print("GEOCODING-READY FILES CREATED")
    print("=" * 80)
    print(f"Shipments: {output_file}")
    print(f"Ports list: {ports_file}")
    print("\nThese files have proper UTF-8 encoding and can be used for:")
    print("  - Geocoding services (Google, OpenCage, etc.)")
    print("  - GIS software (QGIS, ArcGIS)")
    print("  - Mapping libraries (Folium, Leaflet)")
    print("=" * 80)

if __name__ == '__main__':
    main()
