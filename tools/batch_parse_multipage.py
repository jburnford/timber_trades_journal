#!/usr/bin/env python3
"""
Batch process TTJ OCR files with multi-page grouping.
Processes pages sequentially to maintain context across page boundaries.
"""

import csv
import json
import re
import sys
import time
import logging
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from ttj_parser_v3 import TTJContextParser, extract_publication_date_from_filename

# Increase CSV field size limit to handle long cargo descriptions
csv.field_size_limit(1000000)  # 1MB limit

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parsed_output/batch_parser.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_and_flush(message, level='info'):
    """Log message and force flush to ensure immediate write."""
    getattr(logger, level)(message)
    sys.stdout.flush()
    for handler in logging.root.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()


class TimeoutError(Exception):
    """Raised when parser exceeds timeout."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Parser exceeded timeout")


def parse_with_timeout(parser: TTJContextParser, file_path: Path, year: int,
                       timeout_seconds: int = 5) -> Tuple[List, Optional[str]]:
    """
    Parse a file with timeout protection.

    Args:
        parser: Parser instance
        file_path: Path to file
        year: Publication year
        timeout_seconds: Max seconds to allow

    Returns:
        (records_list, error_message)
        error_message is None on success
    """
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        records = parser.parse_file(file_path, year=year)
        signal.alarm(0)  # Cancel alarm
        return records, None
    except TimeoutError:
        signal.alarm(0)
        return [], f"TIMEOUT after {timeout_seconds}s"
    except Exception as e:
        signal.alarm(0)
        return [], f"ERROR: {str(e)}"


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
            file_start = time.time()

            # Parse file with timeout protection (5 seconds max)
            records, error = parse_with_timeout(parser, page_file, year=pub_year, timeout_seconds=5)

            file_time = time.time() - file_start

            if error:
                logger.warning(f"  ⚠ {page_file.name[:60]}: {error}")
                stats['failed'] += 1
                stats['timeout_files'].append(page_file.name)
                continue  # Skip to next file

            logger.debug(f"  ✓ {page_file.name[:60]}: {len(records)} records in {file_time:.2f}s")

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
            logger.error(f"ERROR processing {page_file.name}: {e}", exc_info=True)
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
    logger.info("=" * 80)
    logger.info("TTJ BATCH PARSER - Multi-page aware")
    logger.info("=" * 80)
    logger.info("Grouping multi-page files...")
    file_groups = group_multipage_files(ocr_dir)

    total_files = sum(len(group) for group in file_groups)
    logger.info(f"Found {total_files} OCR files in {len(file_groups)} document groups")
    logger.info("=" * 80)

    all_records = []
    stats = {
        'total_files': total_files,
        'total_groups': len(file_groups),
        'processed': 0,
        'failed': 0,
        'timeout_files': [],  # Track files that timed out
        'total_records': 0,
        'records_with_port': 0,
        'records_with_date': 0,
    }

    # Create SINGLE parser for ALL files to preserve port context across document boundaries
    # This fixes issue where port sections span multiple document groups
    logger.info(">>> Creating parser instance...")
    parser = TTJContextParser()
    logger.info(">>> Parser created successfully")

    # Timing tracking
    start_time = time.time()
    last_checkpoint_time = start_time

    logger.info(">>> Starting processing loop...")
    # Process each group
    for group_idx, file_group in enumerate(file_groups, 1):
        group_name = file_group[0].name[:60]
        if len(file_group) > 1:
            group_name += f" (+{len(file_group)-1} pages)"

        # Process group
        group_start = time.time()
        records = process_file_group(parser, file_group, stats)
        all_records.extend(records)
        group_time = time.time() - group_start

        # Show progress every 10 groups
        if group_idx % 10 == 0 or group_idx == 1:
            elapsed = time.time() - start_time
            avg_time_per_group = elapsed / group_idx
            remaining_groups = len(file_groups) - group_idx
            eta_seconds = avg_time_per_group * remaining_groups
            eta_minutes = eta_seconds / 60

            log_and_flush(f"[{group_idx}/{len(file_groups)}] {group_name}")
            log_and_flush(f"  Records so far: {stats['total_records']:,} | This group: {len(records)} records in {group_time:.1f}s")
            log_and_flush(f"  Elapsed: {elapsed/60:.1f}m | Avg: {avg_time_per_group:.1f}s/group | ETA: {eta_minutes:.1f}m")

        # Incremental save every 50 groups (reduced to minimize memory usage)
        if group_idx % 50 == 0:
            checkpoint_time = time.time() - last_checkpoint_time
            logger.info(f"")
            logger.info(f">>> CHECKPOINT: Saving {len(all_records):,} records (last 50 groups took {checkpoint_time/60:.1f}m)...")

            checkpoint_csv = output_dir / f"ttj_shipments_checkpoint_{group_idx}.csv"
            with open(checkpoint_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
                    'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
                    'publication_day', 'publication_month', 'publication_year',
                    'is_steamship', 'format_type', 'confidence', 'raw_line'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_records)
            logger.info(f"    ✓ Checkpoint saved: {checkpoint_csv}")

            # CRITICAL: Clear memory after checkpoint
            logger.info(f"    ✓ Clearing {len(all_records):,} records from memory...")
            all_records.clear()

            last_checkpoint_time = time.time()

    # Save final batch (any remaining records not yet saved)
    logger.info(f"")
    logger.info(f">>> FINAL SAVE: Handling remaining records...")

    if all_records:
        # Save any records from the last incomplete batch
        final_batch_csv = output_dir / f"ttj_shipments_checkpoint_{len(file_groups)}.csv"
        logger.info(f"Writing {len(all_records):,} remaining records to {final_batch_csv.name}...")

        with open(final_batch_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
                'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
                'publication_day', 'publication_month', 'publication_year',
                'is_steamship', 'format_type', 'confidence', 'raw_line'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)
        logger.info(f"✓ Final batch saved: {final_batch_csv}")
    else:
        logger.info("No remaining records (last checkpoint covered everything)")

    # Merge all checkpoint files into one master CSV
    csv_file = output_dir / "ttj_shipments_multipage.csv"
    logger.info(f"")
    logger.info(f">>> MERGING CHECKPOINTS into {csv_file.name}...")

    checkpoint_files = sorted(output_dir.glob("ttj_shipments_checkpoint_*.csv"))
    if checkpoint_files:
        with open(csv_file, 'w', newline='', encoding='utf-8') as outfile:
            fieldnames = [
                'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
                'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
                'publication_day', 'publication_month', 'publication_year',
                'is_steamship', 'format_type', 'confidence', 'raw_line'
            ]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for i, checkpoint_file in enumerate(checkpoint_files):
                logger.info(f"  Merging {checkpoint_file.name}...")
                with open(checkpoint_file, 'r', newline='', encoding='utf-8') as infile:
                    reader = csv.DictReader(infile)
                    for row in reader:
                        writer.writerow(row)

        logger.info(f"✓ Merged {len(checkpoint_files)} checkpoint files into: {csv_file}")
    else:
        logger.warning("No checkpoint files found to merge!")

    # Save summary JSON
    summary_file = output_dir / "processing_summary_multipage.json"
    summary = {
        'timestamp': datetime.now().isoformat(),
        'statistics': stats,
        'timeout_files': stats['timeout_files'],
        'port_coverage': f"{100 * stats['records_with_port'] / max(1, stats['total_records']):.1f}%",
        'date_coverage': f"{100 * stats['records_with_date'] / max(1, stats['total_records']):.1f}%"
    }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"✓ Summary saved: {summary_file}")

    # Print final statistics
    total_time = time.time() - start_time
    logger.info("")
    logger.info("=" * 80)
    logger.info("BATCH PROCESSING COMPLETE (Multi-page aware)")
    logger.info("=" * 80)
    logger.info(f"Document groups: {stats['total_groups']}")
    logger.info(f"Files processed: {stats['processed']}/{stats['total_files']}")
    logger.info(f"Failed: {stats['failed']}")
    if stats['timeout_files']:
        logger.info(f"Timeout files: {len(stats['timeout_files'])} (see summary JSON for list)")
    logger.info(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    logger.info(f"")
    logger.info(f"Total ship records: {stats['total_records']:,}")
    logger.info(f"  With destination port: {stats['records_with_port']:,} ({100 * stats['records_with_port'] / max(1, stats['total_records']):.1f}%)")
    logger.info(f"  With arrival date: {stats['records_with_date']:,} ({100 * stats['records_with_date'] / max(1, stats['total_records']):.1f}%)")
    logger.info(f"")
    logger.info(f"Output files:")
    logger.info(f"  CSV: {csv_file}")
    logger.info(f"  Summary: {summary_file}")
    if stats['timeout_files']:
        logger.info(f"")
        logger.info(f"NOTE: {len(stats['timeout_files'])} files exceeded 5s timeout and were skipped")
        logger.info(f"      These can be processed separately with LLM assistance")
    logger.info("=" * 80)


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
