#!/usr/bin/env python3
"""
TTJ Shipment Parser v2 - Line-by-line pattern matching approach.
Processes every line to extract ship arrival records, regardless of section boundaries.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RecordFormat(Enum):
    """Different record format patterns identified."""
    EARLY_AT = "early_at"           # Ship @ Origin,—cargo
    STANDARD_DASH = "standard_dash"  # Date Ship-Origin-Cargo-Merchant
    CONDENSED = "condensed"          # Ship-Origin-cargo-Merchant (no date)
    CONTINUATION = "continuation"    # Continuation of previous record
    UNKNOWN = "unknown"


@dataclass
class ShipRecord:
    """Parsed ship arrival record."""
    raw_line: str
    line_number: int

    # Core fields
    ship_name: Optional[str] = None
    origin_port: Optional[str] = None
    destination_port: Optional[str] = None
    cargo: Optional[str] = None
    merchant: Optional[str] = None

    # Date fields
    arrival_date: Optional[str] = None
    day: Optional[int] = None
    month: Optional[str] = None
    year: Optional[int] = None

    # Metadata
    is_steamship: bool = False
    format_type: Optional[RecordFormat] = None
    confidence: float = 0.0


class TTJLineParser:
    """Parse individual lines to extract ship records."""

    def __init__(self):
        # Pattern for EARLY format: Ship @ Origin,—cargo details
        # Example: "Charlotte Vede @ Champion Bay, &c.—115 pcs. timber, Order."
        # Example: "April 27. Andreas @ Fredrikstad,—54,266 boards, Nil."
        self.early_at_pattern = re.compile(
            r'^(?:(?P<month>\w{3,4})\.\s+)?(?:(?P<day>\d{1,2})\s+)?'  # Optional month and day
            r'(?P<ship>[A-Za-z\s\.\&\'\-]+?)\s*'                      # Ship name
            r'(?:\(s\))?\s*'                                           # Optional steamship marker
            r'@\s*'                                                    # @ delimiter
            r'(?P<origin>[A-Za-z\s\.,\-&]+?)\s*'                      # Origin port
            r'[,\.—]\s*'                                               # Separator (comma, period, or em-dash)
            r'(?P<cargo>.*?)$',                                        # Cargo (rest of line)
            re.IGNORECASE
        )

        # Pattern for STANDARD DASH format: Date Ship-Origin-Cargo-Merchant
        # Example: "Sept. 11 Essex (s)-Konigsberg-sleepers-Order"
        self.standard_dash_pattern = re.compile(
            r'^(?:(?P<month>\w{3,4})\.\s+)?(?P<day>\d{1,2})\s+'  # Optional month, required day
            r'(?P<ship>[A-Za-z\s\.\&\'\-]+?)\s*'                 # Ship name
            r'(?:\(s\))?\s*-\s*'                                  # Dash separator (+ optional (s))
            r'(?P<origin>[A-Za-z\s\.,\'\-]+?)\s*-\s*'            # Origin port
            r'(?P<cargo>[^-]+?)\s*-\s*'                          # Cargo
            r'(?P<merchant>.+?)$',                                # Merchant/consignee
            re.IGNORECASE
        )

        # Pattern for CONDENSED format (no date prefix): Ship-Origin-Cargo-Merchant
        # Example: "Fatfield (s)-Memel-sleepers, deals-Order"
        self.condensed_dash_pattern = re.compile(
            r'^(?P<ship>[A-Z][A-Za-z\s\.\&\'\-]+?)\s*'           # Ship name (starts with capital)
            r'(?:\(s\))?\s*-\s*'                                  # Dash separator (+ optional (s))
            r'(?P<origin>[A-Za-z\s\.,\'\-]+?)\s*-\s*'            # Origin port
            r'(?P<cargo>[^-]+?)\s*-\s*'                          # Cargo
            r'(?P<merchant>.+?)$',                                # Merchant/consignee
            re.IGNORECASE
        )

        # Port header pattern (all caps ending with period)
        self.port_header_pattern = re.compile(r'^([A-Z\s&\.\'\(\)]+)\.\s*$')

        # Current context (for multi-line records)
        self.current_port = None
        self.current_month = None
        self.current_year = None

    def set_context(self, port: str = None, month: str = None, year: int = None):
        """Set parsing context for subsequent records."""
        if port:
            self.current_port = port
        if month:
            self.current_month = month
        if year:
            self.current_year = year

    def parse_line(self, line: str, line_number: int = 0) -> Optional[ShipRecord]:
        """
        Parse a single line to extract ship record.

        Args:
            line: Text line to parse
            line_number: Line number in source file

        Returns:
            ShipRecord if pattern matched, None otherwise
        """
        line = line.strip()

        # Skip empty lines
        if not line:
            return None

        # Check for port header (update context)
        port_match = self.port_header_pattern.match(line)
        if port_match:
            self.current_port = port_match.group(1).rstrip('.')
            return None

        # Try each pattern in order of specificity

        # 1. Try EARLY @ format
        match = self.early_at_pattern.match(line)
        if match:
            return self._build_record(match, line, line_number, RecordFormat.EARLY_AT)

        # 2. Try STANDARD DASH format (with date)
        match = self.standard_dash_pattern.match(line)
        if match:
            return self._build_record(match, line, line_number, RecordFormat.STANDARD_DASH)

        # 3. Try CONDENSED DASH format (no date)
        match = self.condensed_dash_pattern.match(line)
        if match:
            return self._build_record(match, line, line_number, RecordFormat.CONDENSED)

        # No pattern matched
        return None

    def _build_record(self, match: re.Match, raw_line: str,
                     line_number: int, format_type: RecordFormat) -> ShipRecord:
        """Build ShipRecord from regex match."""
        groups = match.groupdict()

        # Extract fields
        ship_name = groups.get('ship', '').strip()
        origin_port = groups.get('origin', '').strip()
        cargo = groups.get('cargo', '').strip()
        merchant = groups.get('merchant', '').strip() if 'merchant' in groups else None

        # Date fields
        day = groups.get('day')
        month = groups.get('month') or self.current_month

        # Detect steamship
        is_steamship = '(s)' in raw_line

        # Clean up ship name (remove (s) marker)
        ship_name = ship_name.replace('(s)', '').strip()

        # Build record
        record = ShipRecord(
            raw_line=raw_line,
            line_number=line_number,
            ship_name=ship_name,
            origin_port=origin_port,
            destination_port=self.current_port,
            cargo=cargo,
            merchant=merchant,
            day=int(day) if day else None,
            month=month,
            year=self.current_year,
            is_steamship=is_steamship,
            format_type=format_type,
            confidence=1.0  # High confidence for pattern matches
        )

        # Update month context if present in this record
        if groups.get('month'):
            self.current_month = groups['month']

        return record

    def parse_file(self, file_path: Path, year: int = None) -> List[ShipRecord]:
        """
        Parse entire file line by line.

        Args:
            file_path: Path to OCR text file
            year: Publication year (for date context)

        Returns:
            List of ShipRecord objects
        """
        if year:
            self.set_context(year=year)

        records = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                record = self.parse_line(line, line_num)
                if record:
                    records.append(record)

        return records


def extract_year_from_filename(filename: str) -> Optional[int]:
    """Extract year from filename."""
    match = re.search(r'(187[4-9]|188[0-9]|189[0-9])', filename)
    return int(match.group(1)) if match else None


def main():
    """Test the line parser."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ttj_parser_v2.py <ocr_file.txt>")
        sys.exit(1)

    test_file = Path(sys.argv[1])

    # Extract year from filename
    year = extract_year_from_filename(test_file.name)
    if year:
        print(f"Detected year: {year}")

    # Parse file
    parser = TTJLineParser()
    records = parser.parse_file(test_file, year=year)

    print(f"\nParsed {len(records)} ship records:")
    print("=" * 80)

    # Show statistics by format
    from collections import Counter
    format_counts = Counter(r.format_type.value for r in records)
    print("\nFormat distribution:")
    for fmt, count in format_counts.most_common():
        print(f"  {fmt}: {count}")

    # Show first 10 records
    print(f"\nFirst 10 records:")
    print("-" * 80)
    for i, record in enumerate(records[:10], 1):
        print(f"\n{i}. Line {record.line_number}: {record.format_type.value}")
        print(f"   Ship: {record.ship_name}")
        print(f"   From: {record.origin_port} → To: {record.destination_port}")
        print(f"   Cargo: {record.cargo[:60]}...")
        if record.merchant:
            print(f"   Merchant: {record.merchant}")
        if record.day:
            print(f"   Date: {record.month} {record.day}, {record.year}")
        print(f"   Steamship: {record.is_steamship}")

    # Show unique ports
    ports = set(r.destination_port for r in records if r.destination_port)
    print(f"\n\nDestination ports found ({len(ports)}):")
    for port in sorted(ports):
        count = sum(1 for r in records if r.destination_port == port)
        print(f"  {port}: {count} arrivals")


if __name__ == '__main__':
    main()
