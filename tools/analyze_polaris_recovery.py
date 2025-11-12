#!/usr/bin/env python3
"""
Phase 1.1: Analyze Polaris Alpha OCR recovery - create manifest of failed pages and dates.
"""
import csv
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def extract_date_from_filename(filename):
    """Extract publication date from filename."""
    # Pattern: "May 29 1875" or "May 2 1874" etc
    date_pattern = r'(\w+)\s+(\d{1,2})\s+(187\d|188\d|189\d)'
    match = re.search(date_pattern, filename)

    if match:
        month_str, day_str, year_str = match.groups()
        try:
            # Parse to get standardized format
            date_obj = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
            return {
                'date_str': f"{month_str} {day_str}, {year_str}",
                'year': int(year_str),
                'month': date_obj.month,
                'day': int(day_str),
                'month_name': month_str,
                'sort_key': date_obj.strftime('%Y%m%d')
            }
        except ValueError:
            # Try short month names
            try:
                date_obj = datetime.strptime(f"{month_str} {day_str} {year_str}", "%b %d %Y")
                return {
                    'date_str': f"{month_str} {day_str}, {year_str}",
                    'year': int(year_str),
                    'month': date_obj.month,
                    'day': int(day_str),
                    'month_name': month_str,
                    'sort_key': date_obj.strftime('%Y%m%d')
                }
            except:
                pass

    # Try YYYYMMDD pattern (1881 files)
    date_pattern2 = r'(18\d{2})(\d{2})(\d{2})'
    match2 = re.search(date_pattern2, filename)
    if match2:
        year, month, day = match2.groups()
        try:
            date_obj = datetime.strptime(f"{year}{month}{day}", "%Y%m%d")
            return {
                'date_str': date_obj.strftime("%B %d, %Y"),
                'year': int(year),
                'month': int(month),
                'day': int(day),
                'month_name': date_obj.strftime("%B"),
                'sort_key': f"{year}{month}{day}"
            }
        except:
            pass

    return None

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    failed_csv = base_dir / "failed_ocr_images.csv"
    polaris_dir = base_dir / "ocr_results" / "polaris_alpha"
    output_dir = base_dir / "analysis"
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("PHASE 1.1: POLARIS ALPHA RECOVERY ANALYSIS")
    print("=" * 80)
    print()

    # Read failed images
    failed_pages = []
    with open(failed_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['error_type'] in ('MAX_TOKENS', 'COPYRIGHT'):
                failed_pages.append(row)

    print(f"Total failed pages to analyze: {len(failed_pages)}")
    print(f"  MAX_TOKENS: {sum(1 for p in failed_pages if p['error_type'] == 'MAX_TOKENS')}")
    print(f"  COPYRIGHT: {sum(1 for p in failed_pages if p['error_type'] == 'COPYRIGHT')}")
    print()

    # Extract dates and group
    pages_by_date = defaultdict(list)
    pages_by_year = defaultdict(list)
    pages_without_date = []

    for page in failed_pages:
        filename = page['filename']
        date_info = extract_date_from_filename(filename)

        if date_info:
            page['date_info'] = date_info
            pages_by_date[date_info['date_str']].append(page)
            pages_by_year[date_info['year']].append(page)
        else:
            pages_without_date.append(page)
            print(f"WARNING: Could not extract date from: {filename}")

    print(f"Pages with dates extracted: {sum(len(p) for p in pages_by_date.values())}")
    print(f"Pages without dates: {len(pages_without_date)}")
    print()

    # Summary by year
    print("=" * 80)
    print("FAILED PAGES BY YEAR")
    print("=" * 80)
    for year in sorted(pages_by_year.keys()):
        pages = pages_by_year[year]
        print(f"{year}: {len(pages)} pages")
        for page in sorted(pages, key=lambda x: x['date_info']['sort_key']):
            print(f"  - {page['date_info']['date_str']}: {page['filename'][:60]}...")
    print()

    # Create manifest
    manifest = {
        'generated': datetime.now().isoformat(),
        'total_pages': len(failed_pages),
        'total_dates': len(pages_by_date),
        'pages_by_date': {},
        'pages_by_year': {},
        'summary': {
            'years_affected': sorted(list(pages_by_year.keys())),
            'date_range': {
                'earliest': min(p['date_info']['sort_key'] for p in failed_pages if 'date_info' in p),
                'latest': max(p['date_info']['sort_key'] for p in failed_pages if 'date_info' in p)
            }
        }
    }

    # Add detailed page info
    for date_str, pages in pages_by_date.items():
        manifest['pages_by_date'][date_str] = []
        for page in pages:
            manifest['pages_by_date'][date_str].append({
                'filename': page['filename'],
                'full_path': page['full_path'],
                'error_type': page['error_type'],
                'year': page['date_info']['year'],
                'month': page['date_info']['month'],
                'day': page['date_info']['day']
            })

    for year, pages in pages_by_year.items():
        manifest['pages_by_year'][str(year)] = len(pages)

    # Save manifest
    manifest_path = output_dir / "polaris_recovery_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest saved to: {manifest_path}")

    # Create simple date list for next phase
    dates_list_path = output_dir / "polaris_affected_dates.txt"
    with open(dates_list_path, 'w', encoding='utf-8') as f:
        for date_str in sorted(pages_by_date.keys(), key=lambda d: pages_by_date[d][0]['date_info']['sort_key']):
            f.write(f"{date_str}\n")

    print(f"Date list saved to: {dates_list_path}")
    print()

    # Summary statistics
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Unique publication dates affected: {len(pages_by_date)}")
    print(f"Years covered: {min(pages_by_year.keys())} - {max(pages_by_year.keys())}")
    print(f"Average pages per date: {len(failed_pages) / len(pages_by_date):.1f}")
    print()

    return manifest

if __name__ == '__main__':
    manifest = main()
