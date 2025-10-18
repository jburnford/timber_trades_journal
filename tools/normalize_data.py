#!/usr/bin/env python3
"""
Normalize TTJ data: ports, commodities, and merchants.
Uses fuzzy matching and reference dictionaries.
"""

import csv
import json
from pathlib import Path
from typing import Dict, Set, Optional
from difflib import SequenceMatcher
from collections import Counter


class TTJNormalizer:
    """Normalize TTJ dataset using reference dictionaries and fuzzy matching."""

    def __init__(self, reference_dir: Path):
        """Load reference dictionaries."""
        self.reference_dir = reference_dir

        # Load canonical ports
        with open(reference_dir / 'canonical_ports.json', 'r') as f:
            self.canonical_ports = json.load(f)

        # Load canonical commodities
        with open(reference_dir / 'commodities.json', 'r') as f:
            self.canonical_commodities = json.load(f)

        # Build normalization caches
        self.origin_port_map: Dict[str, str] = {}
        self.destination_port_map: Dict[str, str] = {}
        self.commodity_map: Dict[str, str] = {}

        print(f"Loaded {len(self.canonical_ports)} canonical ports")
        print(f"Loaded {len(self.canonical_commodities)} canonical commodities")

    def similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0-1)."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def normalize_port(self, port: str, is_destination: bool = False) -> str:
        """
        Normalize a port name using fuzzy matching.

        Args:
            port: Raw port name
            is_destination: If True, use destination port rules

        Returns:
            Normalized port name
        """
        if not port or not port.strip():
            return ""

        port = port.strip()

        # Check cache
        cache = self.destination_port_map if is_destination else self.origin_port_map
        if port in cache:
            return cache[port]

        # Exact match (case-insensitive)
        for canonical in self.canonical_ports:
            if port.lower() == canonical.lower():
                cache[port] = canonical
                return canonical

        # Common abbreviations and OCR errors
        port_abbrev_map = {
            "F'stad": "Fredrikstad",
            "Fred'stad": "Fredrikstad",
            "G'burg": "Gothenburg",
            "G'berg": "Gothenburg",
            "Christ'a": "Christiania",
            "Christ": "Christiania",
            "Cronst": "Cronstadt",
            "St. John, N.B.": "St. John",
            "St. John's, N.B.": "St. John",
            "St. John, N. B.": "St. John",
            "St. Johns": "St. John",
            "Dantzig": "Danzig",
            "Dantzic": "Danzig",
            "Danzic": "Danzig",
            "Nykoping": "Nyköping",
            "Bjorneborg": "Björneborg",
            "Gefle": "Gävle",
            "Soderhamn": "Söderhamn",
        }

        # Check abbreviation map
        for abbrev, canonical in port_abbrev_map.items():
            if port.lower() == abbrev.lower():
                cache[port] = canonical
                return canonical

        # Handle "Fredrikstad" variants
        if "fredrik" in port.lower() or "fredrick" in port.lower() or "frederik" in port.lower():
            if "voern" in port.lower() or "voarn" in port.lower() or "vaern" in port.lower():
                cache[port] = "Fredriksvoern"
                return "Fredriksvoern"
            elif "hamn" in port.lower() or "ham" in port.lower():
                cache[port] = "Fredrikshamn"
                return "Fredrikshamn"
            elif "hald" in port.lower() or "hall" in port.lower():
                cache[port] = "Fredrikshald"
                return "Fredrikshald"
            else:
                cache[port] = "Fredrikstad"
                return "Fredrikstad"

        # Handle "Christiania" variants
        if "christian" in port.lower():
            if "sand" in port.lower() or "sann" in port.lower():
                cache[port] = "Christiansand"
                return "Christiansand"
            elif "stad" in port.lower() or "stat" in port.lower():
                cache[port] = "Christianstad"
                return "Christianstad"
            elif "sund" in port.lower():
                cache[port] = "Christiansund"
                return "Christiansund"
            else:
                cache[port] = "Christiania"
                return "Christiania"

        # Fuzzy matching (threshold 0.85)
        best_match = None
        best_score = 0.85

        for canonical in self.canonical_ports:
            score = self.similarity_score(port, canonical)
            if score > best_score:
                best_score = score
                best_match = canonical

        if best_match:
            cache[port] = best_match
            return best_match

        # No match found - return original
        cache[port] = port
        return port

    def normalize_commodity(self, commodity: str) -> str:
        """
        Normalize a commodity name.

        Args:
            commodity: Raw commodity string

        Returns:
            Normalized commodity name
        """
        if not commodity or not commodity.strip():
            return ""

        commodity = commodity.strip().lower()

        # Check cache
        if commodity in self.commodity_map:
            return self.commodity_map[commodity]

        # Exact match
        if commodity in self.canonical_commodities:
            self.commodity_map[commodity] = commodity
            return commodity

        # Common normalizations
        commodity_rules = {
            # Deal variants
            r"^deals?$": "deals",
            r"^deal$": "deals",
            r"sawn fir deals?": "deals",
            r"white deals?": "deals",
            r"yellow deals?": "deals",
            r"bright.*deals?": "deals",
            r"spruce deals?": "deals",
            r"pine deals?": "deals",

            # Timber variants
            r"^timbers?$": "timber",
            r"oak timbers?": "oak timber",
            r"pine timbers?": "pine timber",
            r"birch timbers?": "birch timber",
            r"white pine timbers?": "white pine timber",

            # Board variants
            r"^boards?$": "boards",
            r"^boars$": "boards",  # OCR error
            r"flooring boards?": "flooring boards",
            r"weather boards?": "weather boards",
            r"match boards?": "match boards",

            # Stave variants
            r"^staves?$": "staves",
            r"oak staves?": "oak staves",
            r"pipe staves?": "pipe staves",
            r"fir staves?": "fir staves",

            # Batten variants
            r"^battens?$": "battens",
            r"slating battens?": "slating battens",

            # Log variants
            r"^logs?$": "logs",
            r"mahogany logs?": "logs mahogany",
            r"oak logs?": "logs oak",
            r"walnut logs?": "logs walnut",
            r"cedar logs?": "logs cedar",

            # Plank variants
            r"^planks?$": "planks",
            r"oak planks?": "oak planks",
            r"teak planks?": "teak planks",
        }

        # Apply pattern-based rules
        import re
        for pattern, normalized in commodity_rules.items():
            if re.search(pattern, commodity):
                self.commodity_map[commodity] = normalized
                return normalized

        # Fuzzy matching for common commodities (threshold 0.90)
        best_match = None
        best_score = 0.90

        # Only match against high-frequency commodities (>20 occurrences)
        high_freq_commodities = [c for c, count in self.canonical_commodities.items() if count > 20]

        for canonical in high_freq_commodities:
            score = self.similarity_score(commodity, canonical)
            if score > best_score:
                best_score = score
                best_match = canonical

        if best_match:
            self.commodity_map[commodity] = best_match
            return best_match

        # No match - return original
        self.commodity_map[commodity] = commodity
        return commodity

    def normalize_merchant(self, merchant: str) -> str:
        """
        Normalize merchant names.

        Args:
            merchant: Raw merchant string

        Returns:
            Normalized merchant name
        """
        if not merchant or not merchant.strip():
            return ""

        merchant = merchant.strip()

        # Common placeholders
        if merchant.lower() in ['order', 'nil', 'ditto', '---']:
            return ""

        # Remove trailing periods
        merchant = merchant.rstrip('.')

        # Common abbreviations
        merchant = merchant.replace('&', 'and')
        merchant = merchant.replace(' Co.', ' Company')
        merchant = merchant.replace(' Bros.', ' Brothers')

        return merchant

    def generate_normalized_csv(self, input_dir: Path, output_dir: Path):
        """
        Generate normalized CSV files.

        Args:
            input_dir: Directory with original CSVs
            output_dir: Directory for normalized CSVs
        """
        output_dir.mkdir(exist_ok=True)
        csv.field_size_limit(1000000)

        stats = {
            'total_ships': 0,
            'origin_ports_normalized': 0,
            'destination_ports_normalized': 0,
            'commodities_normalized': 0,
            'merchants_normalized': 0
        }

        # Normalize shipments file
        print("\nNormalizing shipments...")
        shipments_in = input_dir / 'ttj_shipments.csv'
        shipments_out = output_dir / 'ttj_shipments_normalized.csv'

        with open(shipments_in, 'r', encoding='utf-8') as f_in, \
             open(shipments_out, 'w', newline='', encoding='utf-8') as f_out:

            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                stats['total_ships'] += 1

                # Normalize origin port
                original_origin = row['origin_port']
                row['origin_port'] = self.normalize_port(original_origin, is_destination=False)
                if row['origin_port'] != original_origin:
                    stats['origin_ports_normalized'] += 1

                # Normalize destination port
                original_dest = row['destination_port']
                row['destination_port'] = self.normalize_port(original_dest, is_destination=True)
                if row['destination_port'] != original_dest:
                    stats['destination_ports_normalized'] += 1

                # Normalize merchant
                original_merchant = row['merchant']
                row['merchant'] = self.normalize_merchant(original_merchant)
                if row['merchant'] != original_merchant:
                    stats['merchants_normalized'] += 1

                writer.writerow(row)

                if stats['total_ships'] % 5000 == 0:
                    print(f"  Processed {stats['total_ships']:,} ships...")

        # Normalize cargo details file
        print("\nNormalizing cargo details...")
        cargo_in = input_dir / 'ttj_cargo_details.csv'
        cargo_out = output_dir / 'ttj_cargo_details_normalized.csv'

        total_cargo = 0
        with open(cargo_in, 'r', encoding='utf-8') as f_in, \
             open(cargo_out, 'w', newline='', encoding='utf-8') as f_out:

            reader = csv.DictReader(f_in)
            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                total_cargo += 1

                # Normalize commodity
                original_commodity = row['commodity']
                row['commodity'] = self.normalize_commodity(original_commodity)
                if row['commodity'] != original_commodity:
                    stats['commodities_normalized'] += 1

                # Normalize merchant
                original_merchant = row['merchant']
                row['merchant'] = self.normalize_merchant(original_merchant)

                writer.writerow(row)

                if total_cargo % 10000 == 0:
                    print(f"  Processed {total_cargo:,} cargo items...")

        # Print statistics
        print("\n" + "=" * 80)
        print("NORMALIZATION COMPLETE")
        print("=" * 80)
        print(f"Ships processed: {stats['total_ships']:,}")
        print(f"  Origin ports normalized: {stats['origin_ports_normalized']:,} ({100*stats['origin_ports_normalized']/stats['total_ships']:.1f}%)")
        print(f"  Destination ports normalized: {stats['destination_ports_normalized']:,} ({100*stats['destination_ports_normalized']/stats['total_ships']:.1f}%)")
        print(f"  Merchants normalized: {stats['merchants_normalized']:,}")
        print(f"\nCargo items processed: {total_cargo:,}")
        print(f"  Commodities normalized: {stats['commodities_normalized']:,} ({100*stats['commodities_normalized']/total_cargo:.1f}%)")
        print(f"\nOutput files:")
        print(f"  {shipments_out}")
        print(f"  {cargo_out}")

        # Save normalization mappings for review
        mappings_file = output_dir / 'normalization_mappings.json'
        mappings = {
            'origin_ports': self.origin_port_map,
            'destination_ports': self.destination_port_map,
            'commodities': dict(list(self.commodity_map.items())[:500])  # Sample
        }
        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
        print(f"  {mappings_file}")
        print("=" * 80)

        # Analyze results
        self._print_normalization_analysis(output_dir)

    def _print_normalization_analysis(self, output_dir: Path):
        """Print analysis of normalized data."""
        print("\n" + "=" * 80)
        print("NORMALIZED DATA ANALYSIS")
        print("=" * 80)

        # Count unique values after normalization
        origin_ports = Counter()
        destination_ports = Counter()
        commodities = Counter()

        with open(output_dir / 'ttj_shipments_normalized.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['origin_port']:
                    origin_ports[row['origin_port']] += 1
                if row['destination_port']:
                    destination_ports[row['destination_port']] += 1

        with open(output_dir / 'ttj_cargo_details_normalized.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['commodity']:
                    commodities[row['commodity']] += 1

        print(f"Unique origin ports: {len(origin_ports)} (was 1,755)")
        print(f"Unique destination ports: {len(destination_ports)} (was 282)")
        print(f"Unique commodities: {len(commodities)} (was 1,321)")

        print("\nTop 20 origin ports after normalization:")
        for port, count in origin_ports.most_common(20):
            print(f"  {port}: {count:,}")

        print("\nTop 20 commodities after normalization:")
        for comm, count in commodities.most_common(20):
            print(f"  {comm}: {count:,}")

        print("=" * 80)


def main():
    reference_dir = Path("/home/jic823/TTJ Forest of Numbers/reference_data")
    input_dir = Path("/home/jic823/TTJ Forest of Numbers/final_output")
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/final_output/normalized")

    print("=" * 80)
    print("TTJ DATA NORMALIZATION")
    print("=" * 80)
    print(f"Reference data: {reference_dir}")
    print(f"Input data: {input_dir}")
    print(f"Output directory: {output_dir}")

    normalizer = TTJNormalizer(reference_dir)
    normalizer.generate_normalized_csv(input_dir, output_dir)


if __name__ == '__main__':
    main()
