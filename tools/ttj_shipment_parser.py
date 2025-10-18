#!/usr/bin/env python3
"""
TTJ Shipment Parser - Extract structured shipment data from Timber Trades Journal OCR
Parses ship arrivals at British ports with cargo and merchant details.
"""

import re
import csv
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class TTJShipmentParser:
    """Parse timber shipment records from TTJ OCR text."""

    def __init__(self):
        # Patterns for different record formats
        self.port_pattern = re.compile(r'^([A-Z\s&\.\']+)\.$', re.MULTILINE)

        # Ship record pattern: Date Ship(s)-Origin-Cargo-Merchant
        # Example: "22 Australia (s)-Australia-1,587 bdls staves, 22 bdls. lumber-Order"
        self.ship_pattern = re.compile(
            r'^(\d{1,2})\s+'                          # Date (day of month)
            r'([A-Za-z\s\.\&\'\-]+?)'                 # Ship name
            r'(?:\s*\(s\))?'                          # Optional (s) for steamship
            r'\s*-\s*'                                # Separator
            r'([A-Za-z\s\.,\-]+?)'                    # Origin port
            r'\s*-\s*'                                # Separator
            r'(.*?)'                                  # Cargo description
            r'\s*-\s*'                                # Separator
            r'([A-Za-z\s\.,\&\;\-]+?)$',              # Merchant/consignee
            re.MULTILINE
        )

        # Alternate pattern for records with multiple merchants
        # Example: "200 pcs. lumber-Churchill & Co.; 96 deals-Order"
        self.cargo_merchant_pattern = re.compile(
            r'([^;-]+?)\s*-\s*([A-Za-z\s\.,\&]+?)(?:;|$)'
        )

    def extract_port_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Extract port sections from OCR text.

        Args:
            text: Full OCR text from TTJ page

        Returns:
            List of dicts with port name and associated text
        """
        sections = []
        lines = text.split('\n')
        current_port = None
        current_text = []

        for line in lines:
            # Check if this is a port header (all caps, ends with period)
            if self.port_pattern.match(line.strip()):
                # Save previous section
                if current_port:
                    sections.append({
                        'port': current_port,
                        'text': '\n'.join(current_text)
                    })
                # Start new section
                current_port = line.strip().rstrip('.')
                current_text = []
            elif current_port:
                current_text.append(line)

        # Save final section
        if current_port:
            sections.append({
                'port': current_port,
                'text': '\n'.join(current_text)
            })

        return sections

    def parse_shipment_record(self, line: str, port: str, year: int, month: str) -> Optional[Dict]:
        """
        Parse a single shipment record line.

        Args:
            line: Single line with ship record
            port: Destination port name
            year: Year of publication
            month: Month name

        Returns:
            Dict with parsed shipment data or None if no match
        """
        match = self.ship_pattern.match(line.strip())
        if not match:
            return None

        day, ship_name, origin, cargo, merchant = match.groups()

        # Detect steamship
        is_steamship = '(s)' in line
        ship_name = ship_name.replace('(s)', '').strip()

        # Try to parse date
        try:
            date_str = f"{year}-{month}-{day.zfill(2)}"
            arrival_date = datetime.strptime(date_str, "%Y-%B-%d").date()
        except:
            arrival_date = None

        # Clean up fields
        origin = origin.strip()
        cargo = cargo.strip()
        merchant = merchant.strip()

        return {
            'port': port,
            'arrival_date': str(arrival_date) if arrival_date else f"{year}-{month}-{day}",
            'day': int(day),
            'month': month,
            'year': year,
            'ship_name': ship_name,
            'is_steamship': is_steamship,
            'origin_port': origin,
            'cargo': cargo,
            'merchant': merchant,
            'raw_line': line.strip()
        }

    def parse_cargo_details(self, cargo_text: str) -> List[Dict[str, str]]:
        """
        Parse cargo description into structured items.

        Args:
            cargo_text: Cargo description string

        Returns:
            List of cargo items with quantity, unit, type
        """
        items = []

        # Pattern: quantity unit type
        # Examples: "1,587 bdls staves", "22 bdls. lumber", "841 bdls. headings"
        cargo_pattern = re.compile(
            r'(\d{1,3}(?:,\d{3})*)\s+'    # Quantity with commas
            r'([a-z\.]+)\s+'               # Unit (bdls, pcs, lds, etc.)
            r'([a-z\s\.]+?)(?:,|;|$|\s*-)',  # Type (staves, lumber, etc.)
            re.IGNORECASE
        )

        for match in cargo_pattern.finditer(cargo_text):
            quantity, unit, cargo_type = match.groups()
            items.append({
                'quantity': int(quantity.replace(',', '')),
                'unit': unit.rstrip('.'),
                'type': cargo_type.strip()
            })

        return items

    def parse_text(self, text: str, year: int, month: str) -> List[Dict]:
        """
        Parse full OCR text into shipment records.

        Args:
            text: Full OCR text from TTJ page
            year: Year of publication
            month: Month name (e.g., "August")

        Returns:
            List of parsed shipment records
        """
        shipments = []

        # Extract port sections
        port_sections = self.extract_port_sections(text)

        for section in port_sections:
            port = section['port']
            lines = section['text'].split('\n')

            for line in lines:
                if not line.strip():
                    continue

                # Try to parse as shipment record
                record = self.parse_shipment_record(line, port, year, month)
                if record:
                    # Parse cargo details
                    record['cargo_items'] = self.parse_cargo_details(record['cargo'])
                    shipments.append(record)

        return shipments

    def save_to_csv(self, shipments: List[Dict], output_file: Path):
        """Save parsed shipments to CSV."""
        if not shipments:
            return

        fieldnames = [
            'port', 'arrival_date', 'day', 'month', 'year',
            'ship_name', 'is_steamship', 'origin_port',
            'cargo', 'merchant', 'raw_line'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(shipments)

    def save_to_json(self, shipments: List[Dict], output_file: Path):
        """Save parsed shipments to JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(shipments, f, indent=2, ensure_ascii=False)


def main():
    """Test the parser on sample text."""
    parser = TTJShipmentParser()

    # Sample text from your example
    sample_text = """SURREY COMMERCIAL DOCKS
Aug. 22 Australia (s)-Australia-1,587 bdls staves, 22 bdls. lumber, 841 bdls. headings, 393 bdls. wash boards-Order
20 France (s)-New York-500 staves-Churchill & Sim; 43 cs. handles-Robbins & Co.; 89 pkgs. oak blocks-Bennet Furnishing Co.; 26 cs. handles-Order
TILBURY DOCKS.
Aug. 20 Maryland-Baltimore-2,500 staves-Order
Aug. 23 Imbros (s) - Baltimore - 144 logs, 1,055 pcs. lumber-W. Mallinson; 200 pcs. lumber-Churchhill & Co.; 96 deals-Order"""

    shipments = parser.parse_text(sample_text, year=1887, month="August")

    print(f"Parsed {len(shipments)} shipments:")
    for ship in shipments:
        print(f"\n{ship['ship_name']} from {ship['origin_port']} to {ship['port']}")
        print(f"  Date: {ship['arrival_date']}")
        print(f"  Cargo: {ship['cargo']}")
        print(f"  Merchant: {ship['merchant']}")
        if ship['cargo_items']:
            print(f"  Cargo items: {len(ship['cargo_items'])} items")

    # Save to JSON
    parser.save_to_json(shipments, Path('sample_shipments.json'))
    print(f"\nSaved to sample_shipments.json")


if __name__ == '__main__':
    main()
