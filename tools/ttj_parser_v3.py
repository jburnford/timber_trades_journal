#!/usr/bin/env python3
"""
TTJ Shipment Parser v3 - Context-aware line parser with lookback.
Examines preceding lines to capture port headers and date context.
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
    UNKNOWN = "unknown"


# UTF-8 encoding fixes for double-encoded characters
# These appear in OCR output when UTF-8 was misinterpreted as Latin-1
ENCODING_FIXES = {
    # Complete port names (exact replacement)
    'GÃ¤vle': 'Gävle',
    'VÃ¤stervik': 'Västervik',
    'MÃ¶nsterÃ¥s': 'Mönsterås',
    'TimrÃ¥': 'Timrå',
    'VilagarcÃ\xada de Arousa': 'Vilagarcía de Arousa',
    'A CoruÃ±a': 'A Coruña',
    'TÃ¸nsberg': 'Tønsberg',
    'Trois-RiviÃ¨res': 'Trois-Rivières',
    "Pont-l'Abbé": "Pont-l'Abbé",
    'Â\xa0Saint-Brieuc': 'Saint-Brieuc',
    'Â Saint-Brieuc': 'Saint-Brieuc',

    # Character patterns (for partial matches)
    'Ã¤': 'ä',  # Swedish/German a-umlaut
    'Ã¶': 'ö',  # Swedish/German o-umlaut
    'Ã¥': 'å',  # Swedish/Norwegian a-ring
    'Ã¸': 'ø',  # Norwegian/Danish o-slash
    'Ã±': 'ñ',  # Spanish n-tilde
    'Ã©': 'é',  # French e-acute
    'Ã¨': 'è',  # French e-grave
    'Ã­': 'í',  # Spanish i-acute
}

def fix_encoding(text: Optional[str]) -> Optional[str]:
    """Fix double-encoded UTF-8 text (Latin-1 misinterpretation).

    Args:
        text: Original text that may contain corrupted encoding

    Returns:
        Text with encoding fixed, or None if input was None
    """
    if not text:
        return text

    # Try exact replacement first (faster for known complete strings)
    if text in ENCODING_FIXES:
        return ENCODING_FIXES[text]

    # Apply pattern replacements for partial corruption
    fixed = text
    for corrupted, correct in ENCODING_FIXES.items():
        # Only apply pattern replacements (short sequences)
        if len(corrupted) <= 3:
            fixed = fixed.replace(corrupted, correct)

    return fixed


# Non-port headers to skip (journal headers, commodities, advertisements)
SKIP_HEADERS = {
    # Journal headers
    'TIMBER TRADES JOURNAL', 'TIMBER TRADES\' JOURNAL', 'ADES JOURNAL',
    'ENGLAND AND WALES', 'SCOTLAND', 'IRELAND', 'SCOTCH SUPPLEMENT',
    'IMPORTS', 'REVIEWS', 'FREIGHTS', 'FAILURES AND ARRANGEMENTS',
    'LIQUIDATIONS', 'ERRATUM', 'TRADE ITEMS', 'CREDITOR PARTLY SECURED',
    'ACCEPTED TENDERS', 'LONDON DOCK DELIVERIES', 'ARRIVALS',

    # Timber commodities
    'PINE', 'SPRUCE', 'PITCH PINE', 'OAK', 'OAK TIMBER', 'MAHOGANY', 'ASH',
    'LATHWOOD', 'WEATHERBOARDS', 'SLATING BATTENS', 'MOULDING', 'MOULDINGS',
    'VENEERS', 'SLAB BOARDS', 'POLES', 'SPARS', 'DECK DEALS', 'LATHS',
    'PLASTERERS\' LATHS', 'BEAD', 'TORUS SKIRTING', 'DEAL', 'ERABLE',
    'HEWN BALK', 'AHOGANY',

    # Advertisements and misc
    'CONTRACTS OPEN', 'TRADE MARK', 'ILLUSTRATED CATALOGUES FREE ON APPLICATION',
    'POST FREE ON APPLICATION', 'EXPORT ORDERS PROMPTLY EXECUTED',
    'WRITE FOR CATALOGUE', 'DETAILED SPECIFICATION ON APPLICATION',
    'COUNTRY ORDERS RECEIVE PROMPT ATTENTION', 'SEND FOR REFERENCES TO USERS',
    'REGISTERED BRAND', 'SILVER MEDAL', 'CIRCULAR SAWS', 'IN THE WORLD',
    'SPECIFICATIONS OF THE FOLLOWING HAVE BEEN PUBLISHED',
    'EVERY DESCRIPTION OF BALTIC AND AMERICAN TIMBER',
    'VENEERS OF ALL KINDS', 'AND ALL VARIETIES OF FANCY WOODS',
    'EVERY DESCRIPTION OF WOOD ALWAYS IN STOCK',
    'PREPARED FROM THE DIMENSIONS STATED',
    'EXPORTERS AMERICAN HARDWOOD LUMBER',
    'AUSTRALIAN TIMBER TRADE', 'TIMBER FROM CORSICA',
    'SEEDLING AND TRANSPLANTED FOREST TREES',
    'HORTICULTURAL TIMBER MERCHANT', 'THE STANDARD TIMBER MEASURER',
    'GANDY\'S PATENT COTTON BELTING', 'THE GANDY BELT',

    # Company names / abbreviations
    'MAURICE GANDY', 'THOMAS ROEBUCK & COMPANY (LIMITED)',
    'JOSEPH GARDNER & SONS', 'ROBERT PARKER & CO', 'LAVY BROS',

    # Geographic/location indicators
    'AT NEW ORLEANS', 'THE MISSISSIPPI VALLEY', 'THE HAWAIIAN ISLANDS',
    'BRANCH YARD AT NEWBURGH', 'AT THE MILLWALL DOCKS', 'AT AVONMOUTH',
    'BY SURREY COMMERCIAL DOCKS',

    # Typos/OCR errors/Single letters
    'R. M', 'R & CO', 'H', 'A', 'ONE', 'EST', 'TONE', 'BURGH',
    'J. H. ROW... AU', 'B. & F. S. WHARF', 'B. & F. WHARF',
    'Y COMMERCIAL DOCKS', 'COLUMBIA', 'MILWALL'
}


@dataclass
class ShipRecord:
    """Parsed ship arrival record."""
    raw_line: str
    line_number: int
    preceding_context: List[str]  # Lines above this record

    # Core fields
    ship_name: Optional[str] = None
    origin_port: Optional[str] = None
    destination_port: Optional[str] = None
    cargo: Optional[str] = None
    merchant: Optional[str] = None

    # Date fields (from content - actual arrival dates)
    arrival_date: Optional[str] = None
    day: Optional[int] = None
    month: Optional[str] = None
    year: Optional[int] = None

    # Publication date (from filename - fallback/approximate)
    publication_year: Optional[int] = None
    publication_month: Optional[str] = None
    publication_day: Optional[int] = None

    # Metadata
    is_steamship: bool = False
    format_type: Optional[RecordFormat] = None
    confidence: float = 0.0


class TTJContextParser:
    """Parse ship records with context from preceding lines."""

    def __init__(self):
        # Ship record patterns
        # Early @ format handles: "April 27. Ship @..." and "Sept. 11 Ship @..."
        # Fixed to handle abbreviations like "St. John, N.B." without truncation
        # Uses lookahead to stop at comma+em-dash or comma+digit
        self.early_at_pattern = re.compile(
            r'^(?:(?P<month>\w{3,9})\.?\s+(?P<day>\d{1,2})\.?\s+)?'
            r'(?P<ship>[A-Za-z\s\.\&\'\-]+?)\s*'
            r'(?:\(s\))?\s*'
            r'@\s*'
            r'(?P<origin>[A-Za-z\s\.,\-&]+?)'
            r',?\s*(?=[—\d])'  # Optional comma, then lookahead for em-dash or digit
            r'(?P<cargo>.*?)$',
            re.IGNORECASE
        )

        self.standard_dash_pattern = re.compile(
            r'^(?:(?P<month>\w{3,9})\.\s+)?(?P<day>\d{1,2})\s+'
            r'(?P<ship>[A-Za-z\s\.\&\'\-]+?)\s*'
            r'(?:\(s\))?\s*-\s*'
            r'(?P<origin>[A-Za-z\s\.,\'\-]+?)\s*-\s*'
            r'(?P<cargo>[^-]+?)\s*-\s*'
            r'(?P<merchant>.+?)$',
            re.IGNORECASE
        )

        self.condensed_dash_pattern = re.compile(
            r'^(?P<ship>[A-Z][A-Za-z\s\.\&\'\-]+?)\s*'
            r'(?:\(s\))?\s*-\s*'
            r'(?P<origin>[A-Za-z\s\.,\'\-]+?)\s*-\s*'
            r'(?P<cargo>[^-]+?)\s*-\s*'
            r'(?P<merchant>.+?)$',
            re.IGNORECASE
        )

        # Context extraction patterns
        self.port_header_pattern = re.compile(r'^([A-Z\s&\.\'\(\)]+)\.\s*$')

        # Date header patterns (appear above ship records)
        # Example: "April 16." or "Sept. 11" or "Dec. 22"
        self.date_header_pattern = re.compile(
            r'^(?P<month>\w{3,9})\.\s+(?P<day>\d{1,2})\.?\s*$',
            re.IGNORECASE
        )

        # Persistent context (maintained across file boundaries)
        self.current_port = None
        self.current_city = None  # Track city context for dock disambiguation
        self.current_month = None
        self.current_day = None

        # List of known UK port cities that appear as headers
        self.uk_cities = {
            'LONDON', 'LIVERPOOL', 'GLASGOW', 'GREENOCK', 'GRANGEMOUTH',
            'LEITH', 'DUNDEE', 'ABERDEEN', 'BRISTOL', 'CARDIFF', 'HULL',
            'NEWCASTLE', 'SUNDERLAND', 'MIDDLESBROUGH', 'HARTLEPOOL',
            'MANCHESTER', 'GOOLE', 'GRIMSBY', 'SOUTHAMPTON', 'PLYMOUTH',
            'BELFAST', 'DUBLIN', 'CORK', 'BARROW', 'PRESTON'
        }

        # Dock keywords that need city context
        self.dock_keywords = {
            'DOCK', 'DOCKS', 'WHARF', 'WHARVES', 'PIER', 'QUAY'
        }

    def extract_port_from_context(self, context_lines: List[str]) -> Optional[str]:
        """
        Extract destination port from preceding lines.
        Also handles city context for dock names.

        Args:
            context_lines: Previous 2-4 lines before ship record

        Returns:
            Port name if found, None otherwise
        """
        city_context = None
        port_found = None

        # Search backwards through context
        for line in reversed(context_lines):
            line = line.strip()
            match = self.port_header_pattern.match(line)
            if match:
                port = match.group(1).rstrip('.')
                # Filter out non-port headers using comprehensive skip list
                port_upper = port.upper()
                if (len(port) > 2 and
                    not re.match(r'^\d', port) and
                    not any(skip in port_upper for skip in SKIP_HEADERS)):

                    # Check if this is a city header
                    if port_upper in self.uk_cities:
                        city_context = port
                        continue  # Keep looking for dock name

                    # Check if this is a dock name
                    if any(keyword in port_upper for keyword in self.dock_keywords):
                        # If we found a city before this, prepend it
                        if city_context:
                            return f"{city_context} ({port})"
                        else:
                            return port
                    else:
                        # Regular port name
                        return port

        return port_found

    def extract_date_from_context(self, context_lines: List[str]) -> Tuple[Optional[str], Optional[int]]:
        """
        Extract month and day from preceding lines.

        Args:
            context_lines: Previous 2-4 lines before ship record

        Returns:
            Tuple of (month, day) if found
        """
        # Search backwards through context for date headers
        for line in reversed(context_lines):
            line = line.strip()
            match = self.date_header_pattern.match(line)
            if match:
                return match.group('month'), int(match.group('day'))
        return None, None

    def parse_line_with_context(self, line: str, context_lines: List[str],
                               line_number: int = 0, year: int = None) -> Optional[ShipRecord]:
        """
        Parse a single line with awareness of preceding context.

        Args:
            line: Text line to parse
            context_lines: Previous 2-4 lines for context
            line_number: Line number in source file
            year: Publication year

        Returns:
            ShipRecord if pattern matched, None otherwise
        """
        line = line.strip()

        # Skip empty lines and port headers
        if not line or self.port_header_pattern.match(line):
            return None

        # Try each pattern
        match = None
        format_type = None

        # Try early @ format
        if '@' in line:
            match = self.early_at_pattern.match(line)
            if match:
                format_type = RecordFormat.EARLY_AT

        # Try standard dash format (with date)
        if not match and re.match(r'^\w+\.\s+\d{1,2}\s+', line):
            match = self.standard_dash_pattern.match(line)
            if match:
                format_type = RecordFormat.STANDARD_DASH

        # Try condensed dash format
        if not match and '-' in line:
            match = self.condensed_dash_pattern.match(line)
            if match:
                format_type = RecordFormat.CONDENSED

        if not match:
            return None

        # Build basic record from pattern
        groups = match.groupdict()

        ship_name = groups.get('ship', '').strip()
        origin_port = groups.get('origin', '').strip()
        cargo = groups.get('cargo', '').strip()
        merchant = groups.get('merchant', '').strip() if 'merchant' in groups else None

        # Fix encoding for origin port (double-encoded UTF-8)
        origin_port = fix_encoding(origin_port) if origin_port else origin_port

        # Extract date from line or context
        day = groups.get('day')
        month = groups.get('month')

        # If no date in line, check context
        if not day or not month:
            context_month, context_day = self.extract_date_from_context(context_lines)
            if not month:
                month = context_month
            if not day and context_day:
                day = context_day

        # Extract destination port from context
        destination_port = self.extract_port_from_context(context_lines)

        # Fix encoding for destination port (double-encoded UTF-8)
        destination_port = fix_encoding(destination_port) if destination_port else destination_port

        # Detect steamship
        is_steamship = '(s)' in line

        # Clean ship name
        ship_name = ship_name.replace('(s)', '').strip()

        # Build record
        record = ShipRecord(
            raw_line=line,
            line_number=line_number,
            preceding_context=context_lines[-4:],  # Keep last 4 lines
            ship_name=ship_name,
            origin_port=origin_port,
            destination_port=destination_port,
            cargo=cargo,
            merchant=merchant,
            day=int(day) if day else None,
            month=month,
            year=year,
            is_steamship=is_steamship,
            format_type=format_type,
            confidence=1.0 if destination_port else 0.7  # Lower confidence if no port found
        )

        return record

    def parse_file(self, file_path: Path, year: int = None) -> List[ShipRecord]:
        """
        Parse entire file with context awareness.

        Args:
            file_path: Path to OCR text file
            year: Publication year (for date context, optional)

        Returns:
            List of ShipRecord objects
        """
        records = []

        # Extract publication date from filename
        pub_year, pub_month, pub_day = extract_publication_date_from_filename(file_path.name)

        # Use publication year if not explicitly provided
        if not year:
            year = pub_year

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Use instance-level persistent context (maintained across pages)
        # No reset - context carries forward from previous files

        # Process each line with context
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Update persistent port/city context if we see a port header
            port_match = self.port_header_pattern.match(line_stripped)
            if port_match:
                port_candidate = port_match.group(1).rstrip('.')
                # Filter out non-port headers using comprehensive skip list
                port_upper = port_candidate.upper()
                if not any(skip in port_upper for skip in SKIP_HEADERS):
                    # Check if this is a city header (major UK port city)
                    if port_upper in self.uk_cities:
                        self.current_city = port_candidate
                        # Don't set current_port for city headers - wait for dock name
                    else:
                        # Check if this is a dock name that needs city context
                        if any(keyword in port_upper for keyword in self.dock_keywords):
                            # Prepend city name if available
                            if self.current_city:
                                self.current_port = f"{self.current_city} ({port_candidate})"
                            else:
                                self.current_port = port_candidate
                            # Keep city context for subsequent docks in same city
                        else:
                            # Regular port name (not a dock, not a city)
                            self.current_port = port_candidate
                            # Reset city context - we've moved to a different port
                            self.current_city = None
                continue

            # Update persistent date context if we see a date header
            date_match = self.date_header_pattern.match(line_stripped)
            if date_match:
                self.current_month = date_match.group('month')
                self.current_day = int(date_match.group('day'))

            # Get preceding 2-4 lines for immediate context
            context_start = max(0, i - 4)
            context_lines = [lines[j].strip() for j in range(context_start, i)]

            record = self.parse_line_with_context(line, context_lines, i + 1, year)
            if record:
                # Apply persistent context if not found in immediate context
                if not record.destination_port and self.current_port:
                    record.destination_port = self.current_port
                    record.confidence = 0.9  # Slightly lower than immediate context

                if not record.month and self.current_month:
                    record.month = self.current_month
                if not record.day and self.current_day:
                    record.day = self.current_day

                # Update persistent context from this record
                # (dates in record lines act as context for subsequent records)
                if record.month:
                    self.current_month = record.month
                if record.day:
                    self.current_day = record.day

                # Add publication date from filename
                record.publication_year = pub_year
                record.publication_month = pub_month
                record.publication_day = pub_day

                records.append(record)

        return records


def extract_year_from_filename(filename: str) -> Optional[int]:
    """Extract year from filename."""
    match = re.search(r'(187[4-9]|188[0-9]|189[0-9])', filename)
    return int(match.group(1)) if match else None


def extract_publication_date_from_filename(filename: str) -> Tuple[Optional[int], Optional[str], Optional[int]]:
    """
    Extract publication date from filename.

    Args:
        filename: Name of file

    Returns:
        Tuple of (year, month, day) where month is string name
    """
    # Pattern 1: Numeric format YYYYMMDD (e.g., "18790426p.11_p001.txt")
    match = re.search(r'(187[4-9]|188[0-9]|189[0-9])(\d{2})(\d{2})', filename)
    if match:
        year = int(match.group(1))
        month_num = int(match.group(2))
        day = int(match.group(3))

        # Convert month number to name
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        if 1 <= month_num <= 12:
            month = month_names[month_num - 1]
            return year, month, day

    # Pattern 2: Descriptive format "Month Day Year" (e.g., "May 1 1875")
    # Flexible month matching to handle OCR errors (e.g., "Augus" instead of "August")
    match = re.search(
        r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:us)?(?:t)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\w*\s+(\d{1,2})\s+(187[4-9]|188[0-9]|189[0-9])',
        filename, re.I
    )
    if match:
        month_abbrev = match.group(1)[:3].capitalize()
        # Map abbreviation to full month name
        month_map = {
            'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April',
            'May': 'May', 'Jun': 'June', 'Jul': 'July', 'Aug': 'August',
            'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'
        }
        month = month_map.get(month_abbrev, match.group(1).capitalize())
        day = int(match.group(2))
        year = int(match.group(3))
        return year, month, day

    # Fallback: Just year
    year = extract_year_from_filename(filename)
    return year, None, None


def main():
    """Test the context-aware parser."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ttj_parser_v3.py <ocr_file.txt>")
        sys.exit(1)

    test_file = Path(sys.argv[1])

    # Extract publication date from filename
    pub_year, pub_month, pub_day = extract_publication_date_from_filename(test_file.name)
    if pub_year:
        pub_date_str = f"{pub_year}"
        if pub_month:
            pub_date_str = f"{pub_month} {pub_day}, {pub_year}" if pub_day else f"{pub_month} {pub_year}"
        print(f"Publication date: {pub_date_str}")

    # Parse file
    parser = TTJContextParser()
    records = parser.parse_file(test_file)

    print(f"\nParsed {len(records)} ship records:")
    print("=" * 80)

    # Show statistics
    from collections import Counter

    format_counts = Counter(r.format_type.value for r in records)
    print("\nFormat distribution:")
    for fmt, count in format_counts.most_common():
        print(f"  {fmt}: {count}")

    # Port coverage
    with_port = sum(1 for r in records if r.destination_port)
    print(f"\nPort coverage: {with_port}/{len(records)} ({100*with_port/len(records):.1f}%)")

    # Date coverage
    with_date = sum(1 for r in records if r.day and r.month)
    print(f"Date coverage: {with_date}/{len(records)} ({100*with_date/len(records):.1f}%)")

    # Show first 10 records with context
    print(f"\nFirst 10 records:")
    print("-" * 80)
    for i, record in enumerate(records[:10], 1):
        print(f"\n{i}. Line {record.line_number}: {record.format_type.value} (confidence: {record.confidence})")
        print(f"   Ship: {record.ship_name}")
        print(f"   From: {record.origin_port} → To: {record.destination_port or 'UNKNOWN'}")
        print(f"   Cargo: {record.cargo[:60]}...")
        if record.merchant:
            print(f"   Merchant: {record.merchant}")
        if record.day and record.month:
            print(f"   Arrival date: {record.month} {record.day}, {record.year}")
        if record.publication_day and record.publication_month:
            print(f"   Publication: {record.publication_month} {record.publication_day}, {record.publication_year}")
        print(f"   Steamship: {record.is_steamship}")

        # Show context
        if record.preceding_context:
            print(f"   Context (prev lines):")
            for ctx_line in record.preceding_context[-2:]:  # Show last 2 context lines
                if ctx_line:
                    print(f"     {ctx_line[:70]}")

    # Show unique ports
    ports = set(r.destination_port for r in records if r.destination_port)
    print(f"\n\nDestination ports found ({len(ports)}):")
    for port in sorted(ports):
        count = sum(1 for r in records if r.destination_port == port)
        print(f"  {port}: {count} arrivals")

    # Show records without ports
    no_port = [r for r in records if not r.destination_port]
    if no_port:
        print(f"\n\nRecords without port ({len(no_port)}):")
        for r in no_port[:5]:  # Show first 5
            print(f"  Line {r.line_number}: {r.ship_name} from {r.origin_port}")


if __name__ == '__main__':
    main()
