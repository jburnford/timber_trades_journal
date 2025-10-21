#!/usr/bin/env python3
"""
Generate analytical datasets from normalized TTJ data.
Creates multiple views optimized for different types of analysis.
"""

import csv
import json
import re
from pathlib import Path
from collections import defaultdict, Counter


def extract_year(ship_data):
    """Extract year from ship data (uses publication_year or arrival_year)."""
    # Prefer publication year, fall back to arrival year
    year = ship_data.get('publication_year', '') or ship_data.get('arrival_year', '')
    if year:
        try:
            return int(year)
        except (ValueError, TypeError):
            return None
    return None


def format_date(ship_data):
    """Format date from separate fields."""
    year = ship_data.get('publication_year', '') or ship_data.get('arrival_year', '')
    month = ship_data.get('publication_month', '') or ship_data.get('arrival_month', '')
    day = ship_data.get('publication_day', '') or ship_data.get('arrival_day', '')

    parts = [p for p in [year, month, day] if p]
    return '-'.join(parts) if parts else ''


def load_data(base_dir: Path):
    """Load shipments and cargo data."""

    print("Loading data...")

    # Load shipments
    shipments = {}
    shipments_file = base_dir / "final_output" / "authority_normalized" / "ttj_shipments_authority_normalized.csv"
    with open(shipments_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            shipments[row['record_id']] = row

    # Load cargo (commodity normalized)
    cargo_by_ship = defaultdict(list)
    cargo_file = base_dir / "final_output" / "authority_normalized" / "ttj_cargo_details_commodity_normalized.csv"
    with open(cargo_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cargo_by_ship[row['record_id']].append(row)

    print(f"  Loaded {len(shipments):,} shipments")
    print(f"  Loaded {sum(len(c) for c in cargo_by_ship.values()):,} cargo items")

    return shipments, cargo_by_ship


def generate_detailed_long(shipments, cargo_by_ship, output_dir: Path):
    """
    Dataset 1: Detailed shipments in LONG format (one row per cargo item).

    This is the master file with all detail preserved.
    """

    print("\n1. Generating detailed_shipments_long.csv...")

    output_file = output_dir / "detailed_shipments_long.csv"

    fieldnames = [
        'record_id', 'date', 'year', 'ship_name', 'origin_port', 'destination_port',
        'commodity', 'quantity', 'unit', 'merchant', 'is_steamship', 'source_file'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        row_count = 0
        for record_id, cargos in cargo_by_ship.items():
            ship = shipments.get(record_id, {})
            year = extract_year(ship)
            date = format_date(ship)

            for cargo in cargos:
                writer.writerow({
                    'record_id': record_id,
                    'date': date,
                    'year': year if year else '',
                    'ship_name': ship.get('ship_name', ''),
                    'origin_port': ship.get('origin_port', ''),
                    'destination_port': ship.get('destination_port', ''),
                    'commodity': cargo.get('commodity', ''),
                    'quantity': cargo.get('quantity', ''),
                    'unit': cargo.get('unit', ''),
                    'merchant': ship.get('merchant', ''),
                    'is_steamship': ship.get('is_steamship', ''),
                    'source_file': ship.get('source_file', '')
                })
                row_count += 1

        print(f"   ✓ {row_count:,} rows written")


def generate_trade_routes_by_year(shipments, cargo_by_ship, output_dir: Path):
    """
    Dataset 2: Trade routes aggregated by year.

    Shows how trade patterns changed over time.
    """

    print("\n2. Generating trade_routes_by_year.csv...")

    # Aggregate
    routes = defaultdict(lambda: {
        'num_ships': 0,
        'num_cargo_items': 0,
        'commodities': Counter()
    })

    for record_id, ship in shipments.items():
        year = extract_year(ship)
        origin = ship.get('origin_port', '')
        dest = ship.get('destination_port', '')

        if year and origin and dest:
            key = (origin, dest, year)
            routes[key]['num_ships'] += 1

            # Count cargo items
            cargos = cargo_by_ship.get(record_id, [])
            routes[key]['num_cargo_items'] += len(cargos)

            for cargo in cargos:
                commodity = cargo.get('commodity', '')
                if commodity:
                    routes[key]['commodities'][commodity] += 1

    # Write
    output_file = output_dir / "trade_routes_by_year.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['origin_port', 'destination_port', 'year',
                        'num_ships', 'num_cargo_items', 'top_commodity', 'top_commodity_count'])

        for (origin, dest, year), data in sorted(routes.items()):
            top_commodity = data['commodities'].most_common(1)
            top_name = top_commodity[0][0] if top_commodity else ''
            top_count = top_commodity[0][1] if top_commodity else 0

            writer.writerow([
                origin, dest, year,
                data['num_ships'],
                data['num_cargo_items'],
                top_name,
                top_count
            ])

    print(f"   ✓ {len(routes):,} rows written")


def generate_commodity_flows_by_year(shipments, cargo_by_ship, output_dir: Path):
    """
    Dataset 3: Commodity flows aggregated by year.

    Shows how different commodities were traded over time.
    """

    print("\n3. Generating commodity_flows_by_year.csv...")

    # Aggregate
    commodities = defaultdict(lambda: {
        'num_ships': set(),
        'num_cargo_items': 0,
        'origins': Counter(),
        'destinations': Counter()
    })

    for record_id, cargos in cargo_by_ship.items():
        ship = shipments.get(record_id, {})
        year = extract_year(ship)
        origin = ship.get('origin_port', '')
        dest = ship.get('destination_port', '')

        for cargo in cargos:
            commodity = cargo.get('commodity', '')
            if commodity and year:
                key = (commodity, year)
                commodities[key]['num_ships'].add(record_id)
                commodities[key]['num_cargo_items'] += 1
                if origin:
                    commodities[key]['origins'][origin] += 1
                if dest:
                    commodities[key]['destinations'][dest] += 1

    # Write
    output_file = output_dir / "commodity_flows_by_year.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['commodity', 'year', 'num_ships', 'num_cargo_items',
                        'top_origin', 'top_destination'])

        for (commodity, year), data in sorted(commodities.items()):
            top_origin = data['origins'].most_common(1)
            top_dest = data['destinations'].most_common(1)

            writer.writerow([
                commodity, year,
                len(data['num_ships']),
                data['num_cargo_items'],
                top_origin[0][0] if top_origin else '',
                top_dest[0][0] if top_dest else ''
            ])

    print(f"   ✓ {len(commodities):,} rows written")


def generate_route_commodity_matrix(shipments, cargo_by_ship, output_dir: Path):
    """
    Dataset 4: Route-commodity matrix (combined analysis).

    Shows which commodities traveled on which routes by year.
    """

    print("\n4. Generating route_commodity_matrix.csv...")

    # Aggregate
    matrix = defaultdict(lambda: {
        'num_ships': set(),
        'num_cargo_items': 0
    })

    for record_id, cargos in cargo_by_ship.items():
        ship = shipments.get(record_id, {})
        year = extract_year(ship)
        origin = ship.get('origin_port', '')
        dest = ship.get('destination_port', '')

        if year and origin and dest:
            for cargo in cargos:
                commodity = cargo.get('commodity', '')
                if commodity:
                    key = (origin, dest, commodity, year)
                    matrix[key]['num_ships'].add(record_id)
                    matrix[key]['num_cargo_items'] += 1

    # Write
    output_file = output_dir / "route_commodity_matrix.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['origin_port', 'destination_port', 'commodity', 'year',
                        'num_ships', 'num_cargo_items'])

        for (origin, dest, commodity, year), data in sorted(matrix.items()):
            writer.writerow([
                origin, dest, commodity, year,
                len(data['num_ships']),
                data['num_cargo_items']
            ])

    print(f"   ✓ {len(matrix):,} rows written")


def generate_port_activity_summary(shipments, cargo_by_ship, output_dir: Path):
    """
    Dataset 5: Port activity summary by year.

    Shows port importance over time (both as origin and destination).
    """

    print("\n5. Generating port_activity_summary.csv...")

    # Aggregate
    ports = defaultdict(lambda: {
        'num_ships': set(),
        'num_cargo_items': 0,
        'commodities': Counter()
    })

    for record_id, ship in shipments.items():
        year = extract_year(ship)
        origin = ship.get('origin_port', '')
        dest = ship.get('destination_port', '')
        cargos = cargo_by_ship.get(record_id, [])

        if year:
            # Origin port
            if origin:
                key = (origin, 'origin', year)
                ports[key]['num_ships'].add(record_id)
                ports[key]['num_cargo_items'] += len(cargos)
                for cargo in cargos:
                    commodity = cargo.get('commodity', '')
                    if commodity:
                        ports[key]['commodities'][commodity] += 1

            # Destination port
            if dest:
                key = (dest, 'destination', year)
                ports[key]['num_ships'].add(record_id)
                ports[key]['num_cargo_items'] += len(cargos)
                for cargo in cargos:
                    commodity = cargo.get('commodity', '')
                    if commodity:
                        ports[key]['commodities'][commodity] += 1

    # Write
    output_file = output_dir / "port_activity_summary.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['port_name', 'port_type', 'year', 'num_ships', 'num_cargo_items',
                        'top_commodity_1', 'top_commodity_2', 'top_commodity_3'])

        for (port, port_type, year), data in sorted(ports.items()):
            top_3 = data['commodities'].most_common(3)

            writer.writerow([
                port, port_type, year,
                len(data['num_ships']),
                data['num_cargo_items'],
                top_3[0][0] if len(top_3) > 0 else '',
                top_3[1][0] if len(top_3) > 1 else '',
                top_3[2][0] if len(top_3) > 2 else ''
            ])

    print(f"   ✓ {len(ports):,} rows written")


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    output_dir = base_dir / "final_output" / "analytical_datasets"
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("GENERATING ANALYTICAL DATASETS")
    print("=" * 80)

    # Load data
    shipments, cargo_by_ship = load_data(base_dir)

    # Generate all datasets
    generate_detailed_long(shipments, cargo_by_ship, output_dir)
    generate_trade_routes_by_year(shipments, cargo_by_ship, output_dir)
    generate_commodity_flows_by_year(shipments, cargo_by_ship, output_dir)
    generate_route_commodity_matrix(shipments, cargo_by_ship, output_dir)
    generate_port_activity_summary(shipments, cargo_by_ship, output_dir)

    print("\n" + "=" * 80)
    print("ANALYTICAL DATASETS COMPLETE")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  1. detailed_shipments_long.csv - Master file with all detail")
    print("  2. trade_routes_by_year.csv - Geographic trade patterns")
    print("  3. commodity_flows_by_year.csv - Commodity trends over time")
    print("  4. route_commodity_matrix.csv - Route-commodity combinations")
    print("  5. port_activity_summary.csv - Port importance over time")
    print("=" * 80)


if __name__ == '__main__':
    main()
