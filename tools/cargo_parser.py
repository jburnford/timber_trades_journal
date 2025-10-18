#!/usr/bin/env python3
"""
Parse cargo strings into structured commodity records.
Extracts quantity, unit, commodity, and merchant from cargo field.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CargoItem:
    """A single cargo item with quantity, unit, commodity, and merchant."""
    quantity: Optional[str] = None
    unit: Optional[str] = None
    commodity: str = ""
    merchant: Optional[str] = None
    raw_text: str = ""


class CargoParser:
    """Parse cargo strings into structured items."""

    def __init__(self):
        # Pattern: QUANTITY UNIT COMMODITY, MERCHANT
        # More comprehensive pattern to handle various formats
        # Examples: "1,300 staves, Nickols & Co." or "46,012 boards" or "102 bgs. wood pulp"
        self.item_with_merchant_pattern = re.compile(
            r'(\d+[,\d]*)\s+'                    # Quantity (with optional commas)
            r'([a-z]{1,6}\.?)\s+'                # Unit (1-6 chars, optional period)
            r'([a-z\s\-]+?)'                     # Commodity
            r'(?:,\s*([A-Z][A-Za-z\s\.\&\'\-]+?))?'  # Optional merchant (starts with capital)
            r'(?=;|$)',                          # End at semicolon or end of string
            re.IGNORECASE
        )

        # Pattern for: QUANTITY UNIT COMMODITY (unit is explicit abbrev like "pcs.")
        self.item_with_unit_pattern = re.compile(
            r'(\d+[,\d]*)\s+'           # Quantity
            r'([a-z]{1,6}\.)\s+'        # Unit (must have period - pcs., bdls., etc.)
            r'([a-z\s\-&]+)',           # Commodity
            re.IGNORECASE
        )

        # Pattern for: QUANTITY COMMODITY (no explicit unit - commodity is the unit)
        # Examples: "1,300 staves", "46,012 boards"
        self.item_no_unit_pattern = re.compile(
            r'(\d+[,\d]*)\s+'                      # Quantity
            r'([a-z][a-z\s\-&]{2,25}?)'            # Commodity (at least 3 chars)
            r'(?=,|;|\.|\s+[A-Z]|$)',              # Lookahead: comma, semicolon, period, capital letter, or end
            re.IGNORECASE
        )

    def parse_cargo_string(self, cargo: str) -> List[CargoItem]:
        """
        Parse cargo string into structured items.

        Args:
            cargo: Raw cargo string from record

        Returns:
            List of CargoItem objects
        """
        if not cargo or len(cargo) < 3:
            return []

        items = []

        # Clean up leading em-dashes and extra spaces
        cargo = cargo.lstrip('—-').strip()

        # Split on semicolons (separate cargo items)
        segments = re.split(r';', cargo)

        for segment in segments:
            segment = segment.strip()
            if not segment or len(segment) < 5:
                continue

            # Try pattern with explicit unit first (e.g., "102 bgs. wood pulp")
            matches_with_unit = self.item_with_unit_pattern.findall(segment)

            # Try pattern without unit (e.g., "1,300 staves")
            matches_no_unit = self.item_no_unit_pattern.findall(segment)

            all_matches = []

            # Process matches with units
            for match in matches_with_unit:
                all_matches.append((match[0], match[1], match[2]))

            # Process matches without units
            for match in matches_no_unit:
                # Check if this match overlaps with a unit match (avoid duplicates)
                quantity = match[0]
                commodity = match[1]
                overlap = False
                for um in matches_with_unit:
                    if quantity in um[0]:  # Same quantity
                        overlap = True
                        break
                if not overlap:
                    all_matches.append((quantity, None, commodity))

            if all_matches:
                # Extract merchant once per segment
                # Merchant appears after commodity, before semicolon or end
                # Pattern: after last commodity, comma, then capitalized name
                merchant = None

                # More careful merchant extraction - look after the last number/commodity pair
                # Merchant pattern: comma followed by capital letter name (including periods and &)
                merchant_match = re.search(
                    r',\s*([A-Z][A-Za-z\s\.\&\'\-]+?)(?:;|$)',
                    segment
                )
                if merchant_match:
                    merchant_candidate = merchant_match.group(1).strip()
                    # Remove trailing period if present
                    merchant_candidate = merchant_candidate.rstrip('.')
                    # Filter out commodity words and common placeholders
                    if not any(word in merchant_candidate.lower() for word in ['order', 'nil', 'ditto']):
                        # Additional check: merchant should not be just commodity words
                        commodity_words = ['deals', 'timber', 'boards', 'staves', 'battens', 'planks', 'logs']
                        if not all(word.lower() in commodity_words for word in merchant_candidate.split()):
                            merchant = merchant_candidate

                for match in all_matches:
                    quantity = match[0].replace(',', '')  # Remove commas from numbers
                    unit = match[1].lower().rstrip('.') if match[1] else None
                    commodity = match[2].strip().lower()

                    items.append(CargoItem(
                        quantity=quantity,
                        unit=unit,
                        commodity=commodity,
                        merchant=merchant,
                        raw_text=segment[:100]  # Truncate for storage
                    ))
            else:
                # No quantity found - might be descriptive text
                # Look for commodity keywords
                commodity_keywords = [
                    'deals', 'timber', 'boards', 'battens', 'staves', 'mahogany',
                    'cedar', 'oak', 'pine', 'firewood', 'laths', 'planks'
                ]

                found_commodity = None
                for keyword in commodity_keywords:
                    if keyword in segment.lower():
                        found_commodity = keyword
                        break

                if found_commodity:
                    items.append(CargoItem(
                        quantity=None,
                        unit=None,
                        commodity=found_commodity,
                        merchant=None,
                        raw_text=segment[:100]
                    ))

        return items

    def extract_commodity_types(self, cargo: str) -> List[str]:
        """
        Extract just the commodity types (simplified).

        Args:
            cargo: Raw cargo string

        Returns:
            List of commodity names
        """
        items = self.parse_cargo_string(cargo)
        return [item.commodity for item in items if item.commodity]


def main():
    """Test the cargo parser."""
    parser = CargoParser()

    # Real test cases from our data
    test_cases = [
        "—1,300 staves, Nickols & Colven; 41,500 staves, H. & R. Fowler; 9,173 staves, Oppenheimer & Co.",
        "—102 bgs. wood pulp, J. Spicer & Co.; 1,669 planks, J. Neck & Sons; 8,047 boards, G. E. Arnold",
        "—68 logs wood, 6 logs mahogany, 172 logs rosewood, 104 doz. deals, Order.",
        "—115 pcs. timber, Order.",
        "—46,012 boards, 1,238 bdls. laths, Tagart & Co.",
        "deals and battens",
        "570 logs mahogany and cedar",
    ]

    print("=" * 80)
    print("CARGO PARSER TEST (Real Data)")
    print("=" * 80)

    for i, cargo in enumerate(test_cases, 1):
        print(f"\n{i}. Input: {cargo[:80]}...")
        print("-" * 80)
        items = parser.parse_cargo_string(cargo)
        print(f"   Parsed {len(items)} items:")
        for j, item in enumerate(items, 1):
            print(f"   {j}. Qty: {item.quantity or 'N/A':>6}  "
                  f"Unit: {item.unit or 'N/A':<8}  "
                  f"Commodity: {item.commodity[:25]:<25}  "
                  f"Merchant: {(item.merchant or 'N/A')[:20]}")


if __name__ == '__main__':
    main()
