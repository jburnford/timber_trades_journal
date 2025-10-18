#!/usr/bin/env python3
"""
Apply port normalization based on human review decisions.
Reads review CSV and generates normalized dataset.
"""

import json
import csv
from pathlib import Path
from collections import Counter


def load_review_decisions(review_csv: Path) -> dict:
    """Load human review decisions from CSV."""

    decisions = {
        'accept': [],  # Accept as-is (legitimate ports from other years)
        'map': {},     # Map original -> canonical
        'error': []    # Mark as error
    }

    with open(review_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip instruction row
            if row['port_type'] == '=== INSTRUCTIONS ===':
                continue

            original = row['original_port']
            action = row['action'].strip().upper()

            if action == 'ACCEPT':
                decisions['accept'].append({
                    'port': original,
                    'port_type': row['port_type'],
                    'ship_count': int(row['ship_count']),
                    'notes': row['notes']
                })
            elif action == 'MAP':
                map_to = row['map_to_port'].strip()
                if not map_to:
                    print(f"WARNING: MAP action without map_to_port for '{original}'")
                    continue
                decisions['map'][original] = {
                    'canonical': map_to,
                    'port_type': row['port_type'],
                    'ship_count': int(row['ship_count']),
                    'notes': row['notes']
                }
            elif action == 'ERROR':
                decisions['error'].append({
                    'port': original,
                    'port_type': row['port_type'],
                    'ship_count': int(row['ship_count']),
                    'notes': row['notes']
                })
            elif action:  # Non-empty but not recognized
                print(f"WARNING: Unknown action '{action}' for port '{original}'")

    return decisions


def apply_normalization(input_csv: Path, output_csv: Path, normalizer, review_decisions: dict,
                       canonical_origin: set, canonical_dest: set):
    """Apply normalization to dataset."""

    csv.field_size_limit(1000000)

    # Build complete mapping
    # 1. Auto-normalized (from normalizer)
    # 2. Human-reviewed ACCEPT (add to canonical)
    # 3. Human-reviewed MAP (add to mapping)
    # 4. Human-reviewed ERROR (mark as empty)

    # Extend canonical lists with ACCEPT decisions
    extended_origin = canonical_origin.copy()
    extended_dest = canonical_dest.copy()

    for accept in review_decisions['accept']:
        if accept['port_type'] == 'origin':
            extended_origin.add(accept['port'])
        else:
            extended_dest.add(accept['port'])

    # Build error set
    error_ports = {err['port'] for err in review_decisions['error']}

    stats = {
        'total_ships': 0,
        'origin_auto_normalized': 0,
        'origin_human_mapped': 0,
        'origin_human_accepted': 0,
        'origin_marked_error': 0,
        'dest_auto_normalized': 0,
        'dest_human_mapped': 0,
        'dest_human_accepted': 0,
        'dest_marked_error': 0,
    }

    with open(input_csv, 'r', encoding='utf-8') as f_in, \
         open(output_csv, 'w', newline='', encoding='utf-8') as f_out:

        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            stats['total_ships'] += 1

            # Normalize origin port
            if row['origin_port']:
                original = row['origin_port'].strip()

                # Check error list first
                if original in error_ports:
                    row['origin_port'] = ''
                    stats['origin_marked_error'] += 1
                # Check human MAP decisions
                elif original in review_decisions['map']:
                    row['origin_port'] = review_decisions['map'][original]['canonical']
                    stats['origin_human_mapped'] += 1
                # Check if in extended canonical (includes ACCEPT)
                elif original in extended_origin:
                    # Keep as-is (exact match or human-accepted)
                    if original not in canonical_origin:
                        stats['origin_human_accepted'] += 1
                else:
                    # Try auto-normalization
                    normalized, confidence, tier = normalizer.normalize_port(original, 'origin')
                    if tier in ['exact', 'variant', 'fuzzy_high'] and normalized:
                        row['origin_port'] = normalized
                        stats['origin_auto_normalized'] += 1

            # Normalize destination port
            if row['destination_port']:
                original = row['destination_port'].strip()

                # Check error list first
                if original in error_ports:
                    row['destination_port'] = ''
                    stats['dest_marked_error'] += 1
                # Check human MAP decisions
                elif original in review_decisions['map']:
                    row['destination_port'] = review_decisions['map'][original]['canonical']
                    stats['dest_human_mapped'] += 1
                # Check if in extended canonical
                elif original in extended_dest:
                    if original not in canonical_dest:
                        stats['dest_human_accepted'] += 1
                else:
                    # Try auto-normalization
                    normalized, confidence, tier = normalizer.normalize_port(original, 'destination')
                    if tier in ['exact', 'variant', 'fuzzy_high'] and normalized:
                        row['destination_port'] = normalized
                        stats['dest_auto_normalized'] += 1

            writer.writerow(row)

            if stats['total_ships'] % 10000 == 0:
                print(f"  Processed {stats['total_ships']:,} ships...")

    return stats


def main():
    from normalize_with_authority_review import PortNormalizer

    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    ref_dir = base_dir / "reference_data"
    auth_dir = base_dir / "final_output" / "authority_normalized"

    print("=" * 80)
    print("APPLYING PORT NORMALIZATION")
    print("=" * 80)

    # Load canonical ports
    print("\nLoading canonical ports...")
    with open(ref_dir / "canonical_origin_ports.json", 'r') as f:
        canonical_origin = set(json.load(f))
    with open(ref_dir / "canonical_destination_ports.json", 'r') as f:
        canonical_dest = set(json.load(f))

    # Load review decisions
    review_csv = auth_dir / "ports_for_review.csv"
    if not review_csv.exists():
        print(f"ERROR: Review file not found: {review_csv}")
        return

    print(f"Loading review decisions from {review_csv}...")
    decisions = load_review_decisions(review_csv)

    print(f"  ACCEPT (keep as-is): {len(decisions['accept'])} ports")
    print(f"  MAP (to canonical): {len(decisions['map'])} ports")
    print(f"  ERROR (remove): {len(decisions['error'])} ports")

    # Initialize normalizer
    normalizer = PortNormalizer(canonical_origin, canonical_dest)

    # Apply to shipments
    print("\nNormalizing shipments...")
    input_csv = base_dir / "final_output" / "ttj_shipments.csv"
    output_csv = auth_dir / "ttj_shipments_authority_normalized.csv"

    stats = apply_normalization(input_csv, output_csv, normalizer, decisions,
                               canonical_origin, canonical_dest)

    # Also apply to cargo details
    print("\nNormalizing cargo details...")
    input_csv = base_dir / "final_output" / "ttj_cargo_details.csv"
    output_csv_cargo = auth_dir / "ttj_cargo_details_authority_normalized.csv"

    # Cargo uses same ships, so we just copy the logic
    # (Cargo details doesn't have port fields, only via record_id link to shipments)
    import shutil
    shutil.copy(input_csv, output_csv_cargo)
    print(f"  Copied cargo details (normalization via shipments link)")

    # Print statistics
    print("\n" + "=" * 80)
    print("NORMALIZATION COMPLETE")
    print("=" * 80)
    print(f"Total ships processed: {stats['total_ships']:,}")
    print(f"\nOrigin ports:")
    print(f"  Auto-normalized: {stats['origin_auto_normalized']:,}")
    print(f"  Human-mapped: {stats['origin_human_mapped']:,}")
    print(f"  Human-accepted: {stats['origin_human_accepted']:,}")
    print(f"  Marked as errors: {stats['origin_marked_error']:,}")
    print(f"\nDestination ports:")
    print(f"  Auto-normalized: {stats['dest_auto_normalized']:,}")
    print(f"  Human-mapped: {stats['dest_human_mapped']:,}")
    print(f"  Human-accepted: {stats['dest_human_accepted']:,}")
    print(f"  Marked as errors: {stats['dest_marked_error']:,}")

    # Save statistics
    stats_file = auth_dir / "normalization_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\n✓ Saved statistics to: {stats_file}")

    print(f"\n✓ Output files:")
    print(f"  {output_csv}")
    print(f"  {output_csv_cargo}")
    print("=" * 80)


if __name__ == '__main__':
    main()
