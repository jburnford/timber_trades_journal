#!/usr/bin/env python3
"""
Parse the 6 files that timed out in initial batch run.
Uses longer timeout (30s) to handle complex formatting.
"""
import csv
import sys
import time
import signal
from pathlib import Path
from ttj_parser_v3 import TTJContextParser, extract_publication_date_from_filename

csv.field_size_limit(10 * 1024 * 1024)

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Parser exceeded timeout")

def parse_with_timeout(parser, file_path, year, timeout_seconds=30):
    """Parse with extended timeout."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        records = parser.parse_file(file_path, year=year)
        signal.alarm(0)
        return records, None
    except TimeoutError:
        signal.alarm(0)
        return [], f"TIMEOUT after {timeout_seconds}s"
    except Exception as e:
        signal.alarm(0)
        return [], f"ERROR: {str(e)}"

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    flat_dir = base_dir / "ocr_results" / "hybrid_recovery_flat"
    output_dir = base_dir / "parsed_output" / "polaris_recovery"

    # The 6 timeout files
    timeout_files = [
        "18740502_1. p. 6 a╠Ç 8 - May 2 1874 - Imports of Timber, &c. - Timber Trades Journal Vol. 2 1875_p003_polaris_polaris.txt",
        "18741212_17. p. 253-255 - December 12 1874 - Imports of Timber, &c. - Timber Trades Journal Vol. 2 1875_p001_polaris_polaris.txt",
        "18771110_15. 236-239 - November 10 1877 - Imports of Timber, &c. - Timber Trades Journal Vol. 5 1877_p004_gemini.txt",
        "18810723_18810723p.64_p001_gemini.txt",
        "18811217_18811217p.403_p003_gemini.txt",
        "18850502_18. p. 318-320 - Imports - May 2 1885 - Timber Trades Journal 1885_p003_gemini.txt"
    ]

    print("=" * 80)
    print("PARSING TIMEOUT FILES (Extended Timeout: 30s)")
    print("=" * 80)
    print(f"Files to process: {len(timeout_files)}")
    print()

    parser = TTJContextParser()
    all_records = []
    stats = {
        'processed': 0,
        'failed': 0,
        'total_records': 0
    }

    for i, filename in enumerate(timeout_files, 1):
        file_path = flat_dir / filename
        if not file_path.exists():
            print(f"[{i}/6] ⚠ NOT FOUND: {filename[:60]}...")
            stats['failed'] += 1
            continue

        print(f"[{i}/6] Processing: {filename[:60]}...")

        # Extract publication date
        pub_year, pub_month, pub_day = extract_publication_date_from_filename(filename)

        # Parse with 30s timeout
        start_time = time.time()
        records, error = parse_with_timeout(parser, file_path, year=pub_year, timeout_seconds=30)
        elapsed = time.time() - start_time

        if error:
            print(f"      ❌ {error} ({elapsed:.1f}s)")
            stats['failed'] += 1
        else:
            print(f"      ✓ {len(records)} records in {elapsed:.1f}s")
            stats['processed'] += 1
            stats['total_records'] += len(records)

            # Convert to dict format
            for record in records:
                all_records.append({
                    'source_file': filename,
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

    print()
    print("=" * 80)
    print("TIMEOUT FILES PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Successfully processed: {stats['processed']}/6")
    print(f"Failed: {stats['failed']}/6")
    print(f"Total records recovered: {stats['total_records']:,}")
    print()

    if all_records:
        # Save recovered records
        output_csv = output_dir / "ttj_shipments_timeout_recovered.csv"
        fieldnames = [
            'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
            'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
            'publication_day', 'publication_month', 'publication_year',
            'is_steamship', 'format_type', 'confidence', 'raw_line'
        ]

        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)

        print(f"✓ Saved recovered records to: {output_csv}")
        print()
        print("Next: Merge this file with ttj_shipments_multipage.csv before final merge")
    else:
        print("No records recovered from timeout files")

    return stats

if __name__ == '__main__':
    stats = main()
