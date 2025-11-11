#!/usr/bin/env python3
"""
Phase 4: Extract ships from hyphen format records.
Format: Ship-Port-Cargo-Merchant ; Ship-Port-Cargo-Merchant ; ...
"""
import csv
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple

csv.field_size_limit(sys.maxsize)

MONTH_MAP = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
    'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
}

def parse_month(month_str: str) -> int:
    """Convert month name or number string to integer."""
    if not month_str:
        return 1
    try:
        return int(month_str)
    except ValueError:
        return MONTH_MAP.get(month_str, 1)

@dataclass
class ShipRecord:
    source_file: str
    line_number: int
    ship_name: str
    origin_port: str
    destination_port: str
    cargo: str
    merchant: str
    arrival_day: Optional[int]
    arrival_month: Optional[int]
    arrival_year: int
    publication_day: Optional[int]
    publication_month: Optional[int]
    publication_year: int
    is_steamship: bool
    raw_segment: str
    extraction_method: str  # 'HYPHEN_SPLIT'
    needs_review: bool      # True for hyphen format extractions
    original_extracted_ship: str  # The ship that was originally extracted

def extract_ships_from_hyphen_line(raw_line: str, source_file: str, line_number: int,
                                     destination_port: str, pub_date: Tuple,
                                     original_ship: str) -> List[ShipRecord]:
    """
    Extract ships from hyphen-based format with semicolon separators.
    Format: Ship (s)-Port-Cargo-Merchant ; Ship-Port-Cargo-Merchant ; ...
    """
    ships = []
    pub_year, pub_month, pub_day = pub_date

    # Split on semicolons to get individual ship entries
    entries = raw_line.split(';')

    for entry in entries:
        entry = entry.strip()
        if not entry or len(entry) < 10:
            continue

        try:
            # Split on hyphens
            # But be careful - cargo might contain hyphens (like "1,715 deals")
            # Strategy: Look for pattern Ship-Port-Cargo where Ship and Port don't have commas

            # Find first hyphen (after ship name)
            first_hyphen = entry.find('-')
            if first_hyphen == -1:
                continue

            ship_name = entry[:first_hyphen].strip()

            # Check for steamship marker
            is_steamship = '(s)' in ship_name or '(S)' in ship_name
            ship_name = ship_name.replace('(s)', '').replace('(S)', '').strip()

            # Skip if ship name is too short or too long
            if len(ship_name) < 2 or len(ship_name) > 100:
                continue

            # Find second hyphen (after port)
            remainder = entry[first_hyphen + 1:]
            second_hyphen = remainder.find('-')

            if second_hyphen == -1:
                # Only ship-port, no cargo/merchant
                origin_port = remainder.strip()
                cargo = ''
                merchant = ''
            else:
                origin_port = remainder[:second_hyphen].strip()

                # Everything after second hyphen is cargo-merchant
                cargo_merchant = remainder[second_hyphen + 1:].strip()

                # Try to split cargo from merchant
                # Look for last hyphen that might separate merchant
                # Merchant names are usually capitalized words/names
                # Cargo contains numbers and commas

                # Simple heuristic: Last hyphen followed by capitalized words is likely merchant
                parts = cargo_merchant.rsplit('-', 1)
                if len(parts) == 2:
                    cargo = parts[0].strip()
                    merchant = parts[1].strip()
                else:
                    cargo = cargo_merchant
                    merchant = ''

            # Skip if port is too long (likely parsing error)
            if len(origin_port) > 100:
                continue

            # Truncate overly long fields
            cargo = cargo[:500] if len(cargo) > 500 else cargo
            merchant = merchant[:200] if len(merchant) > 200 else merchant

            # Create raw segment for reference
            raw_segment = entry[:500] if len(entry) <= 500 else entry[:500] + '...'

            ships.append(ShipRecord(
                source_file=source_file,
                line_number=line_number,
                ship_name=ship_name,
                origin_port=origin_port,
                destination_port=destination_port,
                cargo=cargo,
                merchant=merchant,
                arrival_day=None,
                arrival_month=None,
                arrival_year=pub_year,
                publication_day=pub_day,
                publication_month=pub_month,
                publication_year=pub_year,
                is_steamship=is_steamship,
                raw_segment=raw_segment,
                extraction_method='HYPHEN_SPLIT',
                needs_review=True,
                original_extracted_ship=original_ship
            ))

        except Exception as e:
            # Continue processing other ships even if one fails
            continue

    return ships

def extract_hyphen_format_records(categories_csv: Path, main_csv: Path, output_csv: Path):
    """Extract ships from hyphen format records."""

    print("="*80)
    print("PHASE 4: EXTRACTING SHIPS FROM HYPHEN FORMAT RECORDS")
    print("="*80)

    # Step 1: Read categorization to find hyphen format records
    print("\nStep 1: Finding hyphen format records...")
    hyphen_records = []

    with open(categories_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Look for records with HYPHEN_SEMICOLON format or high hyphen count with low @ count
            if row['format_type'] == 'HYPHEN_SEMICOLON':
                hyphen_records.append({
                    'source_file': row['source_file'],
                    'line_number': int(row['line_number']),
                    'extracted_ship': row['extracted_ship'],
                    'char_count': int(row['char_count']),
                    'estimated_ships': int(row['estimated_total_ships']),
                    'hyphens': int(row['hyphens']),
                    'semicolons': int(row['semicolons'])
                })

    print(f"Found {len(hyphen_records)} hyphen format records")

    if hyphen_records:
        total_estimated = sum(r['estimated_ships'] for r in hyphen_records)
        print(f"  Estimated ships: {total_estimated}")
        print(f"\nTop 10 hyphen format records:")
        for i, rec in enumerate(sorted(hyphen_records, key=lambda x: x['estimated_ships'], reverse=True)[:10], 1):
            print(f"  [{i:2}] {rec['source_file'][:50]:50} | Ships: {rec['estimated_ships']:3} | Hyphens: {rec['hyphens']:4} | Semicolons: {rec['semicolons']:3}")

    # Step 2: Read main CSV to get full raw_line for each record
    print(f"\nStep 2: Loading full raw_line data from main CSV...")

    hyphen_data = {}
    with open(main_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check if this row matches any hyphen record
            for hyphen in hyphen_records:
                if (row['source_file'] == hyphen['source_file'] and
                    int(row['line_number']) == hyphen['line_number']):
                    # Skip records with missing year
                    if not row['publication_year']:
                        continue

                    hyphen_data[hyphen['line_number']] = {
                        'raw_line': row['raw_line'],
                        'destination_port': row['destination_port'],
                        'publication_year': int(row['publication_year']),
                        'publication_month': parse_month(row['publication_month']),
                        'publication_day': int(row['publication_day']) if row['publication_day'] else 1,
                        'original_ship': row['ship_name']
                    }

    print(f"Loaded {len(hyphen_data)} hyphen format raw_line entries")

    # Step 3: Extract ships from each hyphen format record
    print("\nStep 3: Extracting ships from hyphen format records...")
    all_extracted_ships = []

    for idx, hyphen in enumerate(hyphen_records, 1):
        line_num = hyphen['line_number']
        if line_num not in hyphen_data:
            print(f"  WARNING: Could not find raw_line for {hyphen['source_file']}")
            continue

        data = hyphen_data[line_num]
        raw_line = data['raw_line']

        print(f"  [{idx:2}/{len(hyphen_records)}] {hyphen['source_file'][:60]:60} | Expected: {hyphen['estimated_ships']:3}")

        ships = extract_ships_from_hyphen_line(
            raw_line=raw_line,
            source_file=hyphen['source_file'],
            line_number=line_num,
            destination_port=data['destination_port'],
            pub_date=(data['publication_year'], data['publication_month'], data['publication_day']),
            original_ship=data['original_ship']
        )

        print(f"      Extracted: {len(ships)} ships")
        all_extracted_ships.extend(ships)

    print(f"\nTotal ships extracted: {len(all_extracted_ships):,}")

    # Step 4: Write extracted ships to CSV
    print(f"\nStep 4: Writing extracted ships to {output_csv}...")

    fieldnames = [
        'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
        'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
        'publication_day', 'publication_month', 'publication_year',
        'is_steamship', 'raw_segment', 'extraction_method', 'needs_review', 'original_extracted_ship'
    ]

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for ship in all_extracted_ships:
            writer.writerow({
                'source_file': ship.source_file,
                'line_number': ship.line_number,
                'ship_name': ship.ship_name,
                'origin_port': ship.origin_port,
                'destination_port': ship.destination_port,
                'cargo': ship.cargo,
                'merchant': ship.merchant,
                'arrival_day': ship.arrival_day,
                'arrival_month': ship.arrival_month,
                'arrival_year': ship.arrival_year,
                'publication_day': ship.publication_day,
                'publication_month': ship.publication_month,
                'publication_year': ship.publication_year,
                'is_steamship': ship.is_steamship,
                'raw_segment': ship.raw_segment,
                'extraction_method': ship.extraction_method,
                'needs_review': ship.needs_review,
                'original_extracted_ship': ship.original_extracted_ship
            })

    # Summary
    print("\n" + "="*80)
    print("HYPHEN FORMAT EXTRACTION SUMMARY")
    print("="*80)
    print(f"Hyphen format records processed: {len(hyphen_records)}")
    print(f"Total ships extracted:           {len(all_extracted_ships):,}")

    if hyphen_records:
        expected_total = sum(h['estimated_ships'] for h in hyphen_records)
        print(f"Expected ships:                  {expected_total:,}")
        if expected_total > 0:
            recovery_rate = (len(all_extracted_ships) / expected_total) * 100
            print(f"Recovery rate:                   {recovery_rate:.1f}%")

    print(f"\nOutput file: {output_csv}")
    print("="*80)

    return len(all_extracted_ships)

if __name__ == '__main__':
    categories_csv = Path("/home/jic823/TTJ Forest of Numbers/analysis/high_count_categories.csv")
    main_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final.csv")
    output_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/hyphen_format_extracted.csv")

    extract_hyphen_format_records(categories_csv, main_csv, output_csv)
