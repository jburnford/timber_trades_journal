#!/usr/bin/env python3
"""
Apply Phase 1 port normalization improvements to v3 database.
Fixes: journal artifacts, dock standardization, stand-alone docks.
"""

import json
import csv
import re
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, Set, Tuple, Optional
from collections import Counter


class PortNormalizerV4:
    """Enhanced port normalizer with Phase 1 improvements."""

    def __init__(self, canonical_origin: Set[str], canonical_dest: Set[str],
                 completed_mappings: Dict[str, Dict[str, str]]):
        self.canonical_origin = canonical_origin
        self.canonical_dest = canonical_dest
        self.completed_mappings = completed_mappings

        # Known variant mappings
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
            "Ostend": "Ostende",
        }

        self.dest_variant_map = {
            # Common British port variants
            "Glasglow": "Glasgow",
            "GLASGOW": "Glasgow",
            "Grangmouth": "Grangemouth",
            "Plymouh": "Plymouth",
            "Lonon": "London",

            # OCR variants
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

            # London dock variations
            "LONDON (TILBURY DOCK)": "London (Tilbury Docks)",
            "LONDON (LONDON DOCK)": "London (London Docks)",
            "LONDON (LONDON. DOCKS)": "London (London Docks)",
            "LONDON TILBURY DOCKS": "London (Tilbury Docks)",
        }

        # PHASE 1 ADDITION: Stand-alone dock to parent port mapping
        self.standalone_dock_parents = {
            "NELSON DOCK": "Liverpool (Nelson Dock)",
            "ALEXANDRA DOCK": "Liverpool (Alexandra Dock)",  # Most common
            "VICTORIA DOCK": "London (Victoria Dock)",  # Most common for timber
            "QUEEN'S DOCK": "Liverpool (Queen's Dock)",
            "COBURG DOCK": "Liverpool (Coburg Dock)",
            "PRINCE'S DOCK": "Liverpool (Prince's Dock)",
            "PRINCES DOCK": "Liverpool (Prince's Dock)",
            "BRUNSWICK DOCK": "Liverpool (Brunswick Dock)",
            "WELLINGTON DOCK": "Liverpool (Wellington Dock)",
            "TOWER DOCK": "Liverpool (Tower Dock)",
            "UNION DOCK": "Liverpool (Union Dock)",
            "SURREY COMMERCIAL DOCK": "London (Surrey Commercial Docks)",
            "TILBURY DOCK": "London (Tilbury Docks)",
            "TILBURY DOCKS": "London (Tilbury Docks)",
        }

        # Cache
        self.origin_cache: Dict[str, str] = {}
        self.dest_cache: Dict[str, str] = {}

    def similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def is_journal_artifact(self, port: str) -> bool:
        """
        PHASE 1 ENHANCEMENT: Detect journal artifacts (not real ports).

        These are text fragments from bankruptcy notices, building news,
        tender announcements, etc.
        """
        port_upper = port.upper()

        # Bankruptcy and legal notices
        bankruptcy_phrases = [
            'FULLY SECURED',
            'CREDITORS',
            'PETITION PRESENTED',
            'PETITION',
            'REGISTERED',
            'NOTICE TO CREDITORS',
            'NOTICES TO CREDITORS',
            'CESSIO',
        ]
        if any(phrase in port_upper for phrase in bankruptcy_phrases):
            return True

        # Journal sections
        section_headers = [
            'BUILDING NEWS',
            'SOUND LIST',
            'CORRESPONDENCE',
            'IMPORTERS OF',
            'TIMBER TRADES JOURNAL',
            'JOURNAL',
        ]
        if any(header in port_upper for header in section_headers):
            return True

        # Tender and business announcements
        business_phrases = [
            'TENDERS OPEN',
            'TENDERS',
            'RESULTS OF TENDERS',
            'RESULTS OF',
        ]
        if any(phrase in port_upper for phrase in business_phrases):
            return True

        # Known abbreviations from journal layout
        if port_upper in ['WMW', 'W.M.W.']:
            return True

        return False

    def is_obvious_error(self, port: str, port_type: str) -> bool:
        """Check if port is an obvious error."""
        if not port or not port.strip():
            return True

        port = port.strip()

        # PHASE 1: Check journal artifacts first
        if self.is_journal_artifact(port):
            return True

        # Very short strings
        if len(port) <= 2 and port not in ['Mo', 'Mo.']:
            return True

        if port in ['---', '--', '-', '.', '&', 'and', 'or']:
            return True

        # Very long strings (likely OCR garbage)
        if len(port) > 150:
            return True

        # General journal markers
        journal_markers = ['IMPORTS', 'EXPORTS', 'FREIGHTS', 'FAILURES',
                          'LIQUIDATIONS', 'DIVIDENDS']
        if any(marker in port.upper() for marker in journal_markers):
            return True

        # Commodity words
        if port_type == 'origin':
            commodity_words = ['deals', 'timber', 'staves', 'lathwood', 'pitwood',
                             'props', 'battens', 'boards']
            if port.lower() in commodity_words:
                return True

        if port_type == 'destination':
            if port.upper() in ['PITWOOD', 'DEALS', 'TIMBER', 'REDWOOD']:
                return True

        return False

    def standardize_dock_name(self, port: str) -> str:
        """
        PHASE 1 ENHANCEMENT: Standardize dock naming conventions.

        Rules:
        1. Proper case (Liverpool not LIVERPOOL)
        2. Standardize apostrophes (Queen's not QUEENS)
        3. Standardize dock names (Tilbury Docks not TILBURY DOCK)
        """
        # Check if this is a dock name pattern: CITY (DOCK NAME)
        match = re.match(r'^([A-Z\s]+)\s*\(([^)]+)\)$', port)
        if match:
            city_raw = match.group(1).strip()
            dock_raw = match.group(2).strip()

            # Proper case the city
            city = city_raw.title()

            # Standardize dock name
            dock = dock_raw

            # Fix apostrophes
            dock = re.sub(r"QUEENS?\s+DOCK", "Queen's Dock", dock, flags=re.IGNORECASE)
            dock = re.sub(r"PRINCES?\s+DOCK", "Prince's Dock", dock, flags=re.IGNORECASE)
            dock = re.sub(r"KING'?S?\s+DOCK", "King's Dock", dock, flags=re.IGNORECASE)

            # Standardize dock/docks
            dock = re.sub(r'\bTILBURY DOCKS?\b', 'Tilbury Docks', dock, flags=re.IGNORECASE)
            dock = re.sub(r'\bLONDON DOCKS?\b', 'London Docks', dock, flags=re.IGNORECASE)
            dock = re.sub(r'\bSURREY DOCKS?\b', 'Surrey Commercial Docks', dock, flags=re.IGNORECASE)
            dock = re.sub(r'\bSURREY COMMERCIAL DOCKS?\b', 'Surrey Commercial Docks', dock, flags=re.IGNORECASE)

            # Proper case other dock names if not already handled
            if dock == dock_raw:  # Not yet standardized
                dock = dock.title()
                # Re-capitalize common words
                dock = dock.replace("'S", "'s")

            return f"{city} ({dock})"

        # PHASE 1: Check for stand-alone dock names
        if port.upper() in self.standalone_dock_parents:
            return self.standalone_dock_parents[port.upper()]

        return port

    def normalize_port(self, port: str, port_type: str) -> str:
        """
        Normalize a port name using completed mappings and fallback logic.
        Includes Phase 1 enhancements.
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

        # PHASE 1: Check for obvious errors (includes journal artifacts)
        if self.is_obvious_error(port, port_type):
            cache[port] = ""
            return ""

        # PHASE 1: Standardize dock names for destinations
        if port_type == 'destination':
            standardized = self.standardize_dock_name(port)
            if standardized != port:
                cache[port] = standardized
                return standardized

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

        # Accept legitimate ports not in canonical lists
        if len(port) >= 3 and not any(c.isdigit() for c in port):
            cache[port] = port
            return port

        # Low confidence - return empty
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
    """Load completed port mappings from ports_completed.csv."""
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
                mappings[port_type][original] = original
            elif action == 'ERROR':
                mappings[port_type][original] = ""

    print(f"  Loaded {len(mappings['origin'])} origin port mappings")
    print(f"  Loaded {len(mappings['destination'])} destination port mappings")

    return mappings


def apply_normalization(input_csv: Path, output_csv: Path, normalizer: PortNormalizerV4):
    """Apply port normalization with Phase 1 enhancements."""
    csv.field_size_limit(1000000)

    stats = {
        'total_records': 0,
        'origin_normalized': 0,
        'origin_unchanged': 0,
        'origin_empty': 0,
        'dest_normalized': 0,
        'dest_unchanged': 0,
        'dest_empty': 0,
        'journal_artifacts_removed': 0,
        'docks_standardized': 0,
        'standalone_docks_fixed': 0,
        'new_origin_ports': Counter(),
        'new_dest_ports': Counter(),
    }

    # Track specific improvements
    journal_artifacts = set()
    dock_standardizations = {}
    standalone_fixes = {}

    print(f"\nReading from: {input_csv}")
    print(f"Writing to: {output_csv}")

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        # Use existing normalized column names
        new_fieldnames = []
        for field in fieldnames:
            new_fieldnames.append(field)
            if field == 'origin_port' and 'origin_port_normalized' not in fieldnames:
                new_fieldnames.append('origin_port_normalized')
            elif field == 'destination_port' and 'destination_port_normalized' not in fieldnames:
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
                        if normalizer.is_journal_artifact(origin_raw):
                            stats['journal_artifacts_removed'] += 1
                            journal_artifacts.add(origin_raw)
                    else:
                        stats['origin_normalized'] += 1
                else:
                    origin_normalized = ""
                    stats['origin_empty'] += 1

                row['origin_port_normalized'] = origin_normalized

                # Normalize destination port
                dest_raw = row.get('destination_port', '').strip()
                if dest_raw:
                    dest_normalized = normalizer.normalize_port(dest_raw, 'destination')

                    # Track Phase 1 improvements
                    if dest_normalized == "":
                        stats['dest_empty'] += 1
                        if normalizer.is_journal_artifact(dest_raw):
                            stats['journal_artifacts_removed'] += 1
                            journal_artifacts.add(dest_raw)
                    elif dest_normalized == dest_raw:
                        stats['dest_unchanged'] += 1
                    else:
                        stats['dest_normalized'] += 1

                        # Check if dock was standardized
                        if '(' in dest_normalized and '(' in dest_raw:
                            if dest_normalized != dest_raw:
                                stats['docks_standardized'] += 1
                                if dest_raw not in dock_standardizations:
                                    dock_standardizations[dest_raw] = dest_normalized

                        # Check if standalone dock was fixed
                        if dest_raw.upper() in normalizer.standalone_dock_parents:
                            stats['standalone_docks_fixed'] += 1
                            standalone_fixes[dest_raw] = dest_normalized
                else:
                    dest_normalized = ""
                    stats['dest_empty'] += 1

                row['destination_port_normalized'] = dest_normalized

                writer.writerow(row)

                # Progress indicator
                if stats['total_records'] % 10000 == 0:
                    print(f"  Processed {stats['total_records']:,} records...")

    # Store detailed improvement tracking
    stats['journal_artifacts_list'] = sorted(journal_artifacts)
    stats['dock_standardizations'] = dock_standardizations
    stats['standalone_fixes'] = standalone_fixes

    return stats


def print_statistics(stats: Dict):
    """Print normalization statistics with Phase 1 highlights."""
    print("\n" + "=" * 80)
    print("NORMALIZATION STATISTICS - VERSION 4 (Phase 1)")
    print("=" * 80)
    print(f"\nTotal records processed: {stats['total_records']:,}")

    print(f"\n{'=' * 80}")
    print("PHASE 1 IMPROVEMENTS")
    print(f"{'=' * 80}")
    print(f"\n✓ Journal artifacts removed: {stats['journal_artifacts_removed']:,} records")
    print(f"✓ Docks standardized: {stats['docks_standardized']:,} records")
    print(f"✓ Stand-alone docks fixed: {stats['standalone_docks_fixed']:,} records")
    print(f"\nTOTAL PHASE 1 IMPACT: {stats['journal_artifacts_removed'] + stats['docks_standardized'] + stats['standalone_docks_fixed']:,} records improved")

    if stats.get('journal_artifacts_list'):
        print(f"\nJournal artifacts detected and removed:")
        for artifact in sorted(stats['journal_artifacts_list'])[:20]:
            print(f"  - {artifact}")
        if len(stats['journal_artifacts_list']) > 20:
            print(f"  ... and {len(stats['journal_artifacts_list']) - 20} more")

    if stats.get('standalone_fixes'):
        print(f"\nStand-alone docks fixed (showing first 10):")
        for raw, normalized in list(stats['standalone_fixes'].items())[:10]:
            print(f"  {raw:30} → {normalized}")

    print(f"\n{'=' * 80}")
    print("OVERALL NORMALIZATION")
    print(f"{'=' * 80}")

    print(f"\nORIGIN PORTS:")
    print(f"  Normalized (changed): {stats['origin_normalized']:,}")
    print(f"  Unchanged: {stats['origin_unchanged']:,}")
    print(f"  Empty/Error: {stats['origin_empty']:,}")

    print(f"\nDESTINATION PORTS:")
    print(f"  Normalized (changed): {stats['dest_normalized']:,}")
    print(f"  Unchanged: {stats['dest_unchanged']:,}")
    print(f"  Empty/Error: {stats['dest_empty']:,}")


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    ref_dir = base_dir / "reference_data"
    auth_dir = base_dir / "final_output" / "authority_normalized"
    parsed_dir = base_dir / "parsed_output"

    print("=" * 80)
    print("APPLYING PORT NORMALIZATION V4 - PHASE 1 IMPROVEMENTS")
    print("=" * 80)
    print("\nPhase 1 includes:")
    print("  1. Enhanced journal artifact detection")
    print("  2. Dock name standardization")
    print("  3. Stand-alone dock parent port mapping")

    # Load canonical ports
    print("\nLoading canonical port lists...")
    canonical_origin, canonical_dest = load_canonical_ports(ref_dir)
    print(f"  Canonical origin ports: {len(canonical_origin)}")
    print(f"  Canonical destination ports: {len(canonical_dest)}")

    # Load completed mappings
    completed_csv = auth_dir / "ports_completed.csv"
    completed_mappings = load_completed_mappings(completed_csv)

    # Initialize normalizer
    print("\nInitializing enhanced port normalizer (v4)...")
    normalizer = PortNormalizerV4(canonical_origin, canonical_dest, completed_mappings)

    # Apply normalization
    input_csv = parsed_dir / "ttj_shipments_final_v3_with_llm_1874_1875.csv"
    output_csv = parsed_dir / "ttj_shipments_normalized_v4.csv"

    print("\nApplying Phase 1 normalization enhancements...")
    stats = apply_normalization(input_csv, output_csv, normalizer)

    # Print statistics
    print_statistics(stats)

    # Save statistics
    stats_file = parsed_dir / "normalization_stats_v4_phase1.json"
    stats_serializable = {
        'total_records': stats['total_records'],
        'origin_normalized': stats['origin_normalized'],
        'origin_unchanged': stats['origin_unchanged'],
        'origin_empty': stats['origin_empty'],
        'dest_normalized': stats['dest_normalized'],
        'dest_unchanged': stats['dest_unchanged'],
        'dest_empty': stats['dest_empty'],
        'phase1_improvements': {
            'journal_artifacts_removed': stats['journal_artifacts_removed'],
            'docks_standardized': stats['docks_standardized'],
            'standalone_docks_fixed': stats['standalone_docks_fixed'],
            'journal_artifacts_list': stats.get('journal_artifacts_list', []),
            'dock_standardizations': stats.get('dock_standardizations', {}),
            'standalone_fixes': stats.get('standalone_fixes', {}),
        }
    }
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_serializable, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Phase 1 normalization complete!")
    print(f"✓ Output saved to: {output_csv}")
    print(f"✓ Statistics saved to: {stats_file}")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Review normalization_stats_v4_phase1.json for detailed improvements")
    print("2. Spot-check ttj_shipments_normalized_v4.csv")
    print("3. Compare v3 vs v4 to verify improvements")
    print("4. If satisfied, proceed to Phase 2 (REDWOOD investigation, etc.)")
    print("=" * 80)


if __name__ == '__main__':
    main()
