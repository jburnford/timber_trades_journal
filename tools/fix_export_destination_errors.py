#!/usr/bin/env python3
"""
Fix export destination parsing errors (REDWOOD, QUEBEC, NEW YORK).

These are not actual export destinations but parsing errors:
- REDWOOD: Commodity section header from pricing table
- QUEBEC/NEW YORK: Correspondence section headers or narrative text
"""

import csv
import re
from pathlib import Path
from collections import defaultdict

csv.field_size_limit(1000000)

def extract_actual_destination_from_redwood(row, all_records_by_file):
    """
    REDWOOD records are ALL parsing errors.

    REDWOOD appears as a commodity section header in pricing tables
    and was incorrectly associated with ship import records.

    All 297 REDWOOD records should be set to empty.
    """
    # All REDWOOD records are parsing errors
    # The "ships" are actually cargo items like "logs pia.", "cedar.", "sacks chalk."
    return ''

def is_narrative_text(ship_name, raw_line):
    """
    Detect if this is narrative text, not a ship record.

    Indicators:
    - Long ship names (> 40 chars)
    - Contains common narrative words
    - No ship-like structure
    """
    if not ship_name or ship_name == 'MISSING_FROM_OCR':
        return True

    # Check for narrative patterns
    narrative_markers = [
        'the ', 'and ', 'to ', 'of ', 'in ', 'for ', 'with ',
        'every ', 'them ', 'would ', 'been ', 'will ', 'are ',
        'number and tonnage', 'left column', 'last', 'from our'
    ]

    ship_lower = ship_name.lower()
    for marker in narrative_markers:
        if marker in ship_lower:
            return True

    # Very long ship names are likely narrative
    if len(ship_name) > 40:
        return True

    return False

def is_legitimate_ship_record(raw_line):
    """
    Check if raw line looks like legitimate ship record.

    Pattern: "Ship @ Port,—cargo details"
    """
    # Look for @ symbol (indicates ship arrival format)
    if '@' in raw_line:
        return True

    # Look for ship-to-port pattern with em-dash
    if re.search(r'\w+\s*@\s*\w+,?—', raw_line):
        return True

    return False

def fix_quebec_new_york(dest_port, ship_name, raw_line):
    """
    Fix QUEBEC/NEW YORK destinations.

    Strategy:
    1. If legitimate ship record (with @), keep as export record
    2. If narrative text, set to empty
    3. Otherwise, set to empty (parsing error)
    """
    # Check if narrative text
    if is_narrative_text(ship_name, raw_line):
        return ''

    # Check if legitimate ship format
    if is_legitimate_ship_record(raw_line):
        # This might be a legitimate export record
        # Keep the destination but mark for review
        return dest_port

    # Default: parsing error
    return ''

def load_all_records_by_file(input_csv):
    """Load all records grouped by source file and line number for context checking."""
    all_records = defaultdict(lambda: defaultdict(dict))

    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row['source_file']
            try:
                line_num = int(row['line_number'])
            except:
                continue

            all_records[source][line_num] = {
                'raw_line': row['raw_line'],
                'destination': row['destination_port']
            }

    return all_records

def apply_corrections(input_csv, output_csv):
    """Apply corrections to REDWOOD, QUEBEC, and NEW YORK destination errors."""

    print("Loading records for context analysis...")
    all_records_by_file = load_all_records_by_file(input_csv)

    print("Applying corrections...")

    stats = {
        'total': 0,
        'redwood_fixed': 0,
        'redwood_to_london': 0,
        'redwood_to_hull': 0,
        'redwood_to_empty': 0,
        'quebec_fixed': 0,
        'quebec_kept': 0,
        'quebec_to_empty': 0,
        'newyork_fixed': 0,
        'newyork_kept': 0,
        'newyork_to_empty': 0,
    }

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                stats['total'] += 1

                dest_raw = row['destination_port'].strip()
                dest_norm = row['destination_port_normalized'].strip()

                # Fix REDWOOD
                if dest_raw == 'REDWOOD':
                    new_dest = extract_actual_destination_from_redwood(row, all_records_by_file)
                    row['destination_port_normalized'] = new_dest
                    stats['redwood_fixed'] += 1

                    if new_dest == 'London':
                        stats['redwood_to_london'] += 1
                    elif new_dest == 'Hull':
                        stats['redwood_to_hull'] += 1
                    else:
                        stats['redwood_to_empty'] += 1

                # Fix QUEBEC
                elif dest_raw == 'QUEBEC':
                    new_dest = fix_quebec_new_york(
                        dest_raw,
                        row['ship_name'],
                        row['raw_line']
                    )
                    row['destination_port_normalized'] = new_dest
                    stats['quebec_fixed'] += 1

                    if new_dest:
                        stats['quebec_kept'] += 1
                    else:
                        stats['quebec_to_empty'] += 1

                # Fix NEW YORK
                elif 'NEW YORK' in dest_raw:
                    new_dest = fix_quebec_new_york(
                        dest_raw,
                        row['ship_name'],
                        row['raw_line']
                    )
                    row['destination_port_normalized'] = new_dest
                    stats['newyork_fixed'] += 1

                    if new_dest:
                        stats['newyork_kept'] += 1
                    else:
                        stats['newyork_to_empty'] += 1

                writer.writerow(row)

                if stats['total'] % 10000 == 0:
                    print(f"  Processed {stats['total']:,} records...")

    return stats

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    parsed_dir = base_dir / "parsed_output"

    print("=" * 80)
    print("FIXING EXPORT DESTINATION PARSING ERRORS")
    print("=" * 80)
    print("\nIssues:")
    print("  1. REDWOOD (297 records) - Commodity section header")
    print("  2. QUEBEC (161 records) - Correspondence section header")
    print("  3. NEW YORK (201 records) - Mixed section headers/narrative")
    print("\nTotal affected: 659 records")

    input_csv = parsed_dir / "ttj_shipments_normalized_v4.2.csv"
    output_csv = parsed_dir / "ttj_shipments_normalized_v4.3.csv"

    stats = apply_corrections(input_csv, output_csv)

    print("\n" + "=" * 80)
    print("CORRECTIONS APPLIED")
    print("=" * 80)

    print(f"\nREDWOOD corrections ({stats['redwood_fixed']} records):")
    print(f"  → London: {stats['redwood_to_london']}")
    print(f"  → Hull: {stats['redwood_to_hull']}")
    print(f"  → Empty (parsing error): {stats['redwood_to_empty']}")

    print(f"\nQUEBEC corrections ({stats['quebec_fixed']} records):")
    print(f"  → Kept (legitimate export): {stats['quebec_kept']}")
    print(f"  → Empty (narrative text): {stats['quebec_to_empty']}")

    print(f"\nNEW YORK corrections ({stats['newyork_fixed']} records):")
    print(f"  → Kept (legitimate export): {stats['newyork_kept']}")
    print(f"  → Empty (narrative text): {stats['newyork_to_empty']}")

    print(f"\n✓ Output saved to: {output_csv}")
    print(f"\nTotal records processed: {stats['total']:,}")

if __name__ == '__main__':
    main()
