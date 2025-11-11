#!/usr/bin/env python3
"""
Reparse 1874-1875 files DATE BY DATE with improved multi-ship parser.
Process one publication date at a time to avoid timeouts.
Then replace those records in the existing database.
"""

import csv
import sys
import signal
from pathlib import Path
from collections import defaultdict
from ttj_parser_v3 import TTJContextParser, extract_publication_date_from_filename

csv.field_size_limit(1000000)


class TimeoutError(Exception):
    """Raised when a file takes too long to process."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("File processing timed out")


def parse_file_with_timeout(parser, file_path, timeout_seconds=10):
    """
    Parse a file with a timeout.

    Args:
        parser: TTJContextParser instance
        file_path: Path to file
        timeout_seconds: Maximum seconds to allow

    Returns:
        List of records, or None if timeout

    Raises:
        TimeoutError: If parsing exceeds timeout
    """
    # Set up the timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)

    try:
        records = parser.parse_file(file_path)
        signal.alarm(0)  # Cancel the alarm
        return records
    except TimeoutError:
        signal.alarm(0)  # Cancel the alarm
        raise
    except Exception as e:
        signal.alarm(0)  # Cancel the alarm
        raise


def group_files_by_date(ocr_dir: Path):
    """Group 1874-1875 files by publication date."""
    all_files = sorted(ocr_dir.glob("*.txt"))

    # Group by (year, month, day)
    files_by_date = defaultdict(list)

    for file_path in all_files:
        year, month, day = extract_publication_date_from_filename(file_path.name)
        if year in (1874, 1875):
            date_key = (year, month, day)
            files_by_date[date_key].append(file_path)

    # Sort by date
    sorted_dates = sorted(files_by_date.keys())

    return files_by_date, sorted_dates


def parse_by_date(ocr_dir: Path, output_csv: Path):
    """Parse files one date at a time, saving incrementally."""

    files_by_date, sorted_dates = group_files_by_date(ocr_dir)

    print(f"Found {len(sorted_dates)} unique publication dates in 1874-1875")
    print(f"Total files to process: {sum(len(files) for files in files_by_date.values())}")
    print()

    # Open output CSV for incremental writing
    fieldnames = [
        'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
        'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
        'publication_day', 'publication_month', 'publication_year',
        'is_steamship', 'format_type', 'confidence', 'raw_line'
    ]

    total_records = 0

    with open(output_csv, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for i, date_key in enumerate(sorted_dates, 1):
            year, month, day = date_key

            # Format date string for display (month may be name or number)
            if day:
                date_str = f"{year} {month} {day}"
            else:
                date_str = f"{year} {month}"

            files = files_by_date[date_key]

            print(f"[{i}/{len(sorted_dates)}] Processing {date_str} ({len(files)} file(s))...")

            # Parse files for this date
            parser = TTJContextParser()  # Fresh parser for each date
            date_records = 0

            for file_path in files:
                try:
                    # Parse with 10 second timeout per file
                    records = parse_file_with_timeout(parser, file_path, timeout_seconds=10)

                    # Write records immediately
                    for record in records:
                        writer.writerow({
                            'source_file': file_path.name,
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
                        date_records += 1

                except TimeoutError:
                    print(f"  ⚠ TIMEOUT: {file_path.name} (skipped after 10s)")
                    continue
                except Exception as e:
                    print(f"  ERROR processing {file_path.name}: {e}")
                    continue

            total_records += date_records
            print(f"  → {date_records} records (running total: {total_records:,})")

            # Flush after each date to ensure data is saved
            f_out.flush()

    print()
    print(f"✓ Parsing complete: {total_records:,} records written to {output_csv}")

    return total_records


def replace_in_database(new_records_csv: Path, existing_db: Path, output_db: Path):
    """Replace 1874-1875 records in existing database with newly parsed records."""

    print()
    print("=" * 80)
    print("REPLACING 1874-1875 RECORDS IN DATABASE")
    print("=" * 80)
    print()

    # Read existing database
    print(f"Reading existing database: {existing_db}")
    with open(existing_db, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing_records = list(reader)

    print(f"  Existing total: {len(existing_records):,} records")

    # Count existing 1874-1875 records
    old_1874_1875 = [r for r in existing_records
                     if r['publication_year'] in ('1874', '1875')]

    print(f"  Existing 1874-1875: {len(old_1874_1875):,} records")

    # Define standard fieldnames (exclude extra fields like raw_line_char_count)
    fieldnames = [
        'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
        'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
        'publication_day', 'publication_month', 'publication_year',
        'is_steamship', 'format_type', 'confidence', 'raw_line'
    ]

    # Filter out old 1874-1875 records and normalize to standard fields
    other_records = []
    for r in existing_records:
        if r['publication_year'] not in ('1874', '1875'):
            # Normalize to only include standard fields
            normalized = {k: r.get(k, '') for k in fieldnames}
            other_records.append(normalized)

    print(f"  Records from other years: {len(other_records):,}")
    print()

    # Read new 1874-1875 records
    print(f"Reading new 1874-1875 records: {new_records_csv}")
    with open(new_records_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        new_records = list(reader)

    print(f"  New 1874-1875: {len(new_records):,} records")
    print()

    # Show comparison
    print("=" * 60)
    print("COMPARISON:")
    print("=" * 60)
    print(f"Old 1874-1875: {len(old_1874_1875):,} records")
    print(f"New 1874-1875: {len(new_records):,} records")
    print(f"Difference: {len(new_records) - len(old_1874_1875):+,} records")

    if len(old_1874_1875) > 0:
        pct_change = ((len(new_records) - len(old_1874_1875)) / len(old_1874_1875)) * 100
        print(f"Change: {pct_change:+.1f}%")
    print()

    # Combine records
    combined_records = other_records + new_records
    combined_records.sort(key=lambda x: (
        x['publication_year'],
        x['publication_month'],
        x['publication_day'],
        x['source_file'],
        x.get('line_number', 0)
    ))

    print(f"Final database size: {len(combined_records):,} records")
    print()

    # Write new database
    print(f"Writing updated database to: {output_db}")
    with open(output_db, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined_records)

    print("✓ Database updated!")
    print()

    return len(old_1874_1875), len(new_records), len(combined_records)


def main():
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    existing_db = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final_v2.csv")
    temp_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/1874_1875_reparsed_temp.csv")
    output_db = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final_v3_1874_1875_fixed.csv")

    print("=" * 80)
    print("REPARSE 1874-1875 WITH IMPROVED MULTI-SHIP PARSER (DATE-BY-DATE)")
    print("=" * 80)
    print()

    # Step 1: Parse files date by date
    print("STEP 1: PARSING FILES BY DATE")
    print("-" * 80)
    new_record_count = parse_by_date(ocr_dir, temp_csv)

    if new_record_count == 0:
        print("ERROR: No records parsed!")
        return 1

    # Step 2: Replace in database
    print()
    print("STEP 2: REPLACING RECORDS IN DATABASE")
    print("-" * 80)
    old_count, new_count, final_count = replace_in_database(
        temp_csv, existing_db, output_db
    )

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Old 1874-1875 records: {old_count:,}")
    print(f"New 1874-1875 records: {new_count:,}")
    print(f"Improvement: {new_count - old_count:+,} records ({((new_count - old_count) / old_count * 100):+.1f}%)")
    print()
    print(f"Final database: {final_count:,} records")
    print(f"Output: {output_db}")
    print()
    print(f"Temporary file: {temp_csv}")
    print("  (You can delete this after verifying the results)")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
