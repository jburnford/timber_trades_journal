#!/usr/bin/env python3
"""
Page-by-page custom parser - builds specific logic for each timeout file
"""

import csv
import re
from pathlib import Path
from typing import List, Dict

def parse_page_1_p002(file_path: Path) -> List[Dict]:
    """
    Custom parser for: 1. p. 15-16 - Imports - January 1 1887 - Timber Trades Journal 1887_p002.txt
    Publication: January 1, 1887
    """
    records = []
    current_port = None
    last_day = None

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # Process only ship import lines (lines 1-36 based on examination)
    for i, line in enumerate(lines[:40], 1):  # Extra buffer
        line = line.strip()

        # Skip empty lines and stop at "THE GAZETTE"
        if not line or "THE GAZETTE" in line or "FAILURES" in line:
            break

        # Check for port header (all caps, ends with period or standalone)
        if line.isupper() and len(line) < 30:
            if line not in ['IRELAND', 'SCOTLAND', 'ENGLAND']:  # Skip region headers
                current_port = line.rstrip('.')
            continue

        # Skip page number
        if line.isdigit():
            continue

        # Try to parse ship line
        # Format 1: "Dec. 21 Ship-Origin-Cargo-Merchant"
        # Format 2: "22 Ship-Origin-Cargo-Merchant" (continues date)
        match = re.match(r'^([A-Za-z]+\.?\s+\d+|^\d+)\s+(.+)$', line)
        if match and current_port:
            date_part = match.group(1).strip()
            ship_info = match.group(2).strip()

            # Parse date
            if date_part.isdigit():
                # Just a day number, use last month/day
                day = int(date_part)
                month = 12  # December (from "Dec." in file)
            else:
                # Full date like "Dec. 21"
                months = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                month_match = re.match(r'([A-Za-z]+)\.?\s+(\d+)', date_part)
                if month_match:
                    month_str = month_match.group(1).lower()[:3]
                    day = int(month_match.group(2))
                    month = months.get(month_str, 1)
                    last_day = (day, month)

            # Parse ship info: Ship-Origin-Cargo-Merchant
            # Handle multiple merchants separated by semicolons
            parts = ship_info.split('-')
            if len(parts) >= 2:
                ship_name = parts[0].strip()
                is_steamship = '(s)' in ship_name
                ship_name = ship_name.replace('(s)', '').strip()

                origin_port = parts[1].strip() if len(parts) > 1 else ''

                # Cargo and merchant may be combined or separated
                if len(parts) >= 3:
                    # Check for semicolon-separated merchants
                    remainder = '-'.join(parts[2:])
                    if ';' in remainder:
                        # Multiple cargo-merchant pairs
                        segments = remainder.split(';')
                        for segment in segments:
                            seg_parts = segment.strip().split('-')
                            if len(seg_parts) >= 2:
                                cargo = seg_parts[0].strip()
                                merchant = '-'.join(seg_parts[1:]).strip()
                            else:
                                cargo = segment.strip()
                                merchant = ''

                            records.append({
                                'source_file': file_path.name,
                                'line_number': i,
                                'ship_name': ship_name,
                                'origin_port': origin_port,
                                'destination_port': current_port,
                                'cargo': cargo,
                                'merchant': merchant,
                                'arrival_day': day,
                                'arrival_month': month,
                                'arrival_year': 1886,  # Dec 1886 for Jan 1887 publication
                                'publication_day': 1,
                                'publication_month': 1,
                                'publication_year': 1887,
                                'is_steamship': is_steamship,
                                'raw_line': line
                            })
                    else:
                        # Single cargo-merchant
                        cargo_merchant_parts = remainder.split('-')
                        cargo = cargo_merchant_parts[0].strip() if len(cargo_merchant_parts) > 0 else ''
                        merchant = '-'.join(cargo_merchant_parts[1:]).strip() if len(cargo_merchant_parts) > 1 else ''

                        records.append({
                            'source_file': file_path.name,
                            'line_number': i,
                            'ship_name': ship_name,
                            'origin_port': origin_port,
                            'destination_port': current_port,
                            'cargo': cargo,
                            'merchant': merchant,
                            'arrival_day': day,
                            'arrival_month': month,
                            'arrival_year': 1886,
                            'publication_day': 1,
                            'publication_month': 1,
                            'publication_year': 1887,
                            'is_steamship': is_steamship,
                            'raw_line': line
                        })

    return records


# Test on first file
if __name__ == '__main__':
    file_path = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full/1. p. 15-16 - Imports - January 1 1887 - Timber Trades Journal 1887_p002.txt")

    records = parse_page_1_p002(file_path)

    print(f"Extracted {len(records)} records from {file_path.name}")
    print("\nFirst 10 records:")
    for i, rec in enumerate(records[:10], 1):
        print(f"{i}. {rec['ship_name']} from {rec['origin_port']} to {rec['destination_port']}")
        print(f"   Cargo: {rec['cargo'][:60]}...")
        print(f"   Merchant: {rec['merchant'][:40]}...")

    # Save to CSV
    output_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/page_by_page_records.csv")
    fieldnames = [
        'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
        'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
        'publication_day', 'publication_month', 'publication_year',
        'is_steamship', 'raw_line'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n✓ Saved to {output_file}")
