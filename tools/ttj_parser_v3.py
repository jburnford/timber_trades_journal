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
    'HEWN BALK', 'AHOGANY', 'BOARDS', 'BATTENS', 'FIREWOOD', 'TIMBER',
    'DEALS', 'LOGS', 'STICKS', 'PIECES', 'OARS', 'WOOD PULP',

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

    # Section headings frequently followed by summary tables (no single ship)
    'STAVES', 'STAVES.', 'THIS IS A WELL-KNOWN AND MUCH APPRECIATED PUBLICATION',
    'MOULDING.', 'MOULDINGS.', 'DOORS.', 'THE TIMBER TRADES JOURNAL.',
    'ATLANTA', 'CARL XV', 'OSBORNE', 'PERSIAN MONARCH', 'HIGGS', 'G. E. ARNOLD',

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


def normalize_header_token(text: Optional[str]) -> str:
    """Normalize a candidate header token for skip-list comparison."""
    if not text:
        return ''
    normalized = text.upper().replace('—', ' ').replace('–', ' ').replace('-', ' ')
    normalized = re.sub(r'[^A-Z0-9& ]+', '', normalized)
    return ' '.join(normalized.split())


SKIP_HEADER_TOKENS = {normalize_header_token(token) for token in SKIP_HEADERS}


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

    def __init__(self, require_destination: bool = False):
        # Ship record patterns
        # Normalize dash separators across OCR variants: em dash, en dash, hyphen
        self.dash_sep = r"\s*[—–-]\s*"
        # Lookahead used to detect the start of another ship entry within the same line.
        # Matches delimiters (comma/semicolon/period) followed by an optional numeric index and a ship
        # name that eventually hits a dash or @ sign. This prevents one match from swallowing
        # subsequent ships when OCR failed to insert newlines.
        base_name_class_dash = r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ\(\)\.\'&\s-]{0,40}[—–-]"
        base_name_class_at = r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ\(\)\.\'&\s-]{0,40}@"
        self.next_ship_lookahead = (
            rf'(?=(?:\s*[;,\.]\s*(?:\d+\s+)?(?:{base_name_class_dash}|{base_name_class_at}))'
            rf'|(?:\s+(?:\d+\s+)?(?:{base_name_class_dash}|{base_name_class_at}))|$)'
        )
        # Precision control: when True, only return records when a destination port
        # has been resolved from context (city/dock/port headers)
        self.require_destination = require_destination
        # Early @ format handles: "April 27. Ship @..." and "Sept. 11 Ship @..."
        # Fixed to handle abbreviations like "St. John, N.B." without truncation
        # Uses lookahead to stop at comma+em-dash or comma+digit
        name_chars = r"A-Za-zÀ-ÖØ-öø-ÿ"
        text_chars = r"A-Za-zÀ-ÖØ-öø-ÿ\s\.\&\'\-"
        origin_chars = r"A-Za-zÀ-ÖØ-öø-ÿ\s\.,\'\-&"

        self.early_at_pattern = re.compile(
            r'^(?:(?P<month>\w{3,9})\.?\s+(?P<day>\d{1,2})\.?\s+)?'
            rf'(?P<ship>[{text_chars}]+?)\s*'
            r'(?:\(s\))?\s*'
            r'@\s*'
            rf'(?P<origin>[{origin_chars}]+?)'
            r',?\s*(?=[—\d])'  # Optional comma, then lookahead for em-dash or digit
            r'(?P<cargo>.*?)'
            + self.next_ship_lookahead,
            re.IGNORECASE
        )

        self.standard_dash_pattern = re.compile(
            (
                r'^(?:(?P<month>\w{3,9})\.\s+)?(?P<day>\d{1,2})\s+'
                r'(?:\d+\s+)?'
                rf'(?P<ship>[{text_chars}]+?)\s*'
                r'(?:\(s\))?' + self.dash_sep +
                rf'(?P<origin>[{origin_chars}]+?)' + self.dash_sep +
                r'(?P<cargo>[^—–-]+?)' + self.dash_sep +
                r'(?P<merchant>.+?)'
                + self.next_ship_lookahead
            ),
            re.IGNORECASE
        )

        # Condensed dash format with date: "Dec. 24 Cleveland-Mobile-cargo-merchant" or "25 Patent-Sundswall-cargo-merchant"
        self.condensed_dash_pattern = re.compile(
            (
                r'^(?:(?P<month>\w{3,9})\.\s+)?'  # Optional month
                r'(?P<day>\d{1,2})\s+'  # Day (required in this pattern)
                rf'(?P<ship>[A-Z][{text_chars}]+?)\s*'
                r'(?:\(s\))?' + self.dash_sep +
                rf'(?P<origin>[{origin_chars}]+?)' + self.dash_sep +
                r'(?P<cargo>[^—–-]+?)' + self.dash_sep +
                r'(?P<merchant>.+?)'
                + self.next_ship_lookahead
            ),
            re.IGNORECASE
        )

        # Condensed dash format without date: "Ship-Origin-cargo-merchant" (fallback for records with no date)
        self.condensed_no_date_pattern = re.compile(
            (
                r'^(?:\d+\s+)?'  # Optional index number
                rf'(?P<ship>[A-Z][{text_chars}]+?)\s*'
                r'(?:\(s\))?' + self.dash_sep +
                rf'(?P<origin>[{origin_chars}]+?)' + self.dash_sep +
                r'(?P<cargo>[^—–-]+?)' + self.dash_sep +
                r'(?P<merchant>.+?)'
                + self.next_ship_lookahead
            ),
            re.IGNORECASE
        )

        # Context extraction patterns
        # Accept headers with or without trailing period (e.g., "LONDON" or "LONDON.")
        self.port_header_pattern = re.compile(r"^([A-Z\s&\.\'\(\)]+)\.?\s*$")

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
        # Search backwards through context for date headers or dates at start of lines
        for line in reversed(context_lines):
            line = line.strip()
            # Try standalone date header first (e.g., "April 16.")
            match = self.date_header_pattern.match(line)
            if match:
                return match.group('month'), int(match.group('day'))

            # Also try to extract date from beginning of ship record lines (e.g., "Dec. 24 Ship-Origin...")
            date_prefix = re.match(r'^(?P<month>\w{3,9})\.\s+(?P<day>\d{1,2})\s+', line, re.IGNORECASE)
            if date_prefix:
                return date_prefix.group('month'), int(date_prefix.group('day'))

        return None, None

    def parse_line_with_context(self, line: str, context_lines: List[str],
                               line_number: int = 0, year: int = None) -> List[ShipRecord]:
        """
        Parse a single line with awareness of preceding context.

        Args:
            line: Text line to parse
            context_lines: Previous 2-4 lines for context
            line_number: Line number in source file
            year: Publication year

        Returns:
            List of ShipRecord objects (may be empty if no matches)
        """
        original_line = line.strip()
        records: List[ShipRecord] = []

        # Skip empty lines and port headers
        if not original_line or self.port_header_pattern.match(original_line):
            return records

        fragment = original_line
        while fragment:
            fragment = fragment.lstrip(' ,;')
            if not fragment:
                break

            previous_fragment = None
            while fragment and fragment != previous_fragment:
                previous_fragment = fragment
                stripped_fragment = self._strip_aggregate_prefix(fragment)
                if stripped_fragment != fragment:
                    fragment = stripped_fragment.lstrip(' ,;')
                    continue
                break
            if not fragment:
                break

            match = None
            format_type = None

            # Try early @ format
            if '@' in fragment:
                match = self.early_at_pattern.match(fragment)
                if match:
                    format_type = RecordFormat.EARLY_AT

            # Try standard dash format (with date)
            if not match and re.match(r'^\w+\.\s+\d{1,2}\s+', fragment):
                match = self.standard_dash_pattern.match(fragment)
                if match:
                    format_type = RecordFormat.STANDARD_DASH

            # Try condensed dash format (with date)
            if not match and ('-' in fragment or '—' in fragment or '–' in fragment):
                match = self.condensed_dash_pattern.match(fragment)
                if match:
                    format_type = RecordFormat.CONDENSED

            # Try condensed dash format without date (fallback)
            if not match and ('-' in fragment or '—' in fragment or '–' in fragment):
                match = self.condensed_no_date_pattern.match(fragment)
                if match:
                    format_type = RecordFormat.CONDENSED

            if not match:
                break

            groups = match.groupdict()

            ship_name = groups.get('ship', '').strip()
            origin_port = groups.get('origin', '').strip()
            cargo = groups.get('cargo', '').strip()
            merchant = groups.get('merchant', '').strip() if 'merchant' in groups else None

            # Clean ship name: remove merchant names/terms from start
            # Iteratively remove patterns until no more matches
            ship_name_cleaned = ship_name
            for _ in range(3):  # Max 3 iterations to handle nested patterns
                before = ship_name_cleaned
                # Remove simple merchant terms
                ship_name_cleaned = re.sub(
                    r'^(?:Order|Ditto|Bond|Nil|Co\.|Ltd\.|&|and)\.?\s+',
                    '', ship_name_cleaned, flags=re.IGNORECASE
                ).strip()
                # Remove "Name & Name." or "Name & Co." patterns (with period at end)
                ship_name_cleaned = re.sub(
                    r'^(?:[A-Z][A-Za-z]*\.?\s*)+(?:&|and)\s+(?:[A-Z][A-Za-z]*\.?\s*)*[A-Z][A-Za-z]*\.\s+',
                    '', ship_name_cleaned
                ).strip()
                # Remove single "Name. " pattern
                ship_name_cleaned = re.sub(
                    r'^[A-Z][A-Za-z]+\.\s+',
                    '', ship_name_cleaned
                ).strip()
                if ship_name_cleaned == before:
                    break  # No more changes

            if ship_name_cleaned and len(ship_name_cleaned) > 0 and ship_name_cleaned[0].isupper():
                ship_name = ship_name_cleaned

            normalized_ship_name = normalize_header_token(ship_name)
            if normalized_ship_name and normalized_ship_name in SKIP_HEADER_TOKENS:
                fragment = fragment[match.end():]
                continue

            # Skip obvious advertisement headers and non-ship lines that slip through
            if ship_name and not any(ch.islower() for ch in ship_name):
                fragment = fragment[match.end():]
                continue

            if self._origin_is_commodity(origin_port):
                cargo = f"{origin_port} {cargo}".strip(' ,;')
                origin_port = None

            cargo, merchant, extra_fragment = self._split_order_chain(cargo, merchant)
            cargo = cargo.strip(' ,;') if cargo else cargo
            if merchant and not self._is_valid_merchant_value(merchant):
                merchant = None

            if merchant:
                cargo = f"{cargo}-{merchant}".strip() if cargo else merchant.strip()

            remainder_fragment = fragment[match.end():].strip()
            if extra_fragment:
                extra_fragment = extra_fragment.strip()
                if remainder_fragment:
                    remainder_fragment = f"{extra_fragment} {remainder_fragment}"
                else:
                    remainder_fragment = extra_fragment

            if remainder_fragment and not self._looks_like_new_ship(remainder_fragment):
                if cargo:
                    if remainder_fragment.startswith(';'):
                        cargo = f"{cargo}{remainder_fragment}"
                    elif remainder_fragment.startswith(','):
                        cargo = f"{cargo};{remainder_fragment[1:]}".strip()
                    else:
                        cargo = f"{cargo} {remainder_fragment}"
                else:
                    cargo = remainder_fragment
                remainder_fragment = ''

            # Fix encoding for origin port (double-encoded UTF-8)
            origin_port = fix_encoding(origin_port) if origin_port else origin_port

            # Extract date from line or context
            day = groups.get('day')
            month = groups.get('month')

            if not day or not month:
                context_month, context_day = self.extract_date_from_context(context_lines)
                if not month:
                    month = context_month
                if not day and context_day:
                    day = context_day

            destination_port = self.extract_port_from_context(context_lines)
            destination_port = fix_encoding(destination_port) if destination_port else destination_port

            is_steamship = '(s)' in fragment
            ship_name = ship_name.replace('(s)', '').strip()

            record = ShipRecord(
                raw_line=fragment,
                line_number=line_number,
                preceding_context=context_lines[-4:],
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
                confidence=1.0 if destination_port else 0.7
            )

            records.append(record)

            if remainder_fragment:
                fragment = remainder_fragment
                continue

            # Get remainder and strip leading delimiters
            remainder = fragment[match.end():].lstrip(' ,;.')
            if not remainder:
                break
            fragment = remainder
            # Continue looping to find more ships on the same line

        return records

    def _strip_aggregate_prefix(self, text: str) -> str:
        fragment = text.lstrip(' ,;')
        lowered = fragment.lower()

        if lowered.startswith('joinery-'):
            dash_idx = fragment.find('-')
            if dash_idx != -1:
                fragment = fragment[dash_idx + 1:].lstrip(' ,;')
                lowered = fragment.lower()

        if lowered.startswith('from '):
            dash_idx = fragment.find('-')
            if 0 < dash_idx < 60:
                fragment = fragment[dash_idx + 1:].lstrip(' ,;')
                lowered = fragment.lower()

        if lowered.startswith('ex '):
            fragment = fragment[3:].lstrip(' ,;')

        while fragment and not self._looks_like_new_ship(fragment):
            dash_idx = fragment.find('-')
            if dash_idx == -1:
                break
            fragment = fragment[dash_idx + 1:].lstrip(' ,;')

        if fragment.lower().startswith('order '):
            candidate = fragment.split(' ', 1)[1].lstrip(' ,;')
            if self._looks_like_new_ship(candidate):
                fragment = candidate

        return fragment

    def _is_valid_merchant_value(self, merchant: Optional[str]) -> bool:
        if not merchant:
            return False
        candidate = merchant.strip(' ,;')
        if not candidate:
            return False
        if candidate.lower() in {'order', 'to order', 'in bond', 'nil', 'ditto'}:
            return False
        if any(ch.isdigit() for ch in candidate):
            return False
        if any(delim in candidate for delim in {';', ':'}):
            return False
        normalized = normalize_header_token(candidate)
        if normalized in SKIP_HEADER_TOKENS:
            return False
        return any(ch.isalpha() for ch in candidate)

    def _origin_is_commodity(self, origin: Optional[str]) -> bool:
        if not origin:
            return False
        normalized_origin = normalize_header_token(origin)
        if normalized_origin and normalized_origin in SKIP_HEADER_TOKENS:
            return True
        return not any(ch.isalpha() and ch.isupper() for ch in origin)

    def _split_order_chain(
        self,
        cargo: Optional[str],
        merchant: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if not cargo:
            return cargo, merchant, None

        cargo_clean = cargo.strip(' ,;')
        if not cargo_clean:
            return cargo_clean, merchant, None

        remainder: Optional[str] = None
        order_match = re.search(
            r'\border\b\s+(?P<next>(?:\d+\s+)?[A-Z][A-Za-zÀ-ÖØ-öø-ÿ\.\'&\s\(\)-]{2,})$',
            cargo_clean,
            flags=re.IGNORECASE
        )

        if order_match:
            remainder_candidate = order_match.group('next').strip(' ,;')
            if remainder_candidate:
                normalized = normalize_header_token(remainder_candidate.split('-')[0])
                if normalized not in SKIP_HEADER_TOKENS and any(ch.isalpha() for ch in remainder_candidate):
                    cargo_clean = cargo_clean[:order_match.start()].strip(' ,;')
                    if not cargo_clean:
                        cargo_clean = 'Order'
                    remainder = remainder_candidate

        adjusted_merchant = merchant
        if remainder:
            merchant_tail = merchant.strip(' ,;') if merchant else ''
            if merchant_tail:
                remainder = f"{remainder}-{merchant_tail}"
                adjusted_merchant = None

        if adjusted_merchant and not self._is_valid_merchant_value(adjusted_merchant):
            adjusted_merchant = None

        return cargo_clean, adjusted_merchant, remainder

    def _looks_like_new_ship(self, text: str) -> bool:
        if not text:
            return False
        snippet = text.lstrip(' ,;')
        # Match both dash-format and @ format ships
        match = re.match(
            r'^(?:\d+\s+)?([A-Z][A-Za-zÀ-ÖØ-öø-ÿ\.\'&\s-]{1,60})(?:\(s\))?\s*(?:[—–-]|@)',
            snippet
        )
        if not match:
            return False
        candidate = match.group(1).strip()
        normalized = normalize_header_token(candidate)
        if normalized in SKIP_HEADER_TOKENS:
            return False
        return True

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
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
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
                        # ALSO set current_port - most ships list under city name directly
                        # If a dock subdivision follows, it will override this
                        self.current_port = port_candidate
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
                i += 1
                continue

            # Update persistent date context if we see a date header
            date_match = self.date_header_pattern.match(line_stripped)
            if date_match:
                self.current_month = date_match.group('month')
                self.current_day = int(date_match.group('day'))

            # Get preceding 2-4 lines for immediate context
            context_start = max(0, i - 4)
            context_lines = [lines[j].strip() for j in range(context_start, i)]

            # Try parsing current line
            records_from_line = self.parse_line_with_context(line, context_lines, i + 1, year)

            # If not matched, attempt joining with the next line (wrapped records)
            consumed_extra = 0
            if not records_from_line and (('—' in line or '–' in line or '-' in line) and i + 1 < n):
                next_line = lines[i + 1].strip()
                # Avoid joining if the next line is a clear header
                if not self.port_header_pattern.match(next_line):
                    joined = (line.strip() + ' ' + next_line).strip()
                    records_from_line = self.parse_line_with_context(joined, context_lines, i + 1, year)
                    if records_from_line:
                        consumed_extra = 1

            # If still not matched, try joining two lines ahead
            if not records_from_line and (('—' in line or '–' in line or '-' in line) and i + 2 < n):
                next1 = lines[i + 1].strip()
                next2 = lines[i + 2].strip()
                if not self.port_header_pattern.match(next1) and not self.port_header_pattern.match(next2):
                    joined = (line.strip() + ' ' + next1 + ' ' + next2).strip()
                    rec2 = self.parse_line_with_context(joined, context_lines, i + 1, year)
                    if rec2:
                        records_from_line = rec2
                        consumed_extra = 2
            if records_from_line:
                # Apply persistent context if not found in immediate context
                for record in records_from_line:
                    if not record.destination_port and self.current_port:
                        record.destination_port = self.current_port
                        record.confidence = 0.9  # Slightly lower than immediate context

                    if not record.month and self.current_month:
                        record.month = self.current_month
                    if not record.day and self.current_day:
                        record.day = self.current_day

                    if record.month:
                        self.current_month = record.month
                    if record.day:
                        self.current_day = record.day

                    record.publication_year = pub_year
                    record.publication_month = pub_month
                    record.publication_day = pub_day

                    if self.require_destination and not record.destination_port:
                        continue

                    records.append(record)

            # Advance index by 1 + any consumed extra lines
            i += 1 + consumed_extra

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
