#!/usr/bin/env python3
"""
Auto-map obvious port variants before human review.
Handles known historical names, OCR errors, and high-confidence matches.
"""

import json
import csv
from pathlib import Path
from difflib import SequenceMatcher


def build_enhanced_variant_map(canonical_origin: set, canonical_dest: set) -> dict:
    """Build comprehensive variant mapping including historical names."""

    origin_map = {
        # Historical German → Modern names
        "Memel": "Klaipeda",
        "Dantzig": "Danzig",
        "Dantzic": "Danzig",
        "Danzic": "Danzig",
        "Windau": "Ventspils",
        "Libau": "Liepāja",

        # Scandinavian variants
        "Cronstadt": "Kronstadt",
        "Cronstad": "Kronstadt",
        "G'burg": "Gothenburg",
        "G'berg": "Gothenburg",
        "Gothenburgh": "Gothenburg",
        "F'stad": "Fredrikstad",
        "Fred'stad": "Fredrikstad",
        "Fredrikstadt": "Fredrikstad",
        "Frederikstad": "Fredrikstad",
        "Frederickstad": "Fredrikstad",
        "Fredrikshald": "Halden",
        "Frederikshald": "Halden",
        "Frederickshald": "Halden",
        "Krageroe": "Kragero",
        "Drontheim": "Trondheim",
        "Christiania": "Kristiania",
        "Christ'a": "Kristiania",
        "Cristobal": "Kristiania",  # If OCR error

        # Swedish ports
        "Gefle": "Gävle",  # Check if in canonical
        "Hernosand": "Harnosand",
        "Hudiksvall": "Hudikswall",
        "Bjorneborg": "Bjorneborg",  # Keep as-is (already canonical?)
        "Swartvik": "Svartvik",
        "Swartwick": "Svartvik",
        "Swartwik": "Svartvik",
        "Finklippan": "Finnklippan",
        "Westervik": "Västervik",  # Check canonical
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
        "Calmar": "Kalmar",
        "Falkenburg": "Falkenberg",
        "Vefsen": "Vefsn",

        # North American
        "St. John, N.B.": "St. John",
        "St. John's, N.B.": "St. John",
        "St. John, N. B.": "St. John",
        "St. Johns": "St. John",
        "Halifax, N.S.": "Halifax",
        "Charlotte Town": "Charlottetown",
        "Chatham, N.B.": "Chatham",
        "Norfolk, Va.": "Norfolk",
        "Parrsboro'": "Parrsboro",  # Check canonical

        # Russian/Baltic
        "Archangel": "Arkhangelsk",
        "Wyburg": "Vyborg",
        "Wyborg": "Vyborg",

        # French ports
        "l'Orient": "Lorient",  # Check if these are same
        "Havre": "Le Havre",
        "St. Brieux": "St. Malo",  # Check if correct
        "St. Malo": "St. Malo",

        # Abbreviations
        "P'burg": "Porsgrund",  # Check canonical
        "Dram": "Drammen",

        # Common OCR errors
        "Richibucto": "Richibouctou",
        "Ostend": "Ostende",
    }

    dest_map = {
        # Capitalization fixes
        "LONDON": "London",
        "LIVERPOOL": "Liverpool",
        "HULL": "Hull",
        "SUNDERLAND": "Sunderland",
        "CARDIFF": "Cardiff",
        "DUNDEE": "Dundee",
        "BRISTOL": "Bristol",
        "GLASGOW": "Glasgow",
        "LEITH": "Leith",
        "TYNE": "Tyne",
        "GREENOCK": "Greenock",
        "NEWPORT": "Newport",
        "SWANSEA": "Swansea",
        "GOOLE": "Goole",
        "GRIMSBY": "Grimsby",
        "ABERDEEN": "Aberdeen",
        "MIDDLESBROUGH": "Middlesbrough",
        "BELFAST": "Belfast",
        "DUBLIN": "Dublin",
        "CORK": "Cork",
        "NEWCASTLE": "Newcastle",
        "ANTWERP": "Antwerp",
        "WOOLWICH": "Woolwich",
        "GREENHITHE": "Greenhithe",
        "DEPTFORD": "Deptford",
        "NORTHFLEET": "Northfleet",
        "INVERKEITHING": "Inverkeithing",
        "MALDON": "Maldon",

        # London docks - use full canonical format
        "SURREY COMMERCIAL DOCKS": "London (Surrey Commercial Docks)",
        "MILLWALL DOCKS": "London (Millwall Docks)",
        "VICTORIA DOCKS": "London (Victoria Docks)",
        "WEST INDIA DOCKS": "London (West India Docks)",
        "EAST INDIA DOCKS": "London (East India Docks)",
        "ROYAL ALBERT DOCKS": "London (Royal Albert Docks)",
        "TILBURY DOCKS": "London (Tilbury Docks)",
        "LONDON DOCKS": "London (London Docks)",
        "OTHER DOCKS AND WHARVES": "London (Other Docks and Wharves)",
        "REGENT'S CANAL DOCKS": "London (Regent's Canal Docks)",
        "ST. KATHARINE'S DOCKS": "London (St. Katharine's Docks)",

        # Specific port mappings
        "WEST HARTLEPOOL": "Hartlepool (West)",
        "THE TYNE": "Tyne",
        "BO'NESS": "Borrowstounness",
        "GREAT YARMOUTH": "Yarmouth",
        "KING'S LYNN": "Lynn",
        "PORT GLASGOW": "Port Glasgow",
        "COMMERCIAL DOCKS": "London (Surrey Commercial Docks)",  # Most common London commercial dock

        # Common misspellings
        "Glasglow": "Glasgow",
        "Grangmouth": "Grangemouth",
        "Plymouh": "Plymouth",
        "Lonon": "London",
    }

    # Verify all mapped values are in canonical (or close)
    verified_origin = {}
    for orig, mapped in origin_map.items():
        # Check if mapped value is in canonical or very close
        if mapped in canonical_origin:
            verified_origin[orig] = mapped
        else:
            # Try fuzzy match
            best_match = None
            best_score = 0.90
            for canonical in canonical_origin:
                score = SequenceMatcher(None, mapped.lower(), canonical.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = canonical
            if best_match:
                verified_origin[orig] = best_match
            else:
                print(f"  WARNING: '{orig}' → '{mapped}' but '{mapped}' not in canonical")

    verified_dest = {}
    for orig, mapped in dest_map.items():
        if mapped in canonical_dest:
            verified_dest[orig] = mapped
        else:
            # Try fuzzy match
            best_match = None
            best_score = 0.90
            for canonical in canonical_dest:
                score = SequenceMatcher(None, mapped.lower(), canonical.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = canonical
            if best_match:
                verified_dest[orig] = best_match
            else:
                # Check if it's a London dock variation
                if "london" in mapped.lower() and "(" in mapped:
                    # Keep as-is (it's a canonical London dock)
                    verified_dest[orig] = mapped
                else:
                    print(f"  WARNING: '{orig}' → '{mapped}' but '{mapped}' not in canonical")

    return verified_origin, verified_dest


def auto_fill_review_csv(review_csv: Path, canonical_origin: set, canonical_dest: set):
    """Auto-fill obvious mappings in review CSV."""

    print("=" * 80)
    print("AUTO-MAPPING OBVIOUS VARIANTS")
    print("=" * 80)

    # Build variant maps
    print("\nBuilding enhanced variant mappings...")
    origin_map, dest_map = build_enhanced_variant_map(canonical_origin, canonical_dest)
    print(f"  Origin mappings: {len(origin_map)}")
    print(f"  Destination mappings: {len(dest_map)}")

    # Read review CSV
    records = []
    with open(review_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            records.append(row)

    # Auto-fill
    auto_filled = 0
    high_conf_fuzzy = 0

    for record in records:
        # Skip instruction row
        if record['port_type'] == '=== INSTRUCTIONS ===':
            continue

        # Skip if already filled
        if record['action']:
            continue

        original = record['original_port']
        port_type = record['port_type']

        # Check variant map
        variant_map = origin_map if port_type == 'origin' else dest_map
        if original in variant_map:
            record['action'] = 'MAP'
            record['map_to_port'] = variant_map[original]
            record['notes'] = 'Auto-mapped (known variant)'
            auto_filled += 1
            continue

        # Check high-confidence fuzzy match (≥0.95)
        canonical = canonical_origin if port_type == 'origin' else canonical_dest
        best_match = None
        best_score = 0.95

        for canonical_port in canonical:
            score = SequenceMatcher(None, original.lower(), canonical_port.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = canonical_port

        if best_match:
            record['action'] = 'MAP'
            record['map_to_port'] = best_match
            record['notes'] = f'Auto-mapped (fuzzy {best_score:.3f})'
            high_conf_fuzzy += 1

    # Write back
    backup_csv = review_csv.parent / f"{review_csv.stem}_backup{review_csv.suffix}"
    review_csv.rename(backup_csv)
    print(f"\n✓ Backed up original to: {backup_csv}")

    with open(review_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"✓ Updated review CSV: {review_csv}")

    # Statistics
    total_for_review = len([r for r in records if r['port_type'] != '=== INSTRUCTIONS ==='])
    remaining = len([r for r in records if not r['action'] and r['port_type'] != '=== INSTRUCTIONS ==='])

    print("\n" + "=" * 80)
    print("AUTO-MAPPING COMPLETE")
    print("=" * 80)
    print(f"Total ports for review: {total_for_review}")
    print(f"  Auto-mapped (variants): {auto_filled}")
    print(f"  Auto-mapped (fuzzy ≥0.95): {high_conf_fuzzy}")
    print(f"  Remaining for human review: {remaining}")
    print(f"  Percentage automated: {100*(auto_filled + high_conf_fuzzy)/total_for_review:.1f}%")

    # Show what's left
    remaining_records = [r for r in records if not r['action'] and r['port_type'] != '=== INSTRUCTIONS ===']
    remaining_records.sort(key=lambda x: int(x['ship_count']), reverse=True)

    print(f"\nTop 30 remaining for human review:")
    for i, rec in enumerate(remaining_records[:30], 1):
        match_str = f" → {rec['best_match_canonical']} ({rec['similarity_score']})" if rec['best_match_canonical'] else ""
        print(f"  {i:2}. [{rec['port_type']:11}] {rec['original_port']:30} {rec['ship_count']:4} ships{match_str}")

    if remaining > 30:
        print(f"  ... and {remaining - 30} more")

    print("\n" + "=" * 80)
    print("NEXT: Review remaining ports and save the CSV")
    print("=" * 80)


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    ref_dir = base_dir / "reference_data"
    auth_dir = base_dir / "final_output" / "authority_normalized"

    # Load canonical ports
    with open(ref_dir / "canonical_origin_ports.json", 'r') as f:
        canonical_origin = set(json.load(f))
    with open(ref_dir / "canonical_destination_ports.json", 'r') as f:
        canonical_dest = set(json.load(f))

    # Auto-fill review CSV
    review_csv = auth_dir / "ports_for_review.csv"
    auto_fill_review_csv(review_csv, canonical_origin, canonical_dest)


if __name__ == '__main__':
    main()
