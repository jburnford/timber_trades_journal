#!/usr/bin/env python3
"""
Batch process TTJ OCR files with multi-page grouping.
Processes pages sequentially to maintain context across page boundaries.
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from collections import defaultdict
from ttj_parser_v3 import TTJContextParser, extract_publication_date_from_filename


def group_multipage_files(ocr_dir: Path) -> List[List[Path]]:
    """
    Group files by document, handling multi-page files.

    Returns:
        List of file groups, where each group is pages of same document
    """
    all_files = sorted(ocr_dir.glob("*.txt"))

    # Group files by base name (before _pNNN)
    groups = defaultdict(list)

    for file_path in all_files:
        # Extract base name and page number
        filename = file_path.name

        # Pattern: ...._p001.txt or ...._p002.txt
        page_match = re.search(r'(.+?)_p(\d{3})\.txt$', filename)

        if page_match:
            base_name = page_match.group(1)
            page_num = int(page_match.group(2))
            groups[base_name].append((page_num, file_path))
        else:
            # Single-page file (no _pNNN suffix)
            groups[filename].append((0, file_path))

    # Sort pages within each group and return as list of file lists
    file_groups = []
    for base_name in sorted(groups.keys()):
        pages = sorted(groups[base_name], key=lambda x: x[0])
        file_groups.append([page[1] for page in pages])

    return file_groups


def process_file_group(parser: TTJContextParser, file_group: List[Path],
                       stats: Dict) -> List[Dict]:
    """
    Process a group of related pages sequentially.

    Args:
        parser: Parser instance (maintains state across pages)
        file_group: List of file paths to process as a unit
        stats: Statistics dict to update

    Returns:
        List of record dicts
    """
    all_records = []

    # Extract publication date from first file
    pub_year, pub_month, pub_day = extract_publication_date_from_filename(
        file_group[0].name
    )

    # Process each page in sequence
    for page_file in file_group:
        try:
            # Parse file (parser maintains context)
            records = parser.parse_file(page_file, year=pub_year)

            # Convert to dict format
            for record in records:
                all_records.append({
                    'source_file': page_file.name,
                    'line_number': record.line_number,
                    'ship_name': record.ship_name,
                    'origin_port': record.origin_port,
                    'destination_port': record.destination_port,
                    'cargo': record.cargo,
                    'merchant': record.merchant,
                    'arrival_day': record.day,
                    'arrival_month': record.month,
                    'arrival_year': record.year,
                    'publication_day': record.publication_day,
                    'publication_month': record.publication_month,
                    'publication_year': record.publication_year,
                    'is_steamship': record.is_steamship,
                    'format_type': record.format_type.value,
                    'confidence': record.confidence,
                    'raw_line': record.raw_line
                })

            stats['processed'] += 1
            stats['total_records'] += len(records)
            stats['records_with_port'] += sum(1 for r in records if r.destination_port)
            stats['records_with_date'] += sum(1 for r in records if r.day and r.month)

        except Exception as e:
            print(f"  ERROR processing {page_file.name}: {e}")
            stats['failed'] += 1

    return all_records


def process_all_files(ocr_dir: Path, output_dir: Path):
    """
    Process all OCR text files, grouping multi-page documents.

    Args:
        ocr_dir: Directory containing OCR .txt files
        output_dir: Directory for output files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group files
    print("Grouping multi-page files...")
    file_groups = group_multipage_files(ocr_dir)

    total_files = sum(len(group) for group in file_groups)
    print(f"Found {total_files} OCR files in {len(file_groups)} document groups")
    print("=" * 80)

    all_records = []
    stats = {
        'total_files': total_files,
        'total_groups': len(file_groups),
        'processed': 0,
        'failed': 0,
        'total_records': 0,
        'records_with_port': 0,
        'records_with_date': 0,
    }

    # Process each group
    for group_idx, file_group in enumerate(file_groups, 1):
        group_name = file_group[0].name[:60]
        if len(file_group) > 1:
            group_name += f" (+{len(file_group)-1} pages)"

        print(f"[{group_idx}/{len(file_groups)}] Processing {group_name}...")

        # Create new parser for each document group (fresh context)
        parser = TTJContextParser()

        # Process group
        records = process_file_group(parser, file_group, stats)
        all_records.extend(records)

        if group_idx % 50 == 0:
            print(f"  Progress: {stats['total_records']:,} records extracted so far...")

    # Save to CSV
    csv_file = output_dir / "ttj_shipments_multipage.csv"
    print(f"\nSaving {len(all_records):,} records to CSV...")

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'format_type', 'confidence', 'raw_line'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"✓ CSV saved: {csv_file}")

    # Save summary JSON
    summary_file = output_dir / "processing_summary_multipage.json"
    summary = {
        'timestamp': datetime.now().isoformat(),
        'statistics': stats,
        'port_coverage': f"{100 * stats['records_with_port'] / max(1, stats['total_records']):.1f}%",
        'date_coverage': f"{100 * stats['records_with_date'] / max(1, stats['total_records']):.1f}%"
    }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"✓ Summary saved: {summary_file}")

    # Print final statistics
    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETE (Multi-page aware)")
    print("=" * 80)
    print(f"Document groups: {stats['total_groups']}")
    print(f"Files processed: {stats['processed']}/{stats['total_files']}")
    print(f"Failed: {stats['failed']}")
    print(f"\nTotal ship records: {stats['total_records']:,}")
    print(f"  With destination port: {stats['records_with_port']:,} ({100 * stats['records_with_port'] / max(1, stats['total_records']):.1f}%)")
    print(f"  With arrival date: {stats['records_with_date']:,} ({100 * stats['records_with_date'] / max(1, stats['total_records']):.1f}%)")
    print(f"\nOutput files:")
    print(f"  CSV: {csv_file}")
    print(f"  Summary: {summary_file}")
    print("=" * 80)


def main():
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/parsed_output")

    print("TTJ BATCH PARSER (Multi-page aware)")
    print("=" * 80)
    print(f"OCR directory: {ocr_dir}")
    print(f"Output directory: {output_dir}")
    print()

    process_all_files(ocr_dir, output_dir)


if __name__ == '__main__':
    main()
