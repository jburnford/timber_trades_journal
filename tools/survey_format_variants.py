#!/usr/bin/env python3
"""
Survey OCR files to identify format variants across years.
Samples 4-5 files per year from 1874-1899 to document structural changes.
"""

import re
from pathlib import Path
from collections import defaultdict
import json


def extract_year_from_filename(filename: str) -> int:
    """Extract publication year from filename."""
    # Pattern 1: "YYYY" in filename
    match = re.search(r'(187[4-9]|188[0-9]|189[0-9])', filename)
    if match:
        return int(match.group(1))
    return None


def sample_files_by_year(ocr_dir: Path, samples_per_year: int = 5):
    """Sample OCR files stratified by year."""
    files_by_year = defaultdict(list)

    # Group all .txt files by year
    for txt_file in ocr_dir.glob("*.txt"):
        year = extract_year_from_filename(txt_file.name)
        if year:
            files_by_year[year].append(txt_file)

    # Sample from each year
    samples = {}
    for year in sorted(files_by_year.keys()):
        files = files_by_year[year]
        # Sample up to samples_per_year files
        sample_count = min(samples_per_year, len(files))
        # Spread samples across the year's files
        step = max(1, len(files) // sample_count)
        samples[year] = [files[i] for i in range(0, len(files), step)][:sample_count]

    return samples


def detect_format_signals(text: str) -> dict:
    """Detect key format signals in text."""
    signals = {}

    # Check for import section header variants
    signals['has_import_header'] = bool(re.search(r'Imports? of Timber', text, re.I))
    signals['has_imports_caps'] = bool(re.search(r'^IMPORTS\.?\s*$', text, re.M))

    # Check for delimiter types
    signals['uses_at_delimiter'] = '@' in text
    signals['uses_dash_delimiter'] = bool(re.search(r'\s+-\s+', text))

    # Check for port headers (all caps with period)
    port_headers = re.findall(r'^([A-Z\s&\.\'\(\)]+)\.\s*$', text, re.M)
    signals['port_headers'] = port_headers[:10]  # First 10 for sample
    signals['port_header_count'] = len(port_headers)

    # Check for date patterns at start of line
    signals['has_date_prefix'] = bool(re.search(r'^\w{3,4}\.\s+\d{1,2}\s+', text, re.M))
    signals['has_numeric_date'] = bool(re.search(r'^\d{1,2}\s+[A-Z]', text, re.M))

    # Check for steamship markers
    signals['has_steamship_marker'] = '(s)' in text

    # Check for dock subdivisions (London specific)
    signals['has_dock_subdivisions'] = bool(re.search(r'(SURREY COMMERCIAL DOCKS|MILLWALL DOCKS|TILBURY)', text))

    # Check for compressed format (just commodity-merchant)
    signals['has_compressed_format'] = bool(re.search(r'—\w+[-,]\w+', text))

    # Sample a few records to show structure
    # Look for lines with ship-like patterns
    sample_records = []
    for line in text.split('\n')[:200]:  # Check first 200 lines
        line = line.strip()
        # Match patterns like: "Date Ship @ Origin,—cargo"
        if re.match(r'^(\w+\.\s+)?\d{1,2}\s+\w+.*[@—]', line):
            sample_records.append(line[:150])  # Truncate long lines
            if len(sample_records) >= 5:
                break
    signals['sample_records'] = sample_records

    return signals


def analyze_sample(sample_file: Path) -> dict:
    """Analyze a single OCR file for format characteristics."""
    with open(sample_file, 'r', encoding='utf-8') as f:
        text = f.read()

    analysis = {
        'filename': sample_file.name,
        'file_size': len(text),
        'line_count': text.count('\n'),
        'signals': detect_format_signals(text)
    }

    return analysis


def main():
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")
    output_file = Path("/home/jic823/TTJ Forest of Numbers/tools/format_survey_results.json")

    print("Surveying OCR files for format variants...")
    print("=" * 70)

    # Sample files by year
    samples = sample_files_by_year(ocr_dir, samples_per_year=5)

    print(f"\nFound files spanning {min(samples.keys())} to {max(samples.keys())}")
    print(f"Total years: {len(samples)}")
    print(f"Total samples: {sum(len(files) for files in samples.values())}")
    print()

    # Analyze each sample
    results = {}
    total_samples = sum(len(files) for files in samples.values())
    current = 0

    for year in sorted(samples.keys()):
        year_results = []
        for sample_file in samples[year]:
            current += 1
            print(f"[{current}/{total_samples}] Analyzing {sample_file.name[:60]}...")
            analysis = analyze_sample(sample_file)
            year_results.append(analysis)

        results[year] = year_results

        # Print summary for year
        print(f"\n  Year {year} summary:")
        print(f"    Port headers: {sum(r['signals']['port_header_count'] for r in year_results)} total")
        print(f"    Uses @ delimiter: {sum(1 for r in year_results if r['signals']['uses_at_delimiter'])}/{len(year_results)}")
        print(f"    Uses - delimiter: {sum(1 for r in year_results if r['signals']['uses_dash_delimiter'])}/{len(year_results)}")
        print(f"    Has date prefix: {sum(1 for r in year_results if r['signals']['has_date_prefix'])}/{len(year_results)}")
        print()

    # Save detailed results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print(f"Survey complete! Results saved to: {output_file}")
    print(f"\nAnalyzed {total_samples} files across {len(samples)} years")

    # Print format evolution summary
    print("\nFormat Evolution Summary:")
    print("-" * 70)
    for year in sorted(samples.keys()):
        at_count = sum(1 for r in results[year] if r['signals']['uses_at_delimiter'])
        dash_count = sum(1 for r in results[year] if r['signals']['uses_dash_delimiter'])
        dock_count = sum(1 for r in results[year] if r['signals']['has_dock_subdivisions'])

        format_type = "MIXED"
        if at_count > dash_count:
            format_type = "AT-DELIMITER"
        elif dash_count > 0:
            format_type = "DASH-DELIMITER"

        if dock_count > 0:
            format_type += " + DOCK-SUBS"

        print(f"{year}: {format_type} (@ in {at_count}/{len(results[year])}, - in {dash_count}/{len(results[year])})")


if __name__ == '__main__':
    main()
