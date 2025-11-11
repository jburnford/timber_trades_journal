#!/usr/bin/env python3
"""
Improved parser - handles complex formats better than simple_llm_parser.py
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
    arrival_year: Optional[int]
    publication_day: Optional[int]
    publication_month: Optional[int]
    publication_year: Optional[int]
    is_steamship: bool
    raw_line: str


def extract_date_from_filename(filename: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Extract publication date from filename"""
    # Pattern: YYYYMMDD
    match = re.match(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    # Try other patterns in long filenames
    # "January 1 1887" pattern
    month_names = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    for month_name, month_num in month_names.items():
        if month_name.lower() in filename.lower():
            # Try to extract day and year near the month
            pattern = rf'{month_name}\s+(\d+)\s+(\d{{4}})'
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(2)), month_num, int(match.group(1))

    return None, None, None


def parse_date(date_str: str, pub_year: int, last_month: int = 1) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Parse arrival date"""
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    # Full date: "Dec. 31" or "Jan 5"
    match = re.match(r'([A-Za-z]+)\.?\s+(\d+)', date_str.strip())
    if match:
        month_str = match.group(1).lower()[:3]
        day = int(match.group(2))
        month = months.get(month_str, last_month)
        return day, month, pub_year

    # Just a day number
    if date_str.strip().isdigit():
        return int(date_str.strip()), last_month, pub_year

    return None, None, None


def parse_ship_line_improved(line: str, line_num: int, current_port: str,
                             last_date: Tuple, pub_date: Tuple,
                             source_file: str) -> List[ShipRecord]:
    """
    Improved parser that handles:
    - Multiple cargo/merchant pairs separated by semicolons
    - Date continuation (just day numbers)
    - Complex merchant patterns
    """
    records = []
    line = line.strip()

    if not line or not current_port:
        return records

    # Check for steamship marker
    is_steamship = '(s)' in line
    line = line.replace('(s)', '').strip()

    # Extract date
    date_match = re.match(r'^([A-Za-z]+\.?\s+\d+|\d+)\s+(.+)$', line)
    if not date_match:
        return records

    date_str = date_match.group(1)
    remainder = date_match.group(2).strip()

    pub_year, pub_month, pub_day = pub_date
    last_day, last_month, last_year = last_date if last_date else (None, pub_month, pub_year)

    arr_day, arr_month, arr_year = parse_date(date_str, pub_year, last_month or pub_month)
    if not arr_day:
        return records

    # Split by dash to get ship, origin, cargo/merchant
    parts = remainder.split('-')
    if len(parts) < 2:
        return records

    ship_name = parts[0].strip()
    origin_port = parts[1].strip() if len(parts) > 1 else ''

    if len(parts) < 3:
        return records

    # Everything after origin could be cargo-merchant or multiple segments
    cargo_merchant_str = '-'.join(parts[2:])

    # Check for semicolon-separated cargo/merchant pairs
    if ';' in cargo_merchant_str:
        segments = cargo_merchant_str.split(';')
        for segment in segments:
            segment = segment.strip()
            seg_parts = segment.split('-')

            if len(seg_parts) >= 2:
                cargo = seg_parts[0].strip()
                merchant = '-'.join(seg_parts[1:]).strip()
            elif len(seg_parts) == 1:
                cargo = seg_parts[0].strip()
                merchant = ''
            else:
                continue

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
    else:
        # Single cargo-merchant
        seg_parts = cargo_merchant_str.split('-')
        if len(seg_parts) >= 2:
            cargo = seg_parts[0].strip()
            merchant = '-'.join(seg_parts[1:]).strip()
        elif len(seg_parts) == 1:
            cargo = seg_parts[0].strip()
            merchant = ''
        else:
            return records

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


def parse_file_improved(file_path: Path) -> List[ShipRecord]:
    """Improved file parser"""
    records = []

    pub_year, pub_month, pub_day = extract_date_from_filename(file_path.name)
    if not pub_year:
        pub_year, pub_month, pub_day = 1880, 1, 1

    current_port = None
    last_date = None
    stop_markers = ['THE GAZETTE', 'FAILURES', 'ARRANGEMENTS', 'BANKRUPTCY', 'NOTICES']

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line_stripped = line.strip()

                # Stop at gazette/bankruptcy sections
                if any(marker in line_stripped.upper() for marker in stop_markers):
                    break

                # Skip empty lines
                if not line_stripped:
                    continue

                # Port header (all caps, short)
                if line_stripped.isupper() and len(line_stripped) < 30 and not line_stripped.isdigit():
                    # Skip region headers
                    if line_stripped.rstrip('.') not in ['IRELAND', 'SCOTLAND', 'ENGLAND', 'WALES', 'IMPORTS']:
                        current_port = line_stripped.rstrip('.')
                    continue

                # Try to parse as ship line
                if current_port:
                    ship_records = parse_ship_line_improved(
                        line_stripped, line_num, current_port, last_date,
                        (pub_year, pub_month, pub_day), file_path.name
                    )
                    if ship_records:
                        records.extend(ship_records)
                        # Update last date
                        if ship_records[0].arrival_day and ship_records[0].arrival_month:
                            last_date = (
                                ship_records[0].arrival_day,
                                ship_records[0].arrival_month,
                                ship_records[0].arrival_year
                            )

    except Exception as e:
        print(f"Error parsing {file_path.name}: {e}")

    return records


def process_all_missing_files(missing_files_list: Path, ocr_dir: Path, output_file: Path):
    """Process all missing files with improved parser"""
    with open(missing_files_list, 'r', encoding='utf-8') as f:
        filenames = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(filenames)} files with improved parser...")

    all_records = []
    stats = {'processed': 0, 'failed': 0, 'total_records': 0}

    for i, filename in enumerate(filenames, 1):
        file_path = ocr_dir / filename

        if not file_path.exists():
            stats['failed'] += 1
            continue

        try:
            records = parse_file_improved(file_path)
            all_records.extend(records)
            stats['processed'] += 1
            stats['total_records'] += len(records)

            if i % 20 == 0 or i == 1:
                print(f"  [{i}/{len(filenames)}] {filename[:60]}: {len(records)} records")

        except Exception as e:
            print(f"  [{i}/{len(filenames)}] ERROR {filename}: {e}")
            stats['failed'] += 1

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
    print(f"IMPROVED PARSER RESULTS")
    print(f"{'='*80}")
    print(f"Files processed: {stats['processed']}/{len(filenames)}")
    print(f"Failed: {stats['failed']}")
    print(f"Total records: {stats['total_records']:,}")
    print(f"Avg records/file: {stats['total_records'] / max(1, stats['processed']):.1f}")
    print(f"{'='*80}")

    return stats


if __name__ == '__main__':
    missing_files = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/missing_files_to_parse.txt")
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/improved_parser_records.csv")

    process_all_missing_files(missing_files, ocr_dir, output_file)
