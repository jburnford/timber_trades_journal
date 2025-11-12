#!/usr/bin/env python3
"""
Phase 3: Extract ships from MEGA records (>10K characters).
These are essentially entire pages concatenated into single records.
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
    extraction_method: str  # 'MEGA_SPLIT'
    needs_review: bool      # True for MEGA extractions
    original_extracted_ship: str  # The ship that was originally extracted

def extract_ships_from_mega_line(raw_line: str, source_file: str, line_number: int,
                                  destination_port: str, pub_date: Tuple,
                                  original_ship: str) -> List[ShipRecord]:
    """
    Extract multiple ships from a MEGA concatenated line.
    Strategy: Split on @ symbol, then parse each segment.
    """

    ships = []

    # Find all @ positions (ship-port boundaries)
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
            # Find ship name (work backwards from @ to find start)
            ship_start = find_ship_start(raw_line, at_pos)
            ship_name = raw_line[ship_start:at_pos].strip()

            # Check for steamship marker
            is_steamship = '(s)' in ship_name
            ship_name = ship_name.replace('(s)', '').strip()

            # Skip if ship name is too short or too long
            if len(ship_name) < 2 or len(ship_name) > 100:
                continue

            # Find end of this ship's data (next @ or end of string)
            if idx + 1 < len(at_positions):
                segment_end = find_segment_end(raw_line, at_pos, at_positions[idx + 1])
            else:
                segment_end = len(raw_line)

            # Extract port, cargo, merchant from segment after @
            segment = raw_line[at_pos + 1:segment_end]

            # Parse port (text before first comma or em-dash)
            port_match = re.match(r'^([^,—]+)[,—]', segment)
            if not port_match:
                continue

            origin_port = port_match.group(1).strip()

            # Skip if port is too long (likely parsing error)
            if len(origin_port) > 100:
                continue

            # Extract cargo and merchant
            remainder = segment[len(port_match.group(0)):].strip()

            # Try to split on period or semicolon for merchant
            cargo = remainder
            merchant = ''

            # Look for merchant indicators (common patterns)
            # Merchant often comes after final comma before period/next ship
            parts = remainder.split('.')
            if parts:
                last_part = parts[0]
                # Try to find merchant (text after last comma)
                if ',' in last_part:
                    cargo_merchant_split = last_part.rsplit(',', 1)
                    if len(cargo_merchant_split) == 2:
                        cargo = cargo_merchant_split[0].strip()
                        merchant = cargo_merchant_split[1].strip()
                    else:
                        cargo = last_part.strip()
                else:
                    cargo = last_part.strip()

            # Truncate overly long fields
            cargo = cargo[:500] if len(cargo) > 500 else cargo
            merchant = merchant[:200] if len(merchant) > 200 else merchant

            # Extract raw segment for reference
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
                arrival_day=None,  # Dates not reliably extractable from concatenated mess
                arrival_month=None,
                arrival_year=pub_year,
                publication_day=pub_day,
                publication_month=pub_month,
                publication_year=pub_year,
                is_steamship=is_steamship,
                raw_segment=raw_segment,
                extraction_method='MEGA_SPLIT',
                needs_review=True,
                original_extracted_ship=original_ship
            ))

        except Exception as e:
            # Continue processing other ships even if one fails
            continue

    return ships

def find_ship_start(text: str, at_pos: int) -> int:
    """Find where ship name starts (work backwards from @)."""
    # Ship names typically start after: period, semicolon, or start of string
    # Look back for these boundaries

    search_start = max(0, at_pos - 200)  # Don't search too far back

    # Look for sentence boundaries
    for boundary in ['. ', '; ', '\n']:
        last_boundary = text.rfind(boundary, search_start, at_pos)
        if last_boundary != -1:
            return last_boundary + len(boundary)

    # If no boundary found, start from beginning of search window
    return search_start

def find_segment_end(text: str, current_at: int, next_at: int) -> int:
    """Find where current ship's data ends (before next ship starts)."""
    # Look for ship name before next @
    # Ship names typically start after period

    search_region = text[current_at:next_at]

    # Find last period before next @
    last_period = search_region.rfind('. ')
    if last_period != -1:
        return current_at + last_period + 1

    # If no period, use position before next @
    # Back up to find word boundary
    if next_at - current_at > 50:
        return next_at - 50

    return next_at

def extract_mega_records(categories_csv: Path, main_csv: Path, output_csv: Path):
    """Extract ships from all MEGA records."""

    print("="*80)
    print("PHASE 3: EXTRACTING SHIPS FROM MEGA RECORDS")
    print("="*80)

    # Step 1: Read categorization to find MEGA records
    print("\nStep 1: Finding MEGA records...")
    mega_records = []

    with open(categories_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['size_category'] == 'MEGA':
                mega_records.append({
                    'source_file': row['source_file'],
                    'line_number': int(row['line_number']),
                    'extracted_ship': row['extracted_ship'],
                    'char_count': int(row['char_count']),
                    'estimated_ships': int(row['estimated_total_ships'])
                })

    print(f"Found {len(mega_records)} MEGA records")
    for rec in mega_records:
        print(f"  - {rec['source_file'][:60]:60} | {rec['estimated_ships']:4} ships | {rec['char_count']:7,} chars")

    # Step 2: Read main CSV to get full raw_line for each MEGA record
    print("\nStep 2: Loading full raw_line data from main CSV...")

    mega_data = {}
    with open(main_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check if this row matches any MEGA record
            for mega in mega_records:
                if (row['source_file'] == mega['source_file'] and
                    int(row['line_number']) == mega['line_number']):
                    mega_data[mega['line_number']] = {
                        'raw_line': row['raw_line'],
                        'destination_port': row['destination_port'],
                        'publication_year': int(row['publication_year']),
                        'publication_month': parse_month(row['publication_month']),
                        'publication_day': int(row['publication_day']) if row['publication_day'] else 1,
                        'original_ship': row['ship_name']
                    }

    print(f"Loaded {len(mega_data)} MEGA raw_line entries")

    # Step 3: Extract ships from each MEGA record
    print("\nStep 3: Extracting ships from MEGA records...")
    all_extracted_ships = []

    for mega in mega_records:
        line_num = mega['line_number']
        if line_num not in mega_data:
            print(f"  WARNING: Could not find raw_line for {mega['source_file']}")
            continue

        data = mega_data[line_num]
        raw_line = data['raw_line']

        print(f"\n  Processing: {mega['source_file'][:60]}")
        print(f"    Chars: {len(raw_line):,} | Expected ships: {mega['estimated_ships']}")

        ships = extract_ships_from_mega_line(
            raw_line=raw_line,
            source_file=mega['source_file'],
            line_number=line_num,
            destination_port=data['destination_port'],
            pub_date=(data['publication_year'], data['publication_month'], data['publication_day']),
            original_ship=data['original_ship']
        )

        print(f"    Extracted: {len(ships)} ships")
        all_extracted_ships.extend(ships)

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
    print("MEGA RECORD EXTRACTION SUMMARY")
    print("="*80)
    print(f"MEGA records processed: {len(mega_records)}")
    print(f"Total ships extracted:  {len(all_extracted_ships):,}")
    print(f"Expected ships:         {sum(m['estimated_ships'] for m in mega_records):,}")
    print(f"Recovery rate:          {(len(all_extracted_ships) / sum(m['estimated_ships'] for m in mega_records) * 100):.1f}%")
    print(f"\nOutput file: {output_csv}")
    print("="*80)

    return len(all_extracted_ships)

if __name__ == '__main__':
    categories_csv = Path("/home/jic823/TTJ Forest of Numbers/analysis/high_count_categories.csv")
    main_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final.csv")
    output_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/mega_extracted_ships.csv")

    extract_mega_records(categories_csv, main_csv, output_csv)
