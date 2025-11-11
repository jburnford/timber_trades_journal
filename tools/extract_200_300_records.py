#!/usr/bin/env python3
"""
Phase 2.5: Extract ships from 200-300 character records with multiple @ symbols.
Uses same @ symbol splitting approach as multi-ship extraction.
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
    extraction_method: str  # 'SMALL_MULTI_SPLIT'
    needs_review: bool      # True for extractions
    original_extracted_ship: str

def extract_ships_from_line(raw_line: str, source_file: str, line_number: int,
                            destination_port: str, pub_date: Tuple,
                            original_ship: str) -> List[ShipRecord]:
    """Extract multiple ships from a line using @ symbol boundaries."""
    ships = []

    # Find all @ positions
    at_positions = []
    for i, char in enumerate(raw_line):
        if char == '@':
            at_positions.append(i)

    if not at_positions:
        return ships

    pub_year, pub_month, pub_day = pub_date

    # Process each ship segment
    for idx, at_pos in enumerate(at_positions):
        try:
            # Find ship name
            ship_start = find_ship_start(raw_line, at_pos)
            ship_name = raw_line[ship_start:at_pos].strip()

            # Check for steamship marker
            is_steamship = '(s)' in ship_name
            ship_name = ship_name.replace('(s)', '').strip()

            if len(ship_name) < 2 or len(ship_name) > 100:
                continue

            # Find end of this ship's data
            if idx + 1 < len(at_positions):
                segment_end = find_segment_end(raw_line, at_pos, at_positions[idx + 1])
            else:
                segment_end = len(raw_line)

            segment = raw_line[at_pos + 1:segment_end]

            # Parse port
            port_match = re.match(r'^([^,—]+)[,—]', segment)
            if not port_match:
                continue

            origin_port = port_match.group(1).strip()

            if len(origin_port) > 100:
                continue

            # Extract cargo and merchant
            remainder = segment[len(port_match.group(0)):].strip()

            cargo = remainder
            merchant = ''

            parts = remainder.split('.')
            if parts:
                last_part = parts[0]
                if ',' in last_part:
                    cargo_merchant_split = last_part.rsplit(',', 1)
                    if len(cargo_merchant_split) == 2:
                        cargo = cargo_merchant_split[0].strip()
                        merchant = cargo_merchant_split[1].strip()
                    else:
                        cargo = last_part.strip()
                else:
                    cargo = last_part.strip()

            cargo = cargo[:500] if len(cargo) > 500 else cargo
            merchant = merchant[:200] if len(merchant) > 200 else merchant

            raw_segment = raw_line[ship_start:segment_end].strip()
            if len(raw_segment) > 500:
                raw_segment = raw_segment[:500] + '...'

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
                extraction_method='SMALL_MULTI_SPLIT',
                needs_review=True,
                original_extracted_ship=original_ship
            ))

        except Exception as e:
            continue

    return ships

def find_ship_start(text: str, at_pos: int) -> int:
    """Find where ship name starts."""
    search_start = max(0, at_pos - 200)
    for boundary in ['. ', '; ', '\n']:
        last_boundary = text.rfind(boundary, search_start, at_pos)
        if last_boundary != -1:
            return last_boundary + len(boundary)
    return search_start

def find_segment_end(text: str, current_at: int, next_at: int) -> int:
    """Find where current ship's data ends."""
    search_region = text[current_at:next_at]
    last_period = search_region.rfind('. ')
    if last_period != -1:
        return current_at + last_period + 1
    if next_at - current_at > 50:
        return next_at - 50
    return next_at

def extract_200_300_records(main_csv: Path, output_csv: Path):
    """Extract ships from 200-300 character records with multiple @ symbols."""

    print("="*80)
    print("PHASE 2.5: EXTRACTING SHIPS FROM 200-300 CHAR RECORDS")
    print("="*80)

    print("\nStep 1: Finding 200-300 char records with multiple ships...")
    records_to_process = []

    with open(main_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            char_count = int(row['raw_line_char_count'])
            if 200 <= char_count < 300:
                at_count = row['raw_line'].count('@')
                if at_count > 1:  # Multiple ships
                    records_to_process.append({
                        'source_file': row['source_file'],
                        'line_number': int(row['line_number']),
                        'raw_line': row['raw_line'],
                        'destination_port': row['destination_port'],
                        'publication_year': int(row['publication_year']) if row['publication_year'] else 0,
                        'publication_month': parse_month(row['publication_month']),
                        'publication_day': int(row['publication_day']) if row['publication_day'] else 1,
                        'original_ship': row['ship_name'],
                        'char_count': char_count,
                        'at_count': at_count
                    })

    print(f"Found {len(records_to_process)} records with multiple ships")

    # Step 2: Extract ships
    print("\nStep 2: Extracting ships...")
    all_extracted_ships = []

    for idx, rec in enumerate(records_to_process, 1):
        if rec['publication_year'] == 0:
            continue

        if idx % 50 == 0:
            print(f"  Processed {idx}/{len(records_to_process)}...")

        ships = extract_ships_from_line(
            raw_line=rec['raw_line'],
            source_file=rec['source_file'],
            line_number=rec['line_number'],
            destination_port=rec['destination_port'],
            pub_date=(rec['publication_year'], rec['publication_month'], rec['publication_day']),
            original_ship=rec['original_ship']
        )

        all_extracted_ships.extend(ships)

    print(f"\nTotal ships extracted: {len(all_extracted_ships):,}")

    # Step 3: Write to CSV
    print(f"\nStep 3: Writing extracted ships to {output_csv}...")

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
    print("200-300 CHAR EXTRACTION SUMMARY")
    print("="*80)
    print(f"Records processed: {len(records_to_process)}")
    print(f"Total ships extracted: {len(all_extracted_ships):,}")
    estimated = sum(r['at_count'] for r in records_to_process)
    print(f"Expected ships: {estimated:,}")
    if estimated > 0:
        recovery_rate = (len(all_extracted_ships) / estimated) * 100
        print(f"Recovery rate: {recovery_rate:.1f}%")
    print(f"\nOutput file: {output_csv}")
    print("="*80)

    return len(all_extracted_ships)

if __name__ == '__main__':
    main_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final.csv")
    output_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/small_multi_extracted.csv")

    extract_200_300_records(main_csv, output_csv)
