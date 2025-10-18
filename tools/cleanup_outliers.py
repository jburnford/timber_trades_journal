#!/usr/bin/env python3
"""
Cleanup obvious outliers/OCR errors from normalized data.
Addresses issues identified in outlier analysis.
"""

import csv
import re
from pathlib import Path
from collections import Counter


def is_obvious_error(value: str, field_type: str) -> bool:
    """
    Check if a value is an obvious OCR error or parsing artifact.

    Args:
        value: The field value
        field_type: 'port' or 'commodity'

    Returns:
        True if obvious error
    """
    if not value or not value.strip():
        return False

    value = value.strip()
    value_lower = value.lower()

    # Universal checks
    if len(value) <= 2 and value not in ['Mo', 'Mo.']:  # Mo is a real port
        return True

    if value in ['---', '--', '-', '.', '&', 'and', 'or']:
        return True

    # Port-specific checks
    if field_type == 'port':
        # Commodity words as ports
        commodity_words = ['deals', 'timber', 'staves', 'lathwood', 'pitwood',
                          'oak staves', 'props', 'ends', 'teak']
        if value_lower in commodity_words:
            return True

        # Journal artifacts
        if any(word in value_lower for word in ['journal', 'errata', 'imports',
                                                  'freights', 'failures', 'liquidations',
                                                  'trade items', 'dividends', 'bills of sale']):
            return True

        # Very long strings (likely OCR garbage)
        if len(value) > 150:
            return True

        # Starts with lowercase (fragment)
        if value[0].islower() and value not in ['and', 'from Halifax', 'app']:
            return True

    # Commodity-specific checks
    if field_type == 'commodity':
        # Single letters/numbers
        if len(value) == 1:
            return True

        # Common placeholders
        if value_lower in ['order', 'nil', 'ditto', 'do.', 'do']:
            return True

    return False


def infer_port_from_context(record_id: int, all_records: list, field: str) -> str:
    """
    Try to infer missing/error port from surrounding records.

    Args:
        record_id: Current record ID
        all_records: All records in order
        field: 'origin_port' or 'destination_port'

    Returns:
        Inferred port or empty string
    """
    # Look at previous and next few records
    context_range = 10

    nearby_ports = []
    for i in range(max(0, record_id - context_range),
                   min(len(all_records), record_id + context_range)):
        if i != record_id and all_records[i][field]:
            port = all_records[i][field]
            # Don't use if it's also an error
            if not is_obvious_error(port, 'port'):
                nearby_ports.append(port)

    # Use most common nearby port
    if nearby_ports:
        return Counter(nearby_ports).most_common(1)[0][0]

    return ""


def cleanup_normalized_data(input_dir: Path, output_dir: Path):
    """
    Clean up obvious errors from normalized data.

    Args:
        input_dir: Directory with normalized CSVs
        output_dir: Directory for cleaned CSVs
    """
    output_dir.mkdir(exist_ok=True)
    csv.field_size_limit(1000000)

    stats = {
        'total_ships': 0,
        'origin_errors_fixed': 0,
        'origin_errors_inferred': 0,
        'dest_errors_fixed': 0,
        'dest_artifacts_removed': 0,
        'commodity_errors_fixed': 0
    }

    print("=" * 80)
    print("CLEANING UP OUTLIERS")
    print("=" * 80)

    # First pass: load all records to enable context inference
    print("\nLoading records for context analysis...")
    all_records = []
    with open(input_dir / 'ttj_shipments_normalized.csv', 'r', encoding='utf-8') as f:
        all_records = list(csv.DictReader(f))

    # Clean shipments
    print("\nCleaning shipments...")
    shipments_out = output_dir / 'ttj_shipments_cleaned.csv'

    with open(input_dir / 'ttj_shipments_normalized.csv', 'r', encoding='utf-8') as f_in, \
         open(shipments_out, 'w', newline='', encoding='utf-8') as f_out:

        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()

        for idx, row in enumerate(reader):
            stats['total_ships'] += 1

            # Clean origin port
            if is_obvious_error(row['origin_port'], 'port'):
                original = row['origin_port']
                # Try to infer from context
                inferred = infer_port_from_context(idx, all_records, 'origin_port')
                if inferred:
                    row['origin_port'] = inferred
                    stats['origin_errors_inferred'] += 1
                    print(f"  Record {row['record_id']}: '{original}' → '{inferred}' (inferred)")
                else:
                    row['origin_port'] = ""
                    stats['origin_errors_fixed'] += 1
                    print(f"  Record {row['record_id']}: '{original}' → (removed)")

            # Clean destination port
            if is_obvious_error(row['destination_port'], 'port'):
                original = row['destination_port']
                inferred = infer_port_from_context(idx, all_records, 'destination_port')
                if inferred:
                    row['destination_port'] = inferred
                    stats['dest_errors_fixed'] += 1
                    print(f"  Record {row['record_id']}: '{original}' → '{inferred}' (inferred)")
                else:
                    row['destination_port'] = ""
                    stats['dest_errors_fixed'] += 1
                    print(f"  Record {row['record_id']}: '{original}' → (removed)")

            # Consolidate dock/wharf names to parent city
            if row['destination_port']:
                dest = row['destination_port']
                # Pattern: "CITY (details)" or "CITY DOCK/WHARF"

                # Remove dock/wharf details from London
                if dest.startswith('London (') and dest.endswith(')'):
                    row['destination_port'] = 'London'
                    stats['dest_artifacts_removed'] += 1

                # Generic dock/wharf/buoy consolidation
                elif any(word in dest.lower() for word in ['buoys', 'buoy', 'wharf', 'stairs']):
                    # Extract city name (first word usually)
                    parts = dest.split()
                    if len(parts) >= 2:
                        # Keep first word as city
                        row['destination_port'] = parts[0]
                        stats['dest_artifacts_removed'] += 1

            writer.writerow(row)

            if stats['total_ships'] % 5000 == 0:
                print(f"  Processed {stats['total_ships']:,} ships...")

    # Clean cargo details
    print("\nCleaning cargo details...")
    cargo_out = output_dir / 'ttj_cargo_details_cleaned.csv'

    total_cargo = 0
    with open(input_dir / 'ttj_cargo_details_normalized.csv', 'r', encoding='utf-8') as f_in, \
         open(cargo_out, 'w', newline='', encoding='utf-8') as f_out:

        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            total_cargo += 1

            # Clean commodity
            if is_obvious_error(row['commodity'], 'commodity'):
                original = row['commodity']
                row['commodity'] = ""
                stats['commodity_errors_fixed'] += 1
                if stats['commodity_errors_fixed'] <= 20:  # Limit output
                    print(f"  Cargo {row['cargo_id']}: '{original}' → (removed)")

            # Additional commodity normalizations based on outlier analysis
            comm = row['commodity'].lower().strip()

            # Singular/plural fixes
            if comm == 'lath':
                row['commodity'] = 'laths'
                stats['commodity_errors_fixed'] += 1
            elif comm == 'flooring':
                row['commodity'] = 'floorings'

            writer.writerow(row)

            if total_cargo % 10000 == 0:
                print(f"  Processed {total_cargo:,} cargo items...")

    # Print summary
    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print(f"Ships processed: {stats['total_ships']:,}")
    print(f"  Origin port errors removed: {stats['origin_errors_fixed']}")
    print(f"  Origin ports inferred from context: {stats['origin_errors_inferred']}")
    print(f"  Destination port errors fixed: {stats['dest_errors_fixed']}")
    print(f"  Destination port artifacts consolidated: {stats['dest_artifacts_removed']}")
    print(f"\nCargo items processed: {total_cargo:,}")
    print(f"  Commodity errors removed: {stats['commodity_errors_fixed']}")
    print(f"\nOutput files:")
    print(f"  {shipments_out}")
    print(f"  {cargo_out}")
    print("=" * 80)


def main():
    input_dir = Path("/home/jic823/TTJ Forest of Numbers/final_output/normalized")
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/final_output/cleaned")

    print("=" * 80)
    print("TTJ DATA CLEANUP - OUTLIER REMOVAL")
    print("=" * 80)
    print(f"Input: {input_dir}")
    print(f"Output: {output_dir}")
    print("\nRemoving obvious OCR errors and artifacts...")

    cleanup_normalized_data(input_dir, output_dir)


if __name__ == '__main__':
    main()
