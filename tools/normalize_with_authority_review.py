#!/usr/bin/env python3
"""
Authority-based port normalization with human-in-the-loop review.
Three-tier approach: auto-normalize, flag for review, mark as errors.
"""

import json
import csv
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, Set, Tuple, Optional, List


class PortNormalizer:
    """Normalize ports using canonical lists and fuzzy matching."""

    def __init__(self, canonical_origin_ports: Set[str], canonical_dest_ports: Set[str]):
        self.canonical_origin = canonical_origin_ports
        self.canonical_dest = canonical_dest_ports

        # Known variant mappings (from earlier analysis)
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
            "Wyburg": "Wyborg",

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
        }

        self.dest_variant_map = {
            # Common British port variants
            "Glasglow": "Glasgow",
            "Grangmouth": "Grangemouth",
            "Plymouh": "Plymouth",
            "Lonon": "London",  # OCR error
        }

        # Cache for fuzzy matching
        self.origin_cache: Dict[str, Tuple[Optional[str], float, str]] = {}
        self.dest_cache: Dict[str, Tuple[Optional[str], float, str]] = {}

    def similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def is_obvious_error(self, port: str, port_type: str) -> bool:
        """Check if port is an obvious error."""
        if not port or not port.strip():
            return True

        port = port.strip()

        # Universal checks
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

        # Commodity words as ports
        if port_type == 'origin':
            commodity_words = ['deals', 'timber', 'staves', 'lathwood', 'pitwood',
                             'props', 'battens', 'boards']
            if port.lower() in commodity_words:
                return True

        return False

    def normalize_port(self, port: str, port_type: str) -> Tuple[Optional[str], float, str]:
        """
        Normalize a port name.

        Returns:
            (normalized_port, confidence_score, normalization_tier)
            - normalized_port: The normalized name or None if uncertain
            - confidence_score: 0.0-1.0 (1.0 = exact match)
            - normalization_tier: 'exact', 'variant', 'fuzzy_high', 'fuzzy_medium', 'fuzzy_low', 'error', 'unmapped'
        """
        if not port or not port.strip():
            return (None, 0.0, 'error')

        port = port.strip()

        # Check cache
        cache = self.origin_cache if port_type == 'origin' else self.dest_cache
        if port in cache:
            return cache[port]

        # Choose canonical list and variant map
        canonical = self.canonical_origin if port_type == 'origin' else self.canonical_dest
        variant_map = self.origin_variant_map if port_type == 'origin' else self.dest_variant_map

        # Check for obvious errors
        if self.is_obvious_error(port, port_type):
            result = (None, 0.0, 'error')
            cache[port] = result
            return result

        # Tier 1: Exact match (case-insensitive)
        for canonical_port in canonical:
            if port.lower() == canonical_port.lower():
                result = (canonical_port, 1.0, 'exact')
                cache[port] = result
                return result

        # Tier 1: Known variant
        if port in variant_map:
            mapped = variant_map[port]
            # Verify the mapped port is in canonical list
            for canonical_port in canonical:
                if mapped.lower() == canonical_port.lower():
                    result = (canonical_port, 1.0, 'variant')
                    cache[port] = result
                    return result

        # Tier 1: Fuzzy match ≥0.92 (auto-normalize)
        best_match = None
        best_score = 0.92

        for canonical_port in canonical:
            score = self.similarity(port, canonical_port)
            if score > best_score:
                best_score = score
                best_match = canonical_port

        if best_match:
            result = (best_match, best_score, 'fuzzy_high')
            cache[port] = result
            return result

        # Tier 2: Fuzzy match 0.85-0.92 (flag for review)
        best_match = None
        best_score = 0.85

        for canonical_port in canonical:
            score = self.similarity(port, canonical_port)
            if score > best_score:
                best_score = score
                best_match = canonical_port

        if best_match:
            result = (best_match, best_score, 'fuzzy_medium')
            cache[port] = result
            return result

        # Tier 2/3: No match found
        # Return unmapped with best match if any (even if <0.85)
        best_match = None
        best_score = 0.0

        for canonical_port in canonical:
            score = self.similarity(port, canonical_port)
            if score > best_score:
                best_score = score
                best_match = canonical_port

        if best_score > 0.70:
            result = (best_match, best_score, 'fuzzy_low')
        else:
            result = (None, 0.0, 'unmapped')

        cache[port] = result
        return result


def analyze_ports_for_review(input_csv: Path, normalizer: PortNormalizer) -> Dict:
    """
    Analyze parsed data and categorize ports for human review.

    Returns:
        Dictionary with categorized ports and statistics
    """
    csv.field_size_limit(1000000)

    origin_ports = Counter()
    dest_ports = Counter()
    origin_years = {}  # port -> set of years
    dest_years = {}

    print("Reading parsed data...")
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = row.get('arrival_year') or row.get('publication_year')

            if row['origin_port']:
                port = row['origin_port'].strip()
                origin_ports[port] += 1
                if port not in origin_years:
                    origin_years[port] = set()
                if year:
                    origin_years[port].add(year)

            if row['destination_port']:
                port = row['destination_port'].strip()
                dest_ports[port] += 1
                if port not in dest_years:
                    dest_years[port] = set()
                if year:
                    dest_years[port].add(year)

    print(f"Found {len(origin_ports)} unique origin ports")
    print(f"Found {len(dest_ports)} unique destination ports")

    # Categorize ports
    results = {
        'origin': {
            'auto_normalized': [],  # Tier 1: high confidence
            'for_review': [],        # Tier 2: medium confidence or high-freq unmapped
            'errors': [],            # Tier 3: obvious errors
        },
        'destination': {
            'auto_normalized': [],
            'for_review': [],
            'errors': [],
        },
        'stats': {
            'origin': {'total': len(origin_ports), 'total_ships': sum(origin_ports.values())},
            'destination': {'total': len(dest_ports), 'total_ships': sum(dest_ports.values())},
        }
    }

    # Process origin ports
    print("\nAnalyzing origin ports...")
    for port, count in origin_ports.items():
        normalized, confidence, tier = normalizer.normalize_port(port, 'origin')
        years = sorted(origin_years.get(port, set()))

        port_info = {
            'original': port,
            'normalized': normalized,
            'confidence': confidence,
            'tier': tier,
            'ship_count': count,
            'years': years,
            'year_range': f"{years[0]}-{years[-1]}" if years else "unknown"
        }

        if tier in ['exact', 'variant', 'fuzzy_high']:
            results['origin']['auto_normalized'].append(port_info)
        elif tier == 'error':
            results['origin']['errors'].append(port_info)
        else:
            # Tier 2: fuzzy_medium, fuzzy_low, or high-freq unmapped
            if count >= 20 or tier == 'fuzzy_medium':
                results['origin']['for_review'].append(port_info)
            elif count < 10:
                results['origin']['errors'].append(port_info)
            else:
                results['origin']['for_review'].append(port_info)

    # Process destination ports
    print("Analyzing destination ports...")
    for port, count in dest_ports.items():
        normalized, confidence, tier = normalizer.normalize_port(port, 'destination')
        years = sorted(dest_years.get(port, set()))

        port_info = {
            'original': port,
            'normalized': normalized,
            'confidence': confidence,
            'tier': tier,
            'ship_count': count,
            'years': years,
            'year_range': f"{years[0]}-{years[-1]}" if years else "unknown"
        }

        if tier in ['exact', 'variant', 'fuzzy_high']:
            results['destination']['auto_normalized'].append(port_info)
        elif tier == 'error':
            results['destination']['errors'].append(port_info)
        else:
            if count >= 20 or tier == 'fuzzy_medium':
                results['destination']['for_review'].append(port_info)
            elif count < 10:
                results['destination']['errors'].append(port_info)
            else:
                results['destination']['for_review'].append(port_info)

    # Sort for_review by ship count (descending)
    results['origin']['for_review'].sort(key=lambda x: x['ship_count'], reverse=True)
    results['destination']['for_review'].sort(key=lambda x: x['ship_count'], reverse=True)

    return results


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    ref_dir = base_dir / "reference_data"
    output_dir = base_dir / "final_output" / "authority_normalized"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("AUTHORITY-BASED PORT NORMALIZATION ANALYSIS")
    print("=" * 80)

    # Load canonical ports
    print("\nLoading canonical port lists...")
    with open(ref_dir / "canonical_origin_ports.json", 'r', encoding='utf-8') as f:
        canonical_origin = set(json.load(f))
    print(f"  Canonical origin ports: {len(canonical_origin)}")

    with open(ref_dir / "canonical_destination_ports.json", 'r', encoding='utf-8') as f:
        canonical_dest = set(json.load(f))
    print(f"  Canonical destination ports: {len(canonical_dest)}")

    # Initialize normalizer
    normalizer = PortNormalizer(canonical_origin, canonical_dest)

    # Analyze ports
    input_csv = base_dir / "final_output" / "ttj_shipments.csv"
    results = analyze_ports_for_review(input_csv, normalizer)

    # Print statistics
    print("\n" + "=" * 80)
    print("NORMALIZATION ANALYSIS SUMMARY")
    print("=" * 80)

    for port_type in ['origin', 'destination']:
        print(f"\n{port_type.upper()} PORTS:")
        stats = results['stats'][port_type]
        print(f"  Total unique ports in data: {stats['total']}")
        print(f"  Total ships: {stats['total_ships']}")

        auto = len(results[port_type]['auto_normalized'])
        review = len(results[port_type]['for_review'])
        errors = len(results[port_type]['errors'])

        auto_ships = sum(p['ship_count'] for p in results[port_type]['auto_normalized'])
        review_ships = sum(p['ship_count'] for p in results[port_type]['for_review'])
        error_ships = sum(p['ship_count'] for p in results[port_type]['errors'])

        print(f"\n  Auto-normalized (Tier 1): {auto} ports, {auto_ships} ships")
        print(f"  For review (Tier 2): {review} ports, {review_ships} ships ⭐")
        print(f"  Errors (Tier 3): {errors} ports, {error_ships} ships")

        if review > 0:
            print(f"\n  Top 10 ports needing review:")
            for i, port in enumerate(results[port_type]['for_review'][:10], 1):
                match_str = f"→ {port['normalized']} ({port['confidence']:.2f})" if port['normalized'] else "(no match)"
                print(f"    {i:2}. {port['original']:30} {port['ship_count']:4} ships  {match_str}")

    # Save detailed analysis
    analysis_file = output_dir / "normalization_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved detailed analysis to: {analysis_file}")

    print("\n" + "=" * 80)
    print("Next: Run generate_review_csv.py to create human review file")
    print("=" * 80)


if __name__ == '__main__':
    main()
