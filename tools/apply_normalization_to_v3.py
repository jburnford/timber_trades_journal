#!/usr/bin/env python3
"""
Apply port normalization to v3 database with LLM-parsed 1874-1875 records.
Adds normalized columns while preserving raw port columns.
"""

import json
import csv
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, Set, Tuple, Optional
from collections import Counter


class PortNormalizer:
    """Enhanced port normalizer that uses both completed mappings and canonical lists."""

    def __init__(self, canonical_origin: Set[str], canonical_dest: Set[str],
                 completed_mappings: Dict[str, Dict[str, str]]):
        self.canonical_origin = canonical_origin
        self.canonical_dest = canonical_dest
        self.completed_mappings = completed_mappings  # {port_type: {original_port: normalized_port}}

        # Known variant mappings (comprehensive list from earlier analysis)
        self.origin_variant_map = {
            # Scandinavian ports
            "Cronstadt": "Kronstadt",
            "Cronstad": "Kronstadt",
            "G'burg": "Gothenburg",
            "G'berg": "Gothenburg",
            "F'stad": "Fredrikstad",
            "Fred'stad": "Fredrikstad",
            "Fredrikstadt": "Fredrikstad",
            "Frederikstad": "Fredrikstad",
            "Frederickstad": "Fredrikstad",
            "Fredrikshald": "Halden",
            "Frederikshald": "Halden",
            "Frederickshald": "Halden",
            "Hernosand": "Harnosand",
            "Hudiksvall": "Hudikswall",

            # Baltic ports
            "Dantzic": "Danzig",
            "Dantzig": "Danzig",
            "Danzic": "Danzig",
            "Windau": "Ventspils",
            "Libau": "Liepāja",
            "Wyburg": "Vyborg",

            # North American ports
            "St. John, N.B.": "St. John",
            "St. John's, N.B.": "St. John",
            "St. John, N. B.": "St. John",
            "St. Johns": "St. John",
            "Halifax, N.S.": "Halifax",
            "Charlotte Town": "Charlottetown",

            # Other common variants
            "Krageroe": "Kragero",
            "Finklippan": "Finnklippan",
            "Swartvik": "Svartvik",
            "Swartwick": "Svartvik",
            "Swartwik": "Svartvik",
            "Westervik": "Västervik",
            "Westerwik": "Västervik",
            "Uddewalla": "Uddevalla",
            "Halmstadt": "Halmstad",
            "Jacobstad": "Jakobstad",
            "Carlshamn": "Karlshamn",
            "Bergqvara": "Bergkvara",
            "Ornskjoldsvik": "Örnsköldsvik",
            "Ornskoldsvik": "Örnsköldsvik",
            "Holmstrand": "Holmestrand",
            "Grimstadt": "Grimstad",

            # Additional variants found in v3 data
            "Ostend": "Ostende",
            "Krageroe": "Kragero",
        }

        self.dest_variant_map = {
            # Common British port variants
            "Glasglow": "Glasgow",
            "GLASGOW": "Glasgow",
            "Grangmouth": "Grangemouth",
            "Plymouh": "Plymouth",
            "Lonon": "London",

            # OCR variants found in v3 data
            "BORROWSTOUNESS": "Borrowstounness",
            "BORROWSTUNESS": "Borrowstounness",
            "BARROWSTOUNNESS": "Borrowstounness",
            "BORROWSTOWNNESS": "Borrowstounness",
            "RROWSTOUNNESS": "Borrowstounness",
            "LIVERPOOLE": "Liverpool",
            "CARNARVON": "Carnavon",
            "DU NDEE": "Dundee",
            "WISBEACH": "Wisbech",
            "GRENOCK": "Greenock",
            "GRANTOWN": "Granton",
            "MIDDLESBOROUGH": "Middlesbrough",
            "KIRCALDY": "Kirkcaldy",
            "IVERNESS": "Inverness",
            "NVERNESS": "Inverness",

            # London dock variations - normalize to standard form
            "LONDON (TILBURY DOCK)": "London (Tilbury Docks)",
            "LONDON (LONDON DOCK)": "London (London Docks)",
            "LONDON (LONDON. DOCKS)": "London (London Docks)",
            "LONDON TILBURY DOCKS": "London (Tilbury Docks)",
        }

        # Cache for fuzzy matching
        self.origin_cache: Dict[str, str] = {}
        self.dest_cache: Dict[str, str] = {}

    def similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def is_obvious_error(self, port: str, port_type: str) -> bool:
        """Check if port is an obvious error."""
        if not port or not port.strip():
            return True

        port = port.strip()

        # Very short strings
        if len(port) <= 2 and port not in ['Mo', 'Mo.']:
            return True

        if port in ['---', '--', '-', '.', '&', 'and', 'or']:
            return True

        # Very long strings (likely OCR garbage)
        if len(port) > 150:
            return True

        # Journal artifacts
        journal_markers = ['TIMBER TRADES JOURNAL', 'JOURNAL', 'IMPORTS', 'EXPORTS',
                          'FREIGHTS', 'FAILURES', 'LIQUIDATIONS', 'DIVIDENDS']
        if any(marker in port.upper() for marker in journal_markers):
            return True

        # Special handling for known non-ports
        if port_type == 'origin':
            # Commodity words that appear as ports in raw data
            commodity_words = ['deals', 'timber', 'staves', 'lathwood', 'pitwood',
                             'props', 'battens', 'boards']
            if port.lower() in commodity_words:
                return True

        # Additional error patterns from completed mappings
        if port_type == 'destination':
            # Destinations that are actually commodities
            if port.upper() in ['PITWOOD', 'DEALS', 'TIMBER']:
                return True

        return False

    def normalize_port(self, port: str, port_type: str) -> str:
        """
        Normalize a port name using completed mappings and fallback logic.

        Returns:
            Normalized port name or empty string if error
        """
        if not port or not port.strip():
            return ""

        port = port.strip()

        # Check cache first
        cache = self.origin_cache if port_type == 'origin' else self.dest_cache
        if port in cache:
            return cache[port]

        # Check completed mappings first (highest priority)
        if port in self.completed_mappings.get(port_type, {}):
            normalized = self.completed_mappings[port_type][port]
            cache[port] = normalized
            return normalized

        # Check for obvious errors
        if self.is_obvious_error(port, port_type):
            cache[port] = ""
            return ""

        # Choose canonical list and variant map
        canonical = self.canonical_origin if port_type == 'origin' else self.canonical_dest
        variant_map = self.origin_variant_map if port_type == 'origin' else self.dest_variant_map

        # Exact match (case-insensitive)
        for canonical_port in canonical:
            if port.lower() == canonical_port.lower():
                cache[port] = canonical_port
                return canonical_port

        # Known variant
        if port in variant_map:
            mapped = variant_map[port]
            # Verify the mapped port is in canonical list
            for canonical_port in canonical:
                if mapped.lower() == canonical_port.lower():
                    cache[port] = canonical_port
                    return canonical_port
            # If not in canonical, use the variant mapping anyway
            cache[port] = mapped
            return mapped

        # Fuzzy match ≥0.92 (high confidence auto-normalize)
        best_match = None
        best_score = 0.92

        for canonical_port in canonical:
            score = self.similarity(port, canonical_port)
            if score > best_score:
                best_score = score
                best_match = canonical_port

        if best_match:
            cache[port] = best_match
            return best_match

        # For new data (1874-1875), accept legitimate ports that aren't in canonical lists
        # These are from years not included in the original canonical extraction
        # Only accept if they appear to be real ports (not errors)
        if len(port) >= 3 and not any(c.isdigit() for c in port):
            # Use as-is for now (could be a legitimate port from a year not in canonical list)
            cache[port] = port
            return port

        # Low confidence or likely error - return empty
        cache[port] = ""
        return ""


def load_canonical_ports(ref_dir: Path) -> Tuple[Set[str], Set[str]]:
    """Load canonical port lists from JSON files."""
    with open(ref_dir / "canonical_origin_ports.json", 'r', encoding='utf-8') as f:
        canonical_origin = set(json.load(f))

    with open(ref_dir / "canonical_destination_ports.json", 'r', encoding='utf-8') as f:
        canonical_dest = set(json.load(f))

    return canonical_origin, canonical_dest


def load_completed_mappings(completed_csv: Path) -> Dict[str, Dict[str, str]]:
    """
    Load completed port mappings from ports_completed.csv.

    Returns:
        {port_type: {original_port: normalized_port}}
    """
    mappings = {
        'origin': {},
        'destination': {}
    }

    print(f"Loading completed port mappings from {completed_csv}...")
    with open(completed_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            port_type = row['port_type']
            original = row['original_port']
            action = row['action']
            map_to = row['map_to_port']

            if action == 'MAP' and map_to:
                mappings[port_type][original] = map_to
            elif action == 'ACCEPT':
                # Use the port as-is
                mappings[port_type][original] = original
            elif action == 'ERROR':
                # Map to empty string
                mappings[port_type][original] = ""

    print(f"  Loaded {len(mappings['origin'])} origin port mappings")
    print(f"  Loaded {len(mappings['destination'])} destination port mappings")

    return mappings


def apply_normalization(input_csv: Path, output_csv: Path, normalizer: PortNormalizer):
    """
    Apply port normalization to database, adding normalized columns.

    Input columns: ..., origin_port, destination_port, ...
    Output columns: ..., origin_port, origin_port_normalized, destination_port, destination_port_normalized, ...
    """
    csv.field_size_limit(1000000)

    # Track statistics
    stats = {
        'total_records': 0,
        'origin_normalized': 0,
        'origin_unchanged': 0,
        'origin_empty': 0,
        'dest_normalized': 0,
        'dest_unchanged': 0,
        'dest_empty': 0,
        'new_origin_ports': Counter(),
        'new_dest_ports': Counter(),
    }

    print(f"\nReading from: {input_csv}")
    print(f"Writing to: {output_csv}")

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        # Add normalized columns after the port columns
        new_fieldnames = []
        for field in fieldnames:
            new_fieldnames.append(field)
            if field == 'origin_port':
                new_fieldnames.append('origin_port_normalized')
            elif field == 'destination_port':
                new_fieldnames.append('destination_port_normalized')

        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
            writer.writeheader()

            for row in reader:
                stats['total_records'] += 1

                # Normalize origin port
                origin_raw = row.get('origin_port', '').strip()
                if origin_raw:
                    origin_normalized = normalizer.normalize_port(origin_raw, 'origin')
                    if origin_normalized == origin_raw:
                        stats['origin_unchanged'] += 1
                    elif origin_normalized == "":
                        stats['origin_empty'] += 1
                    else:
                        stats['origin_normalized'] += 1
                        # Track new ports (not in canonical, not in completed mappings)
                        if origin_raw not in normalizer.completed_mappings.get('origin', {}):
                            if origin_raw.lower() not in {p.lower() for p in normalizer.canonical_origin}:
                                stats['new_origin_ports'][origin_raw] += 1
                else:
                    origin_normalized = ""
                    stats['origin_empty'] += 1

                row['origin_port_normalized'] = origin_normalized

                # Normalize destination port
                dest_raw = row.get('destination_port', '').strip()
                if dest_raw:
                    dest_normalized = normalizer.normalize_port(dest_raw, 'destination')
                    if dest_normalized == dest_raw:
                        stats['dest_unchanged'] += 1
                    elif dest_normalized == "":
                        stats['dest_empty'] += 1
                    else:
                        stats['dest_normalized'] += 1
                        # Track new ports
                        if dest_raw not in normalizer.completed_mappings.get('destination', {}):
                            if dest_raw.lower() not in {p.lower() for p in normalizer.canonical_dest}:
                                stats['new_dest_ports'][dest_raw] += 1
                else:
                    dest_normalized = ""
                    stats['dest_empty'] += 1

                row['destination_port_normalized'] = dest_normalized

                writer.writerow(row)

                # Progress indicator
                if stats['total_records'] % 10000 == 0:
                    print(f"  Processed {stats['total_records']:,} records...")

    return stats


def print_statistics(stats: Dict):
    """Print normalization statistics."""
    print("\n" + "=" * 80)
    print("NORMALIZATION STATISTICS")
    print("=" * 80)
    print(f"\nTotal records processed: {stats['total_records']:,}")

    print(f"\nORIGIN PORTS:")
    print(f"  Normalized (changed): {stats['origin_normalized']:,}")
    print(f"  Unchanged: {stats['origin_unchanged']:,}")
    print(f"  Empty/Error: {stats['origin_empty']:,}")

    print(f"\nDESTINATION PORTS:")
    print(f"  Normalized (changed): {stats['dest_normalized']:,}")
    print(f"  Unchanged: {stats['dest_unchanged']:,}")
    print(f"  Empty/Error: {stats['dest_empty']:,}")

    if stats['new_origin_ports']:
        print(f"\nNEW ORIGIN PORTS (not in canonical or completed mappings):")
        print(f"  Total unique: {len(stats['new_origin_ports'])}")
        print(f"  Top 20 by frequency:")
        for port, count in stats['new_origin_ports'].most_common(20):
            print(f"    {port:40} {count:>6} occurrences")

    if stats['new_dest_ports']:
        print(f"\nNEW DESTINATION PORTS (not in canonical or completed mappings):")
        print(f"  Total unique: {len(stats['new_dest_ports'])}")
        print(f"  Top 20 by frequency:")
        for port, count in stats['new_dest_ports'].most_common(20):
            print(f"    {port:40} {count:>6} occurrences")


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    ref_dir = base_dir / "reference_data"
    auth_dir = base_dir / "final_output" / "authority_normalized"
    parsed_dir = base_dir / "parsed_output"

    print("=" * 80)
    print("APPLYING PORT NORMALIZATION TO V3 DATABASE")
    print("=" * 80)

    # Load canonical ports
    print("\nLoading canonical port lists...")
    canonical_origin, canonical_dest = load_canonical_ports(ref_dir)
    print(f"  Canonical origin ports: {len(canonical_origin)}")
    print(f"  Canonical destination ports: {len(canonical_dest)}")

    # Load completed mappings
    completed_csv = auth_dir / "ports_completed.csv"
    completed_mappings = load_completed_mappings(completed_csv)

    # Initialize normalizer
    print("\nInitializing port normalizer...")
    normalizer = PortNormalizer(canonical_origin, canonical_dest, completed_mappings)

    # Apply normalization
    input_csv = parsed_dir / "ttj_shipments_final_v3_with_llm_1874_1875.csv"
    output_csv = parsed_dir / "ttj_shipments_normalized_v3.csv"

    print("\nApplying normalization to v3 database...")
    stats = apply_normalization(input_csv, output_csv, normalizer)

    # Print statistics
    print_statistics(stats)

    # Save statistics
    stats_file = parsed_dir / "normalization_stats_v3.json"
    # Convert Counter to dict for JSON serialization
    stats_serializable = {
        'total_records': stats['total_records'],
        'origin_normalized': stats['origin_normalized'],
        'origin_unchanged': stats['origin_unchanged'],
        'origin_empty': stats['origin_empty'],
        'dest_normalized': stats['dest_normalized'],
        'dest_unchanged': stats['dest_unchanged'],
        'dest_empty': stats['dest_empty'],
        'new_origin_ports': dict(stats['new_origin_ports'].most_common()),
        'new_dest_ports': dict(stats['new_dest_ports'].most_common()),
    }
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_serializable, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Normalization complete!")
    print(f"✓ Output saved to: {output_csv}")
    print(f"✓ Statistics saved to: {stats_file}")

    if stats['new_origin_ports'] or stats['new_dest_ports']:
        print(f"\n⚠ Warning: Found new ports not in canonical lists or completed mappings.")
        print(f"   These have been accepted as-is. Review the statistics above.")
        print(f"   Consider adding frequently occurring ports to completed mappings.")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Review normalization_stats_v3.json for new ports")
    print("2. Spot-check ttj_shipments_normalized_v3.csv")
    print("3. If satisfied, copy to final_output/ as production database")
    print("=" * 80)


if __name__ == '__main__':
    main()
