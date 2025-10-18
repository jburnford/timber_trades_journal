#!/usr/bin/env python3
"""
TTJ Format Detector - Identifies format variants and structural elements.
Handles multiple format types from 1874-1899.
"""

import re
from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


class FormatType(Enum):
    """Format variants identified across years."""
    EARLY_AT_DELIMITER = "early_at"      # 1874-1878: Ship @ Origin,—cargo
    TRANSITION = "transition"             # 1879-1880: Mixed formats
    STANDARD_DASH = "standard_dash"       # 1881-1890: Date Ship-Origin-Cargo-Merchant
    LATE_DOCK_SUBS = "late_dock"          # 1885+: With dock subdivisions
    UNKNOWN = "unknown"


@dataclass
class ContentBlock:
    """A block of content with classification."""
    text: str
    block_type: str  # 'import_list', 'editorial', 'table', 'other'
    confidence: float
    start_line: int
    end_line: int


class FormatDetector:
    """Detect format type and structural elements in TTJ OCR text."""

    def __init__(self):
        # Known port names (major ones)
        self.major_ports = {
            'LONDON', 'LIVERPOOL', 'HULL', 'GRIMSBY', 'BRISTOL', 'CARDIFF',
            'LEITH', 'GLASGOW', 'NEWCASTLE', 'SUNDERLAND', 'TYNE', 'HARTLEPOOL',
            'MANCHESTER', 'BIRKENHEAD', 'NEWPORT', 'SWANSEA', 'BELFAST',
            'DUBLIN', 'DUNDEE', 'ABERDEEN', 'SOUTHAMPTON', 'PLYMOUTH',
            'MIDDLESBROUGH', 'YARMOUTH', 'WEYMOUTH', 'EXETER'
        }

        # London dock subdivisions (late format)
        self.london_docks = {
            'SURREY COMMERCIAL DOCKS', 'MILLWALL DOCKS', 'ROYAL ALBERT DOCKS',
            'VICTORIA DOCKS', 'TILBURY DOCKS', 'WEST INDIA DOCKS',
            'REGENT\'S CANAL DOCK', 'SHADWELL BASIN', 'BREWER\'S QUAY',
            'BURT\'S WHARF', 'GALLEON\'S BUOYS', 'HANOVER HOLE',
            'PRINCE REGENT\'S WHARF', 'OTHER DOCKS AND WHARVES'
        }

    def detect_format(self, text: str, year: Optional[int] = None) -> FormatType:
        """
        Detect the format type of the document.

        Args:
            text: Full OCR text
            year: Optional year hint from filename

        Returns:
            FormatType enum value
        """
        # Year-based heuristic (if available)
        if year:
            if year <= 1878:
                return FormatType.EARLY_AT_DELIMITER
            elif year <= 1880:
                return FormatType.TRANSITION
            elif year <= 1884:
                return FormatType.STANDARD_DASH
            else:
                return FormatType.LATE_DOCK_SUBS

        # Content-based detection
        signals = self._detect_format_signals(text)

        # Decision logic
        if signals['uses_at_delimiter'] and signals['at_count'] > signals['dash_count']:
            return FormatType.EARLY_AT_DELIMITER

        if signals['has_dock_subdivisions']:
            return FormatType.LATE_DOCK_SUBS

        if signals['uses_dash_delimiter']:
            return FormatType.STANDARD_DASH

        if signals['at_count'] > 0 and signals['dash_count'] > 0:
            return FormatType.TRANSITION

        return FormatType.UNKNOWN

    def _detect_format_signals(self, text: str) -> Dict:
        """Detect format-specific signals."""
        signals = {}

        # Delimiter usage
        signals['uses_at_delimiter'] = '@' in text
        signals['uses_dash_delimiter'] = bool(re.search(r'-[A-Z]', text))

        # Count occurrences
        signals['at_count'] = text.count('@')
        signals['dash_count'] = len(re.findall(r'\s+-\s+', text))

        # Dock subdivisions
        signals['has_dock_subdivisions'] = any(
            dock in text for dock in self.london_docks
        )

        # Date patterns
        signals['has_month_day_prefix'] = bool(
            re.search(r'^\w{3,4}\.\s+\d{1,2}\s+', text, re.M)
        )

        return signals

    def extract_import_sections(self, text: str) -> List[ContentBlock]:
        """
        Extract import list sections from mixed content.

        Args:
            text: Full OCR text

        Returns:
            List of ContentBlock objects for import lists
        """
        blocks = []
        lines = text.split('\n')

        in_import_section = False
        current_block_lines = []
        current_start = 0
        consecutive_non_import = 0  # Track consecutive non-import lines

        for i, line in enumerate(lines):
            # Check for import section start
            if self._is_import_header(line):
                if current_block_lines and in_import_section:
                    # Save previous block
                    blocks.append(self._create_content_block(
                        current_block_lines, current_start, i - 1
                    ))
                current_block_lines = [line]
                current_start = i
                in_import_section = True
                consecutive_non_import = 0
                continue

            # Check for import section end
            if in_import_section and self._is_section_end(line):
                if current_block_lines and len(current_block_lines) > 5:
                    blocks.append(self._create_content_block(
                        current_block_lines, current_start, i - 1
                    ))
                current_block_lines = []
                in_import_section = False
                consecutive_non_import = 0
                continue

            # Check if line looks like import record
            if in_import_section:
                if self._is_import_record(line) or self._is_port_header(line):
                    current_block_lines.append(line)
                    consecutive_non_import = 0
                elif not line.strip():  # Allow blank lines
                    current_block_lines.append(line)
                    consecutive_non_import = 0
                else:
                    # Track consecutive non-import lines
                    consecutive_non_import += 1
                    if consecutive_non_import <= 3:  # Allow a few non-import lines
                        current_block_lines.append(line)
                    else:
                        # End of section - too many non-import lines
                        if len(current_block_lines) > 5:
                            blocks.append(self._create_content_block(
                                current_block_lines, current_start, i - 3
                            ))
                        current_block_lines = []
                        in_import_section = False
                        consecutive_non_import = 0

        # Save final block
        if current_block_lines and in_import_section and len(current_block_lines) > 5:
            blocks.append(self._create_content_block(
                current_block_lines, current_start, len(lines) - 1
            ))

        return blocks

    def _is_import_header(self, line: str) -> bool:
        """Check if line is an import section header."""
        line = line.strip()
        patterns = [
            r'^Imports? of Timber',
            r'^IMPORTS\.?\s*$',
            r'^Timber Imports'
        ]
        return any(re.search(p, line, re.I) for p in patterns)

    def _is_port_header(self, line: str) -> bool:
        """Check if line is a port name header."""
        line = line.strip()

        # All caps ending with period
        if not re.match(r'^[A-Z\s&\.\'\(\)]+\.\s*$', line):
            return False

        # Remove trailing period
        port_name = line.rstrip('.').strip()

        # Check against known ports
        if port_name in self.major_ports:
            return True

        # Check for London dock subdivisions
        if port_name in self.london_docks:
            return True

        # Allow other all-caps patterns (might be smaller ports)
        return len(port_name) > 3

    def _is_import_record(self, line: str) -> bool:
        """Check if line looks like a ship import record."""
        line = line.strip()

        if not line or len(line) < 10:
            return False

        # Pattern 1: Date Ship @ Origin
        if '@' in line:
            return True

        # Pattern 2: Date Ship-Origin-Cargo-Merchant
        if re.match(r'^(\w+\.\s+)?\d{1,2}\s+\w+.*-.*-', line):
            return True

        # Pattern 3: Ship-Origin-Cargo-Merchant (no date)
        if re.match(r'^\w+[\s\(].*-.*-.*-', line):
            return True

        # Pattern 4: Continuation line (starts with cargo/merchant)
        if re.match(r'^\d{1,5}\s+(pcs\.|lds\.|deals|timber|boards)', line):
            return True

        return False

    def _is_section_end(self, line: str) -> bool:
        """Check if line marks end of import section."""
        line = line.strip()

        # New article/section headers
        editorial_markers = [
            r'^THE\s+\w+\s+TRADE',
            r'^\(From\s+our\s+own\s+Correspondent',
            r'^[A-Z\s]{10,}\.$',  # Long all-caps header
            r'^MARKET\s+REPORTS',
            r'^PRICES\s+CURRENT'
        ]

        return any(re.search(p, line, re.I) for p in editorial_markers)

    def _create_content_block(self, lines: List[str], start: int, end: int) -> ContentBlock:
        """Create a ContentBlock from lines."""
        text = '\n'.join(lines)

        # Calculate confidence based on import record density
        import_lines = sum(1 for line in lines if self._is_import_record(line))
        total_lines = len([l for l in lines if l.strip()])

        confidence = import_lines / max(1, total_lines)

        return ContentBlock(
            text=text,
            block_type='import_list',
            confidence=confidence,
            start_line=start,
            end_line=end
        )

    def extract_port_sections(self, text: str) -> List[Dict]:
        """
        Extract port-specific sections from import list.

        Args:
            text: Import section text

        Returns:
            List of dicts with 'port', 'text', 'start_line'
        """
        sections = []
        lines = text.split('\n')

        current_port = None
        current_text = []
        current_start = 0

        for i, line in enumerate(lines):
            if self._is_port_header(line):
                # Save previous section
                if current_port:
                    sections.append({
                        'port': current_port,
                        'text': '\n'.join(current_text),
                        'start_line': current_start
                    })

                # Start new section
                current_port = line.strip().rstrip('.')
                current_text = []
                current_start = i + 1
            elif current_port:
                current_text.append(line)

        # Save final section
        if current_port:
            sections.append({
                'port': current_port,
                'text': '\n'.join(current_text),
                'start_line': current_start
            })

        return sections


def main():
    """Test the format detector."""
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python ttj_format_detector.py <ocr_file.txt>")
        sys.exit(1)

    test_file = Path(sys.argv[1])
    with open(test_file, 'r', encoding='utf-8') as f:
        text = f.read()

    detector = FormatDetector()

    # Detect format
    format_type = detector.detect_format(text)
    print(f"Format detected: {format_type.value}")
    print()

    # Extract import sections
    blocks = detector.extract_import_sections(text)
    print(f"Found {len(blocks)} import blocks:")
    for i, block in enumerate(blocks, 1):
        print(f"  Block {i}: lines {block.start_line}-{block.end_line}, "
              f"confidence {block.confidence:.2f}")
    print()

    # Extract port sections from first block
    if blocks:
        port_sections = detector.extract_port_sections(blocks[0].text)
        print(f"Found {len(port_sections)} ports in first block:")
        for section in port_sections[:10]:  # Show first 10
            line_count = section['text'].count('\n') + 1
            print(f"  {section['port']}: {line_count} lines")


if __name__ == '__main__':
    main()
