#!/usr/bin/env python3
"""
Simple parser for timeout files - uses straightforward line-by-line parsing
instead of complex regex patterns.
"""

import csv
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ShipRecord:
    """Simple ship record"""
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
    """Extract publication date from filename like '18800110.txt'"""
    # Pattern: YYYYMMDD
    match = re.match(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return year, month, day
    return None, None, None


def parse_arrival_date(date_str: str, pub_year: int) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Parse arrival date like 'Dec. 31' or 'Jan. 5'"""
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    # Pattern: "Dec. 31" or "Jan. 5"
    match = re.match(r'([A-Za-z]+)\.?\s+(\d+)', date_str.strip())
    if match:
        month_str = match.group(1).lower()[:3]
        day = int(match.group(2))
        month = months.get(month_str)
        if month:
            # Year inference: if month > pub_month, it's previous year
            return day, month, pub_year
    return None, None, None


def parse_simple_ship_line(line: str, line_num: int, current_port: str,
                           pub_year: int, pub_month: int, pub_day: int,
                           source_file: str) -> Optional[ShipRecord]:
    """
    Parse a simple ship line like:
    'Dec. 31 Bessie Young-Quebec-527 pcs. oak, elm, and pine-Davies and Sons'
    """
    line = line.strip()
    if not line:
        return None

    # Check for steamship marker
    is_steamship = '(s)' in line
    line = line.replace('(s)', '').strip()

    # Try to extract date at start
    date_match = re.match(r'^([A-Za-z]+\.?\s+\d+)\s+(.+)$', line)
    if not date_match:
        return None

    date_str = date_match.group(1)
    remainder = date_match.group(2)

    arr_day, arr_month, arr_year = parse_arrival_date(date_str, pub_year)

    # Split on dashes to get: Ship-Origin-Cargo-Merchant
    parts = remainder.split('-')
    if len(parts) < 2:
        return None

    ship_name = parts[0].strip()
    origin_port = parts[1].strip() if len(parts) > 1 else ''
    cargo = parts[2].strip() if len(parts) > 2 else ''
    merchant = parts[3].strip() if len(parts) > 3 else ''

    # Handle cases where merchant is on next segment
    if len(parts) > 4:
        merchant = '-'.join(parts[3:]).strip()

    return ShipRecord(
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
    )


def parse_file_simple(file_path: Path) -> List[ShipRecord]:
    """Parse a file using simple line-by-line approach"""
    records = []

    # Extract publication date from filename
    pub_year, pub_month, pub_day = extract_date_from_filename(file_path.name)
    if not pub_year:
        pub_year = 1880  # Default fallback
        pub_month = 1
        pub_day = 1

    current_port = None

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and headers
            if not line or line.startswith('THE TIMBER') or line == 'IMPORTS.':
                continue

            # Check if this is a port header (all caps, no punctuation at start)
            if line.isupper() and not line[0].isdigit():
                # Port header like "BEAUMARIS." or "CARDIFF."
                current_port = line.rstrip('.').strip()
                continue

            # Try to parse as ship line
            if current_port and line and line[0].isalpha():
                record = parse_simple_ship_line(
                    line, line_num, current_port,
                    pub_year, pub_month, pub_day,
                    file_path.name
                )
                if record:
                    records.append(record)

    return records


def process_timeout_files(timeout_list_file: Path, ocr_dir: Path, output_file: Path,
                          max_files: int = None) -> Dict:
    """Process timeout files and extract records"""

    # Read timeout files list
    with open(timeout_list_file, 'r', encoding='utf-8') as f:
        timeout_files = [line.strip() for line in f if line.strip()]

    if max_files:
        timeout_files = timeout_files[:max_files]

    print(f"Processing {len(timeout_files)} timeout files...")

    all_records = []
    stats = {
        'total_files': len(timeout_files),
        'processed': 0,
        'failed': 0,
        'total_records': 0
    }

    for i, filename in enumerate(timeout_files, 1):
        file_path = ocr_dir / filename

        if not file_path.exists():
            print(f"  [{i}/{len(timeout_files)}] ⚠ {filename} - NOT FOUND")
            stats['failed'] += 1
            continue

        try:
            records = parse_file_simple(file_path)
            all_records.extend(records)
            stats['processed'] += 1
            stats['total_records'] += len(records)

            if i % 10 == 0 or i == 1:
                print(f"  [{i}/{len(timeout_files)}] ✓ {filename[:60]}: {len(records)} records")

        except Exception as e:
            print(f"  [{i}/{len(timeout_files)}] ✗ {filename}: {e}")
            stats['failed'] += 1

    # Write to CSV
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

        print(f"\n✓ Wrote {len(all_records):,} records to {output_file}")

    return stats


if __name__ == '__main__':
    timeout_list = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/missing_files_to_parse.txt")
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/llm_extracted_records.csv")

    # Process ALL missing files
    stats = process_timeout_files(timeout_list, ocr_dir, output_file, max_files=None)

    print("\n" + "="*80)
    print("SIMPLE PARSER RESULTS - Missing Files")
    print("="*80)
    print(f"Files processed: {stats['processed']}/{stats['total_files']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total records extracted: {stats['total_records']:,}")
    print("="*80)
