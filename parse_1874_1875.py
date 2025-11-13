#!/usr/bin/env python3
"""
Parse 1874-1875 Timber Trades Journal OCR files to extract ship arrival records.
Handles multi-ship lines and the "early_at" format: ShipName @ Port,—cargo, merchant
"""

import re
import csv
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Month name to number mapping
MONTHS = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8, 'augus': 8,  # Handle OCR typo
    'september': 9, 'october': 10, 'november': 11, 'december': 12
}

def extract_publication_date(filename: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Extract publication date from filename.
    Examples:
        "1. p. 6 a╠Ç 8 - May 2 1874 - Imports..." -> (2, 5, 1874)
        "10. 152-155 - September 4 1875 - Imports..." -> (4, 9, 1875)
    """
    # Pattern: Month Day Year
    pattern = r'-\s+([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})\s+-'
    match = re.search(pattern, filename)
    if match:
        month_name = match.group(1).lower()
        day = int(match.group(2))
        year = int(match.group(3))
        month = MONTHS.get(month_name)
        if month:
            return (day, month, year)
    return (None, None, None)

def extract_arrival_date(date_line: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract arrival date from lines like "April 17th." or "May 1st."
    Returns (day, month_number)
    """
    # Pattern: Month Day(st/nd/rd/th)
    pattern = r'([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\.?'
    match = re.match(pattern, date_line.strip())
    if match:
        month_name = match.group(1).lower()
        day = int(match.group(2))
        month = MONTHS.get(month_name)
        if month:
            return (day, month)
    return (None, None)

def split_multi_ship_line(line: str) -> List[str]:
    """
    Split a line containing multiple ship entries.
    Pattern: ShipName @ Port,—cargo, merchant. NextShip @ Port,—...

    Key insight: Ships are separated by ". " followed by a capitalized word and " @ "
    """
    # Find all positions where a new ship entry starts
    # Pattern: ". [Capital letter(s)] @ "
    ship_pattern = r'\.\s+([A-Z][^\s@]+(?:\s+[A-Z][^\s@]+)*)\s+@\s+'

    matches = list(re.finditer(ship_pattern, line))

    if not matches:
        # No multi-ship pattern found, return the whole line
        return [line]

    ships = []

    # Get the first ship (before the first match)
    first_ship = line[:matches[0].start() + 1].strip()  # Include the period
    if first_ship:
        ships.append(first_ship)

    # Get subsequent ships
    for i in range(len(matches)):
        start_pos = matches[i].start() + 2  # Skip ". "
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start() + 1  # Include period of next ship
        else:
            end_pos = len(line)

        ship_entry = line[start_pos:end_pos].strip()
        if ship_entry:
            ships.append(ship_entry)

    return ships

def parse_ship_entry(entry: str, arrival_day: Optional[int], arrival_month: Optional[int],
                     arrival_year: Optional[int]) -> Optional[Dict]:
    """
    Parse a single ship entry.
    Format: ShipName (s) @ Port,—cargo details, merchant name

    Returns a dictionary with extracted fields, or None if not a valid ship entry.
    """
    # Pattern: ShipName (optional (s)) @ Port,—cargo and merchant
    # The @ symbol is the key delimiter
    if '@' not in entry:
        return None

    # Split on @
    parts = entry.split('@', 1)
    if len(parts) != 2:
        return None

    ship_part = parts[0].strip()
    rest = parts[1].strip()

    # Extract ship name and check for (s) steamship indicator
    is_steamship = False
    if '(s)' in ship_part:
        ship_name = ship_part.replace('(s)', '').strip()
        is_steamship = True
    else:
        ship_name = ship_part.strip()

    # Remove any leading date markers (like "April 17th.")
    ship_name = re.sub(r'^[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\.\s+', '', ship_name)

    if not ship_name:
        return None

    # Split rest into port and cargo/merchant
    # Pattern: Port,—cargo details, merchant
    if ',—' in rest or ',-' in rest or ',–' in rest:
        # Find the first occurrence of ,— or variants
        port_cargo_split = re.split(r',[-—–]', rest, 1)
        if len(port_cargo_split) == 2:
            origin_port = port_cargo_split[0].strip()
            cargo_merchant = port_cargo_split[1].strip()
        else:
            origin_port = rest.strip()
            cargo_merchant = ''
    else:
        # No clear delimiter, try to extract port before first comma
        comma_idx = rest.find(',')
        if comma_idx > 0:
            origin_port = rest[:comma_idx].strip()
            cargo_merchant = rest[comma_idx+1:].strip()
        else:
            origin_port = rest.strip()
            cargo_merchant = ''

    # Split cargo and merchant
    # Merchant is typically after the last comma, but cargo can have many commas
    # Simple heuristic: last segment after comma that's not purely numeric/cargo data
    cargo = cargo_merchant
    merchant = ''

    if cargo_merchant:
        # Try to find merchant name (typically capitalized names at the end)
        # Look for pattern like "Some Cargo, Some Company & Co." or "Some Cargo, Order."
        merchant_pattern = r',\s+([A-Z][^,]*(?:&\s+Co\.?|Sons?|Ltd\.?|Order\.?))\s*\.?$'
        merchant_match = re.search(merchant_pattern, cargo_merchant)
        if merchant_match:
            merchant = merchant_match.group(1).strip().rstrip('.')
            cargo = cargo_merchant[:merchant_match.start()].strip()

    return {
        'ship_name': ship_name,
        'origin_port': origin_port,
        'cargo': cargo,
        'merchant': merchant,
        'arrival_day': arrival_day,
        'arrival_month': arrival_month,
        'arrival_year': arrival_year,
        'is_steamship': is_steamship
    }

def process_file(filepath: Path, pub_day: int, pub_month: int, pub_year: int) -> List[Dict]:
    """
    Process a single OCR file and extract all ship records.
    """
    records = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_arrival_day = None
    current_arrival_month = None
    current_arrival_year = pub_year  # Assume same year as publication

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        if not line:
            continue

        # Check if this is a date line
        arrival_date = extract_arrival_date(line)
        if arrival_date[0] is not None:
            current_arrival_day, current_arrival_month = arrival_date
            # Date line may also contain ship entries on the same line
            # Check if there's content after the date
            date_pattern = r'[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\.\s+'
            match = re.match(date_pattern, line)
            if match:
                remainder = line[match.end():].strip()
                if remainder and '@' in remainder:
                    line = remainder  # Process the ship entries
                else:
                    continue  # Just a date line, no ships
            else:
                continue

        # Check if line contains ship entries
        if '@' not in line:
            continue

        # Skip header lines
        if any(keyword in line for keyword in ['TIMBER TRADES JOURNAL', 'Imports of Timber']):
            continue

        # Split multi-ship lines
        ship_entries = split_multi_ship_line(line)

        for entry in ship_entries:
            parsed = parse_ship_entry(
                entry,
                current_arrival_day,
                current_arrival_month,
                current_arrival_year
            )

            if parsed:
                records.append({
                    'source_file': filepath.name,
                    'line_number': line_num,
                    'ship_name': parsed['ship_name'],
                    'origin_port': parsed['origin_port'],
                    'destination_port': 'LONDON',  # Default, could be extracted from section headers
                    'cargo': parsed['cargo'],
                    'merchant': parsed['merchant'],
                    'arrival_day': parsed['arrival_day'],
                    'arrival_month': parsed['arrival_month'],
                    'arrival_year': parsed['arrival_year'],
                    'publication_day': pub_day,
                    'publication_month': pub_month,
                    'publication_year': pub_year,
                    'is_steamship': 'TRUE' if parsed['is_steamship'] else 'FALSE',
                    'format_type': 'early_at',
                    'confidence': 'medium',
                    'raw_line': entry[:200]  # Truncate if too long
                })

    return records

def main():
    # Paths
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/parsed_output")
    output_file = output_dir / "1874_1875_llm_parsed.csv"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all 1874-1875 files
    all_files = sorted(ocr_dir.glob("*.txt"))
    target_files = [f for f in all_files if re.search(r'187[45]', f.name)]

    print(f"Found {len(target_files)} files to process")

    # Process all files
    all_records = []
    files_processed = 0
    files_with_errors = []

    for filepath in target_files:
        try:
            # Extract publication date
            pub_day, pub_month, pub_year = extract_publication_date(filepath.name)

            if pub_day is None:
                print(f"Warning: Could not extract publication date from {filepath.name}")
                files_with_errors.append(filepath.name)
                continue

            # Process file
            records = process_file(filepath, pub_day, pub_month, pub_year)
            all_records.extend(records)
            files_processed += 1

            if files_processed % 10 == 0:
                print(f"Processed {files_processed}/{len(target_files)} files, {len(all_records)} records so far...")

        except Exception as e:
            print(f"Error processing {filepath.name}: {e}")
            files_with_errors.append(filepath.name)

    # Write CSV
    if all_records:
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'format_type', 'confidence', 'raw_line'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(f"\n✓ Successfully processed {files_processed} files")
        print(f"✓ Extracted {len(all_records)} ship arrival records")
        print(f"✓ Output saved to: {output_file}")

        if files_with_errors:
            print(f"\n⚠ {len(files_with_errors)} files had errors:")
            for fname in files_with_errors:
                print(f"  - {fname}")
    else:
        print("No records extracted!")

    return len(all_records)

if __name__ == "__main__":
    total_records = main()
