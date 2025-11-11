#!/usr/bin/env python3
"""
Year-specific parser for 1891 timeout groups.
Strategy: Use simple string operations instead of complex regex to prevent backtracking.
"""
import csv
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

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
    raw_line: str

MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

def parse_simple_date(date_str: str, pub_year: int, last_month: int) -> Tuple[Optional[int], Optional[int], int]:
    """Parse date with SIMPLE patterns only."""
    date_str = date_str.strip()

    # "Jan. 5" or "Jan 5"
    match = re.match(r'([A-Za-z]{3,9})\.?\s+(\d{1,2})', date_str)
    if match:
        month_str = match.group(1).lower()[:3]
        day = int(match.group(2))
        month = MONTHS.get(month_str, last_month)
        return day, month, pub_year

    # Just a number (day continuation)
    if date_str.isdigit():
        return int(date_str), last_month, pub_year

    return None, None, pub_year


def parse_line_1891(line: str, line_num: int, current_port: str,
                    last_date: Tuple, pub_date: Tuple, source_file: str) -> List[ShipRecord]:
    """
    Parse 1891 format with SIMPLE string operations.
    Format: Date Ship-Origin-Cargo-Merchant
    """
    records = []
    line = line.strip()

    if not line or not current_port:
        return records

    # Check steamship marker
    is_steamship = '(s)' in line
    line = line.replace('(s)', '').strip()

    # Hard limit: skip lines over 500 chars to prevent hanging
    if len(line) > 500:
        return records

    pub_year, pub_month, pub_day = pub_date
    last_day, last_month, _ = last_date if last_date else (None, pub_month, pub_year)

    # Try to extract date at start
    # Pattern: "Jan. 5 " or "5 " at line start
    date_match = re.match(r'^([A-Za-z]+\.?\s+\d{1,2}|\d{1,2})\s+(.+)$', line)
    if not date_match:
        return records

    date_str = date_match.group(1)
    remainder = date_match.group(2).strip()

    arr_day, arr_month, arr_year = parse_simple_date(date_str, pub_year, last_month or pub_month)
    if not arr_day:
        return records

    # Now parse remainder: Ship-Origin-Cargo-Merchant
    # Use FIND instead of regex to locate dashes

    # Find first dash (after ship name)
    first_dash = remainder.find('-')
    if first_dash == -1:
        return records

    ship_name = remainder[:first_dash].strip()
    if len(ship_name) == 0 or len(ship_name) > 100:  # Sanity check
        return records

    # Find second dash (after origin)
    second_dash = remainder.find('-', first_dash + 1)
    if second_dash == -1:
        return records

    origin_port = remainder[first_dash + 1:second_dash].strip()
    if len(origin_port) == 0 or len(origin_port) > 100:  # Sanity check
        return records

    # Find third dash (after cargo)
    third_dash = remainder.find('-', second_dash + 1)
    if third_dash == -1:
        # No merchant, cargo goes to end
        cargo = remainder[second_dash + 1:].strip()
        merchant = ''
    else:
        cargo = remainder[second_dash + 1:third_dash].strip()
        merchant = remainder[third_dash + 1:].strip()

    # Truncate overly long fields
    cargo = cargo[:200] if len(cargo) > 200 else cargo
    merchant = merchant[:200] if len(merchant) > 200 else merchant

    records.append(ShipRecord(
        source_file=source_file,
        line_number=line_num,
        ship_name=ship_name,
        origin_port=origin_port,
        destination_port=current_port,
        cargo=cargo,
        merchant=merchant,
        arrival_day=arr_day,
        arrival_month=arr_month,
        arrival_year=arr_year,
        publication_day=pub_day,
        publication_month=pub_month,
        publication_year=pub_year,
        is_steamship=is_steamship,
        raw_line=line
    ))

    return records


def parse_file_1891(file_path: Path) -> List[ShipRecord]:
    """Parse single 1891 file with simple patterns."""
    records = []

    # Extract pub date from filename: YYYYMMDD format
    match = re.match(r'(\d{4})(\d{2})(\d{2})', file_path.name)
    if match:
        pub_year = int(match.group(1))
        pub_month = int(match.group(2))
        pub_day = int(match.group(3))
    else:
        pub_year, pub_month, pub_day = 1891, 1, 1

    current_port = None
    last_date = (None, pub_month, pub_year)
    stop_markers = ['GAZETTE', 'FAILURES', 'BANKRUPTCY', 'NOTICES', 'TELEGRAPH']

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line_stripped = line.strip()

                # Stop markers
                if any(marker in line_stripped.upper() for marker in stop_markers):
                    break

                if not line_stripped:
                    continue

                # Port header (all caps, short)
                if line_stripped.isupper() and len(line_stripped) < 30:
                    if line_stripped not in ['IMPORTS', 'ENGLAND', 'SCOTLAND', 'IRELAND', 'WALES']:
                        current_port = line_stripped.rstrip('.')
                    continue

                # Try parsing as ship line
                if current_port:
                    ship_records = parse_line_1891(
                        line_stripped, line_num, current_port, last_date,
                        (pub_year, pub_month, pub_day), file_path.name
                    )
                    if ship_records:
                        records.extend(ship_records)
                        # Update last date
                        if ship_records[0].arrival_day:
                            last_date = (ship_records[0].arrival_day, ship_records[0].arrival_month, pub_year)

    except Exception as e:
        print(f"Error parsing {file_path.name}: {e}")

    return records


def process_1891_timeout_groups(timeout_list: Path, ocr_dir: Path, output_file: Path):
    """Process all 1891 timeout groups."""
    # Read base names from timeout list
    with open(timeout_list, 'r', encoding='utf-8') as f:
        base_names = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(base_names)} 1891 timeout groups...")

    all_records = []
    stats = {'processed': 0, 'failed': 0, 'total_records': 0}

    for i, base_name in enumerate(base_names, 1):
        # Find all pages for this base name
        pattern = f"{base_name}*.txt"
        page_files = sorted(ocr_dir.glob(pattern))

        if not page_files:
            print(f"  [{i}/{len(base_names)}] {base_name}: No files found")
            stats['failed'] += 1
            continue

        # Process all pages for this document group
        group_records = []
        for page_file in page_files:
            try:
                records = parse_file_1891(page_file)
                group_records.extend(records)
            except Exception as e:
                print(f"  [{i}/{len(base_names)}] ERROR {page_file.name}: {e}")

        all_records.extend(group_records)
        stats['processed'] += 1
        stats['total_records'] += len(group_records)

        if i % 10 == 0 or i == 1:
            print(f"  [{i}/{len(base_names)}] {base_name}: {len(group_records)} records")

    # Write records
    if all_records:
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'raw_line'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for record in all_records:
                writer.writerow({
                    'source_file': record.source_file,
                    'line_number': record.line_number,
                    'ship_name': record.ship_name,
                    'origin_port': record.origin_port,
                    'destination_port': record.destination_port,
                    'cargo': record.cargo,
                    'merchant': record.merchant,
                    'arrival_day': record.arrival_day,
                    'arrival_month': record.arrival_month,
                    'arrival_year': record.arrival_year,
                    'publication_day': record.publication_day,
                    'publication_month': record.publication_month,
                    'publication_year': record.publication_year,
                    'is_steamship': record.is_steamship,
                    'raw_line': record.raw_line
                })

    print(f"\n{'='*80}")
    print(f"1891 PARSER RESULTS")
    print(f"{'='*80}")
    print(f"Groups processed: {stats['processed']}/{len(base_names)}")
    print(f"Failed: {stats['failed']}")
    print(f"Total records: {stats['total_records']:,}")
    print(f"Avg records/group: {stats['total_records'] / max(1, stats['processed']):.1f}")
    print(f"{'='*80}")

    return stats


if __name__ == '__main__':
    timeout_list = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/timeout_clusters/timeout_1891.txt")
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/timeout_1891_records.csv")

    process_1891_timeout_groups(timeout_list, ocr_dir, output_file)
