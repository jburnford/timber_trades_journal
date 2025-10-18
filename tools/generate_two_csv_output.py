#!/usr/bin/env python3
"""
Generate two-CSV output from parsed shipment data:
1. ttj_shipments.csv - One row per ship arrival
2. ttj_cargo_details.csv - Multiple rows per ship (one per cargo item)
"""

import csv
from pathlib import Path
from cargo_parser import CargoParser


def generate_two_csv_output(input_csv: Path, output_dir: Path):
    """
    Generate shipments and cargo_details CSV files.

    Args:
        input_csv: Path to ttj_shipments_multipage.csv
        output_dir: Directory for output files
    """
    output_dir.mkdir(exist_ok=True)
    csv.field_size_limit(1000000)

    parser = CargoParser()

    # Output files
    shipments_file = output_dir / "ttj_shipments.csv"
    cargo_details_file = output_dir / "ttj_cargo_details.csv"

    # Open output files
    with open(input_csv, 'r', encoding='utf-8') as f_in, \
         open(shipments_file, 'w', newline='', encoding='utf-8') as f_ships, \
         open(cargo_details_file, 'w', newline='', encoding='utf-8') as f_cargo:

        reader = csv.DictReader(f_in)

        # Shipments CSV - main ship arrival records
        ship_fields = [
            'record_id',
            'source_file',
            'line_number',
            'ship_name',
            'origin_port',
            'destination_port',
            'merchant',
            'arrival_day',
            'arrival_month',
            'arrival_year',
            'publication_day',
            'publication_month',
            'publication_year',
            'is_steamship',
            'format_type',
            'confidence'
        ]
        ship_writer = csv.DictWriter(f_ships, fieldnames=ship_fields)
        ship_writer.writeheader()

        # Cargo details CSV - cargo line items
        cargo_fields = [
            'cargo_id',
            'record_id',
            'source_file',
            'line_number',
            'quantity',
            'unit',
            'commodity',
            'merchant',
            'raw_cargo_segment'
        ]
        cargo_writer = csv.DictWriter(f_cargo, fieldnames=cargo_fields)
        cargo_writer.writeheader()

        record_id = 0
        cargo_id = 0

        stats = {
            'total_ships': 0,
            'total_cargo_items': 0,
            'ships_with_cargo_details': 0,
            'ships_with_merchant': 0
        }

        for row in reader:
            record_id += 1
            stats['total_ships'] += 1

            # Write shipment record
            ship_record = {
                'record_id': record_id,
                'source_file': row['source_file'],
                'line_number': row['line_number'],
                'ship_name': row['ship_name'],
                'origin_port': row['origin_port'],
                'destination_port': row['destination_port'],
                'merchant': row['merchant'],  # From parser (standard/condensed formats)
                'arrival_day': row['arrival_day'],
                'arrival_month': row['arrival_month'],
                'arrival_year': row['arrival_year'],
                'publication_day': row['publication_day'],
                'publication_month': row['publication_month'],
                'publication_year': row['publication_year'],
                'is_steamship': row['is_steamship'],
                'format_type': row['format_type'],
                'confidence': row['confidence']
            }
            ship_writer.writerow(ship_record)

            if ship_record['merchant']:
                stats['ships_with_merchant'] += 1

            # Parse cargo field to extract items
            cargo_items = parser.parse_cargo_string(row['cargo'])

            if cargo_items:
                stats['ships_with_cargo_details'] += 1
                stats['total_cargo_items'] += len(cargo_items)

                for item in cargo_items:
                    cargo_id += 1

                    # Use merchant from cargo item if available, otherwise from ship record
                    merchant = item.merchant if item.merchant else row['merchant']

                    cargo_record = {
                        'cargo_id': cargo_id,
                        'record_id': record_id,
                        'source_file': row['source_file'],
                        'line_number': row['line_number'],
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'commodity': item.commodity,
                        'merchant': merchant,
                        'raw_cargo_segment': item.raw_text
                    }
                    cargo_writer.writerow(cargo_record)

            # Progress indicator
            if record_id % 5000 == 0:
                print(f"  Processed {record_id:,} ships, {stats['total_cargo_items']:,} cargo items...")

    # Print summary
    print("\n" + "=" * 80)
    print("TWO-CSV OUTPUT GENERATION COMPLETE")
    print("=" * 80)
    print(f"Ship records: {stats['total_ships']:,}")
    print(f"  With merchant data: {stats['ships_with_merchant']:,} ({100*stats['ships_with_merchant']/stats['total_ships']:.1f}%)")
    print(f"  With cargo details: {stats['ships_with_cargo_details']:,} ({100*stats['ships_with_cargo_details']/stats['total_ships']:.1f}%)")
    print(f"\nCargo line items: {stats['total_cargo_items']:,}")
    print(f"  Average items per ship: {stats['total_cargo_items']/stats['total_ships']:.1f}")
    print(f"\nOutput files:")
    print(f"  Shipments: {shipments_file}")
    print(f"  Cargo details: {cargo_details_file}")
    print("=" * 80)


def main():
    input_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_multipage.csv")
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/final_output")

    print("=" * 80)
    print("GENERATING TWO-CSV OUTPUT")
    print("=" * 80)
    print(f"Input: {input_csv}")
    print(f"Output directory: {output_dir}")
    print()

    generate_two_csv_output(input_csv, output_dir)


if __name__ == '__main__':
    main()
