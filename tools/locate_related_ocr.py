#!/usr/bin/env python3
"""
Phase 1.2: Locate all OCR files related to failed pages.
For each failed page date, find ALL OCR files from that same publication date.
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def normalize_date(date_str):
    """Convert various date formats to YYYYMMDD for comparison."""
    # Try multiple formats
    formats = [
        "%B %d, %Y",    # "May 2, 1874"
        "%b %d, %Y",    # "May 2, 1874"
        "%Y%m%d"        # "18740502"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y%m%d")
        except:
            continue

    return None

def extract_date_from_path(filepath):
    """Extract publication date from OCR filepath."""
    filename = Path(filepath).name

    # Pattern 1: "May 2 1874" format
    date_pattern1 = r'(\w+)\s+(\d{1,2})\s+(187\d|188\d|189\d)'
    match = re.search(date_pattern1, filename)
    if match:
        month, day, year = match.groups()
        try:
            dt = datetime.strptime(f"{month} {day} {year}", "%B %d %Y")
            return dt.strftime("%Y%m%d")
        except:
            try:
                dt = datetime.strptime(f"{month} {day} {year}", "%b %d %Y")
                return dt.strftime("%Y%m%d")
            except:
                pass

    # Pattern 2: YYYYMMDD format (1881 files)
    date_pattern2 = r'(18\d{2})(\d{2})(\d{2})'
    match = re.search(date_pattern2, filename)
    if match:
        year, month, day = match.groups()
        return f"{year}{month}{day}"

    return None

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    manifest_path = base_dir / "analysis" / "polaris_recovery_manifest.json"
    ocr_results_dir = base_dir / "ocr_results"
    output_dir = base_dir / "analysis"

    print("=" * 80)
    print("PHASE 1.2: LOCATE RELATED OCR FILES")
    print("=" * 80)
    print()

    # Load manifest from Phase 1.1
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # Get all affected dates
    affected_dates = {}
    for date_str, pages in manifest['pages_by_date'].items():
        norm_date = normalize_date(date_str)
        if norm_date:
            affected_dates[norm_date] = {
                'date_str': date_str,
                'failed_pages': pages,
                'gemini_ocr_files': [],
                'polaris_ocr_files': []
            }

    print(f"Affected dates: {len(affected_dates)}")
    print()

    # Scan Gemini OCR directories
    print("Scanning Gemini OCR directories...")
    gemini_dirs = [
        ocr_results_dir / "gemini_full",
        ocr_results_dir / "gemini_512"
    ]

    for gemini_dir in gemini_dirs:
        if gemini_dir.exists():
            print(f"  Scanning: {gemini_dir.name}")
            for txt_file in gemini_dir.glob("*.txt"):
                file_date = extract_date_from_path(txt_file)
                if file_date and file_date in affected_dates:
                    affected_dates[file_date]['gemini_ocr_files'].append(str(txt_file))

    # Scan Polaris Alpha OCR directory
    print("Scanning Polaris Alpha OCR directory...")
    polaris_dir = ocr_results_dir / "polaris_alpha"
    if polaris_dir.exists():
        for txt_file in polaris_dir.glob("*_polaris.txt"):
            file_date = extract_date_from_path(txt_file)
            if file_date and file_date in affected_dates:
                affected_dates[file_date]['polaris_ocr_files'].append(str(txt_file))

    print()

    # Generate summary
    print("=" * 80)
    print("OCR FILE MAPPING SUMMARY")
    print("=" * 80)
    print()

    total_gemini = 0
    total_polaris = 0
    dates_with_no_gemini = 0
    dates_with_no_polaris = 0

    for norm_date in sorted(affected_dates.keys()):
        info = affected_dates[norm_date]
        gemini_count = len(info['gemini_ocr_files'])
        polaris_count = len(info['polaris_ocr_files'])
        failed_count = len(info['failed_pages'])

        total_gemini += gemini_count
        total_polaris += polaris_count

        if gemini_count == 0:
            dates_with_no_gemini += 1
        if polaris_count == 0:
            dates_with_no_polaris += 1

        print(f"{info['date_str']:25} | Failed: {failed_count} | Gemini: {gemini_count} | Polaris: {polaris_count}")

    print()
    print(f"Total Gemini OCR files: {total_gemini}")
    print(f"Total Polaris OCR files: {total_polaris}")
    print(f"Dates with no Gemini OCR: {dates_with_no_gemini}")
    print(f"Dates with no Polaris recovery: {dates_with_no_polaris}")
    print()

    # Save enhanced manifest
    output_manifest = {
        'generated': datetime.now().isoformat(),
        'total_affected_dates': len(affected_dates),
        'total_gemini_files': total_gemini,
        'total_polaris_files': total_polaris,
        'dates': {}
    }

    for norm_date, info in affected_dates.items():
        output_manifest['dates'][norm_date] = {
            'date_str': info['date_str'],
            'failed_pages': info['failed_pages'],
            'gemini_ocr_files': sorted(info['gemini_ocr_files']),
            'polaris_ocr_files': sorted(info['polaris_ocr_files']),
            'counts': {
                'failed': len(info['failed_pages']),
                'gemini': len(info['gemini_ocr_files']),
                'polaris': len(info['polaris_ocr_files'])
            }
        }

    output_path = output_dir / "polaris_ocr_mapping.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_manifest, f, indent=2, ensure_ascii=False)

    print(f"OCR mapping saved to: {output_path}")
    print()

    # Warning summary
    if dates_with_no_gemini > 0:
        print(f"WARNING: {dates_with_no_gemini} dates have NO Gemini OCR files!")
        print("  These dates may not be in the current database.")

    if dates_with_no_polaris > 0:
        print(f"WARNING: {dates_with_no_polaris} dates have NO Polaris recovery!")
        print("  These were the 2 failed Polaris OCR attempts.")

    return output_manifest

if __name__ == '__main__':
    manifest = main()
