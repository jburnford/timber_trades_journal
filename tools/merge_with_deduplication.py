#!/usr/bin/env python3
"""
Phase 5: Merge extracted ships with main dataset, using careful deduplication.

Strategy:
1. Combine all 4 extraction files
2. Check each extracted ship against the original_extracted_ship from that line
3. Use fuzzy matching to detect duplicates (ship names may have minor variations)
4. Flag potential duplicates for review
5. Merge clean records with main dataset
"""
import csv
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

csv.field_size_limit(sys.maxsize)

def normalize_ship_name(name: str) -> str:
    """Normalize ship name for comparison."""
    if not name:
        return ''
    # Lowercase, remove extra whitespace, remove punctuation
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
    name = re.sub(r'\s+', ' ', name)  # Collapse whitespace
    return name

def ships_are_similar(ship1: str, ship2: str, threshold: float = 0.85) -> Tuple[bool, float]:
    """
    Check if two ship names are similar using fuzzy matching.
    Returns (is_similar, similarity_score)
    """
    norm1 = normalize_ship_name(ship1)
    norm2 = normalize_ship_name(ship2)

    if not norm1 or not norm2:
        return False, 0.0

    # Exact match after normalization
    if norm1 == norm2:
        return True, 1.0

    # Fuzzy match using SequenceMatcher
    similarity = SequenceMatcher(None, norm1, norm2).ratio()

    return similarity >= threshold, similarity

def merge_extracted_ships(extraction_files: List[Path], main_csv: Path,
                          output_csv: Path, duplicates_csv: Path,
                          stats_file: Path):
    """
    Merge extracted ships with main dataset using careful deduplication.
    """

    print("="*80)
    print("PHASE 5: MERGING EXTRACTED SHIPS WITH DEDUPLICATION")
    print("="*80)

    # Step 1: Load all extracted ships
    print("\nStep 1: Loading extracted ships from all sources...")
    all_extracted = []

    for filepath in extraction_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_extracted.append(row)
        print(f"  Loaded {filepath.name}: {len(all_extracted)} total extracted ships")

    print(f"\nTotal extracted ships to process: {len(all_extracted):,}")

    # Step 2: Deduplicate against original extracted ships
    print("\nStep 2: Checking for duplicates against original extractions...")

    clean_ships = []
    potential_duplicates = []
    exact_duplicates = 0
    fuzzy_duplicates = 0

    for idx, ship in enumerate(all_extracted, 1):
        if idx % 1000 == 0:
            print(f"  Processed {idx:,}/{len(all_extracted):,}...")

        ship_name = ship['ship_name']
        original_ship = ship['original_extracted_ship']

        # Check if this ship is similar to the original extracted ship
        is_similar, similarity = ships_are_similar(ship_name, original_ship)

        if is_similar:
            if similarity == 1.0:
                exact_duplicates += 1
            else:
                fuzzy_duplicates += 1

            # Add to potential duplicates list with similarity score
            dup_record = ship.copy()
            dup_record['similarity_score'] = f"{similarity:.4f}"
            dup_record['duplicate_reason'] = 'Similar to original_extracted_ship'
            potential_duplicates.append(dup_record)
        else:
            # Not a duplicate - add to clean ships
            clean_ships.append(ship)

    print(f"\n  Clean ships (not duplicates): {len(clean_ships):,}")
    print(f"  Potential duplicates found: {len(potential_duplicates):,}")
    print(f"    - Exact duplicates: {exact_duplicates:,}")
    print(f"    - Fuzzy duplicates (>85% similar): {fuzzy_duplicates:,}")

    # Step 3: Check for internal duplicates within clean_ships
    print("\nStep 3: Checking for internal duplicates within extracted ships...")

    # Create index by (source_file, line_number, ship_name) for quick duplicate detection
    ship_index = {}
    internal_duplicates = []
    truly_clean_ships = []

    for ship in clean_ships:
        # Create a key based on source, line, ship name, and port
        key = (
            ship['source_file'],
            ship['line_number'],
            normalize_ship_name(ship['ship_name']),
            normalize_ship_name(ship['origin_port'])
        )

        if key in ship_index:
            # This is a duplicate within our extracted ships
            dup_record = ship.copy()
            dup_record['similarity_score'] = '1.0000'
            dup_record['duplicate_reason'] = 'Duplicate within extracted ships'
            internal_duplicates.append(dup_record)
        else:
            ship_index[key] = True
            truly_clean_ships.append(ship)

    print(f"  Internal duplicates removed: {len(internal_duplicates):,}")
    print(f"  Truly clean ships remaining: {len(truly_clean_ships):,}")

    # Step 4: Load main dataset to check for existing ships
    print("\nStep 4: Checking against main dataset for pre-existing ships...")

    # Build index of main dataset ships
    main_ship_index = {}
    main_record_count = 0

    with open(main_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            main_record_count += 1
            if main_record_count % 10000 == 0:
                print(f"  Indexed {main_record_count:,} main records...")

            # Create key for comparison
            key = (
                row['source_file'],
                row['line_number'],
                normalize_ship_name(row['ship_name']),
                normalize_ship_name(row['origin_port'])
            )
            main_ship_index[key] = True

    print(f"  Main dataset indexed: {main_record_count:,} records")

    # Check truly_clean_ships against main index
    main_duplicates = []
    final_clean_ships = []

    for ship in truly_clean_ships:
        key = (
            ship['source_file'],
            ship['line_number'],
            normalize_ship_name(ship['ship_name']),
            normalize_ship_name(ship['origin_port'])
        )

        if key in main_ship_index:
            dup_record = ship.copy()
            dup_record['similarity_score'] = '1.0000'
            dup_record['duplicate_reason'] = 'Already in main dataset'
            main_duplicates.append(dup_record)
        else:
            final_clean_ships.append(ship)

    print(f"  Ships already in main dataset: {len(main_duplicates):,}")
    print(f"  Final clean ships to add: {len(final_clean_ships):,}")

    # Step 5: Write duplicates file for review
    print(f"\nStep 5: Writing duplicates to {duplicates_csv}...")

    all_duplicates = potential_duplicates + internal_duplicates + main_duplicates

    if all_duplicates:
        fieldnames = list(all_duplicates[0].keys())
        with open(duplicates_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_duplicates)

    print(f"  Total duplicates written: {len(all_duplicates):,}")

    # Step 6: Merge clean ships with main dataset
    print(f"\nStep 6: Merging {len(final_clean_ships):,} clean ships with main dataset...")

    # Read main dataset
    main_records = []
    with open(main_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        main_fieldnames = reader.fieldnames
        for row in reader:
            main_records.append(row)

    print(f"  Main dataset records: {len(main_records):,}")

    # Prepare clean ships for merging - ensure they have all main fieldnames
    merged_records = main_records.copy()

    # Get main fieldnames and add extraction-specific fields
    output_fieldnames = list(main_fieldnames) + ['extraction_method', 'needs_review', 'original_extracted_ship']

    # Add extraction_method, needs_review, original_extracted_ship to main records if not present
    for record in merged_records:
        if 'extraction_method' not in record:
            record['extraction_method'] = ''
        if 'needs_review' not in record:
            record['needs_review'] = ''
        if 'original_extracted_ship' not in record:
            record['original_extracted_ship'] = ''

    # Add clean ships - map their fields to main dataset fields
    for ship in final_clean_ships:
        merged_record = {}

        # Copy fields that exist in main dataset
        for field in main_fieldnames:
            merged_record[field] = ship.get(field, '')

        # Add extraction-specific fields
        merged_record['extraction_method'] = ship.get('extraction_method', '')
        merged_record['needs_review'] = ship.get('needs_review', '')
        merged_record['original_extracted_ship'] = ship.get('original_extracted_ship', '')

        merged_records.append(merged_record)

    # Write merged dataset
    print(f"\nStep 7: Writing merged dataset to {output_csv}...")

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(merged_records)

    print(f"  Merged dataset records: {len(merged_records):,}")

    # Step 8: Write statistics
    print(f"\nStep 8: Writing statistics to {stats_file}...")

    stats = {
        'Total extracted ships': len(all_extracted),
        'Duplicates vs original_extracted_ship': len(potential_duplicates),
        '  - Exact name matches': exact_duplicates,
        '  - Fuzzy matches (>85% similar)': fuzzy_duplicates,
        'Internal duplicates (within extractions)': len(internal_duplicates),
        'Already in main dataset': len(main_duplicates),
        'Total duplicates removed': len(all_duplicates),
        'Clean ships added to dataset': len(final_clean_ships),
        'Original main dataset size': len(main_records),
        'Final merged dataset size': len(merged_records),
        'Net increase': len(merged_records) - len(main_records)
    }

    with open(stats_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("MERGE AND DEDUPLICATION STATISTICS\n")
        f.write("="*80 + "\n\n")
        for key, value in stats.items():
            f.write(f"{key:45} : {value:>10,}\n")
        f.write("\n" + "="*80 + "\n")

    # Print statistics to console
    print("\n" + "="*80)
    print("MERGE AND DEDUPLICATION SUMMARY")
    print("="*80)
    for key, value in stats.items():
        print(f"{key:45} : {value:>10,}")
    print("="*80)

    print(f"\nOutput files created:")
    print(f"  - Merged dataset: {output_csv}")
    print(f"  - Duplicates (for review): {duplicates_csv}")
    print(f"  - Statistics: {stats_file}")
    print("="*80)

    return stats

if __name__ == '__main__':
    extraction_files = [
        Path("/home/jic823/TTJ Forest of Numbers/parsed_output/mega_extracted_ships.csv"),
        Path("/home/jic823/TTJ Forest of Numbers/parsed_output/multi_ship_extracted.csv"),
        Path("/home/jic823/TTJ Forest of Numbers/parsed_output/hyphen_format_extracted.csv"),
        Path("/home/jic823/TTJ Forest of Numbers/parsed_output/small_multi_extracted.csv")
    ]

    main_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final.csv")
    output_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_merged.csv")
    duplicates_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/extraction_duplicates.csv")
    stats_file = Path("/home/jic823/TTJ Forest of Numbers/analysis/merge_statistics.txt")

    merge_extracted_ships(extraction_files, main_csv, output_csv, duplicates_csv, stats_file)
