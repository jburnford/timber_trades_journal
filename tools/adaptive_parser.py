#!/usr/bin/env python3
"""
Adaptive parser - tries multiple format patterns for each file
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import Counter

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
    format_pattern: str
    raw_line: str


def extract_pub_date(filename: str) -> Tuple:
    """Extract publication date"""
    match = re.match(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    months = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
              'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
    for month_name, month_num in months.items():
        if month_name.lower() in filename.lower():
            match = re.search(rf'{month_name}\s+(\d+)\s+(\d{{4}})', filename, re.IGNORECASE)
            if match:
                return int(match.group(2)), month_num, int(match.group(1))

    return 1880, 1, 1


def parse_date(date_str: str, default_year: int, last_month: int = 1) -> Tuple:
    """Parse arrival date"""
    months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
              'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}

    match = re.match(r'([A-Za-z]+)\.?\s+(\d+)', date_str.strip())
    if match:
        month_str = match.group(1).lower()[:3]
        day = int(match.group(2))
        month = months.get(month_str, last_month)
        return day, month, default_year

    if date_str.strip().isdigit():
        return int(date_str.strip()), last_month, default_year

    return None, None, None


def try_pattern_dash(line: str, current_port: str, date_info: Tuple, pub_date: Tuple,
                     source_file: str, line_num: int) -> List[ShipRecord]:
    """Pattern: 'Dec. 31 Ship-Origin-Cargo-Merchant' with semicolon-separated cargo/merchant"""
    records = []
    is_steamship = '(s)' in line
    line = line.replace('(s)', '').strip()

    date_match = re.match(r'^([A-Za-z]+\.?\s+\d+|\d+)\s+(.+)$', line)
    if not date_match:
        return records

    date_str = date_match.group(1)
    remainder = date_match.group(2).strip()

    pub_year, pub_month, pub_day = pub_date
    last_day, last_month, _ = date_info if date_info[0] else (None, pub_month, pub_year)

    arr_day, arr_month, arr_year = parse_date(date_str, pub_year, last_month or pub_month)
    if not arr_day:
        return records

    parts = remainder.split('-')
    if len(parts) < 3:
        return records

    ship_name = parts[0].strip()
    origin_port = parts[1].strip()
    cargo_merchant_str = '-'.join(parts[2:])

    # Handle semicolon-separated segments
    if ';' in cargo_merchant_str:
        segments = cargo_merchant_str.split(';')
        for segment in segments:
            seg_parts = segment.strip().split('-')
            cargo = seg_parts[0].strip() if len(seg_parts) > 0 else ''
            merchant = '-'.join(seg_parts[1:]).strip() if len(seg_parts) > 1 else ''

            records.append(ShipRecord(
                source_file=source_file, line_number=line_num, ship_name=ship_name,
                origin_port=origin_port, destination_port=current_port, cargo=cargo,
                merchant=merchant, arrival_day=arr_day, arrival_month=arr_month,
                arrival_year=arr_year, publication_day=pub_day, publication_month=pub_month,
                publication_year=pub_year, is_steamship=is_steamship,
                format_pattern='dash_semicolon', raw_line=line
            ))
    else:
        seg_parts = cargo_merchant_str.split('-')
        cargo = seg_parts[0].strip() if len(seg_parts) > 0 else ''
        merchant = '-'.join(seg_parts[1:]).strip() if len(seg_parts) > 1 else ''

        records.append(ShipRecord(
            source_file=source_file, line_number=line_num, ship_name=ship_name,
            origin_port=origin_port, destination_port=current_port, cargo=cargo,
            merchant=merchant, arrival_day=arr_day, arrival_month=arr_month,
            arrival_year=arr_year, publication_day=pub_day, publication_month=pub_month,
            publication_year=pub_year, is_steamship=is_steamship,
            format_pattern='dash_simple', raw_line=line
        ))

    return records


def try_pattern_at(line: str, current_port: str, date_info: Tuple, pub_date: Tuple,
                   source_file: str, line_num: int) -> List[ShipRecord]:
    """Pattern: 'Ship @ Origin,—Cargo, Merchant' (at-sign format)"""
    records = []
    is_steamship = '(s)' in line
    line = line.replace('(s)', '').strip()

    # Check if line has @ separator
    if '@' not in line:
        return records

    # Extract date if present (optional for @ format)
    date_match = re.match(r'^([A-Za-z]+\.?\s+\d+|\d+)\.\s+(.+)$', line)
    if date_match:
        date_str = date_match.group(1)
        remainder = date_match.group(2).strip()
    else:
        # No date, use last known date
        date_str = None
        remainder = line

    pub_year, pub_month, pub_day = pub_date
    last_day, last_month, _ = date_info if date_info[0] else (None, pub_month, pub_year)

    if date_str:
        arr_day, arr_month, arr_year = parse_date(date_str, pub_year, last_month or pub_month)
    else:
        arr_day, arr_month, arr_year = last_day, last_month, pub_year

    # Split by @ to get ship and rest
    at_parts = remainder.split('@')
    if len(at_parts) < 2:
        return records

    ship_name = at_parts[0].strip()
    rest = at_parts[1].strip()

    # Split rest by ,— or , to get origin, cargo, merchant
    comma_dash_match = re.split(r',—|,\s+', rest)
    if len(comma_dash_match) >= 2:
        origin_port = comma_dash_match[0].strip()
        cargo = comma_dash_match[1].strip() if len(comma_dash_match) > 1 else ''
        merchant = comma_dash_match[2].strip() if len(comma_dash_match) > 2 else ''

        records.append(ShipRecord(
            source_file=source_file, line_number=line_num, ship_name=ship_name,
            origin_port=origin_port, destination_port=current_port, cargo=cargo,
            merchant=merchant, arrival_day=arr_day, arrival_month=arr_month,
            arrival_year=arr_year, publication_day=pub_day, publication_month=pub_month,
            publication_year=pub_year, is_steamship=is_steamship,
            format_pattern='at_comma', raw_line=line
        ))

    return records


def parse_file_adaptive(file_path: Path) -> Tuple[List[ShipRecord], Counter]:
    """Parse file trying multiple patterns"""
    records = []
    pattern_stats = Counter()

    pub_year, pub_month, pub_day = extract_pub_date(file_path.name)
    current_port = None
    last_date = (None, pub_month, pub_year)

    stop_markers = ['THE GAZETTE', 'FAILURES', 'ARRANGEMENTS', 'BANKRUPTCY', 'NOTICES',
                    'American Intelligence', 'THE SAGINAW']

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line_stripped = line.strip()

                if any(marker in line_stripped for marker in stop_markers):
                    break

                if not line_stripped:
                    continue

                # Port header
                if line_stripped.isupper() and len(line_stripped) < 30 and not line_stripped.isdigit():
                    if line_stripped.rstrip('.') not in ['IRELAND', 'SCOTLAND', 'ENGLAND', 'WALES', 'IMPORTS', 'THE TIMBER TRADES JOURNAL']:
                        current_port = line_stripped.rstrip('.')
                    continue

                if not current_port:
                    continue

                # Try pattern @ first (for files like the one we just saw)
                pattern_records = try_pattern_at(line_stripped, current_port, last_date,
                                                (pub_year, pub_month, pub_day), file_path.name, line_num)
                if pattern_records:
                    records.extend(pattern_records)
                    pattern_stats['at_comma'] += len(pattern_records)
                    last_date = (pattern_records[0].arrival_day, pattern_records[0].arrival_month,
                               pattern_records[0].arrival_year)
                    continue

                # Try dash pattern
                pattern_records = try_pattern_dash(line_stripped, current_port, last_date,
                                                  (pub_year, pub_month, pub_day), file_path.name, line_num)
                if pattern_records:
                    records.extend(pattern_records)
                    if pattern_records[0].format_pattern == 'dash_semicolon':
                        pattern_stats['dash_semicolon'] += len(pattern_records)
                    else:
                        pattern_stats['dash_simple'] += len(pattern_records)
                    last_date = (pattern_records[0].arrival_day, pattern_records[0].arrival_month,
                               pattern_records[0].arrival_year)

    except Exception as e:
        print(f"Error parsing {file_path.name}: {e}")

    return records, pattern_stats


def process_all_files(missing_files_list: Path, ocr_dir: Path, output_file: Path):
    """Process all files with adaptive parser"""
    with open(missing_files_list, 'r', encoding='utf-8') as f:
        filenames = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(filenames)} files with adaptive parser...")

    all_records = []
    global_pattern_stats = Counter()
    stats = {'processed': 0, 'failed': 0, 'total_records': 0}

    for i, filename in enumerate(filenames, 1):
        file_path = ocr_dir / filename

        if not file_path.exists():
            stats['failed'] += 1
            continue

        try:
            records, pattern_stats = parse_file_adaptive(file_path)
            all_records.extend(records)
            stats['processed'] += 1
            stats['total_records'] += len(records)
            global_pattern_stats += pattern_stats

            if i % 20 == 0 or i == 1:
                patterns_used = ', '.join([f"{k}:{v}" for k, v in pattern_stats.items()]) if pattern_stats else "none"
                print(f"  [{i}/{len(filenames)}] {filename[:50]}: {len(records)} records ({patterns_used})")

        except Exception as e:
            print(f"  [{i}/{len(filenames)}] ERROR {filename}: {e}")
            stats['failed'] += 1

    # Write records
    if all_records:
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'format_pattern', 'raw_line'
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
                    'format_pattern': record.format_pattern,
                    'raw_line': record.raw_line
                })

    print(f"\n{'='*80}")
    print(f"ADAPTIVE PARSER RESULTS")
    print(f"{'='*80}")
    print(f"Files processed: {stats['processed']}/{len(filenames)}")
    print(f"Failed: {stats['failed']}")
    print(f"Total records: {stats['total_records']:,}")
    print(f"Avg records/file: {stats['total_records'] / max(1, stats['processed']):.1f}")
    print(f"\nPattern usage:")
    for pattern, count in global_pattern_stats.most_common():
        print(f"  {pattern}: {count:,} records")
    print(f"{'='*80}")

    return stats


if __name__ == '__main__':
    missing_files = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/missing_files_to_parse.txt")
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/adaptive_parser_records.csv")

    process_all_files(missing_files, ocr_dir, output_file)
