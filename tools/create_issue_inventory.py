#!/usr/bin/env python3
"""
Create comprehensive inventory of TTJ issues with OCR and parsing status.
"""
import os
import re
import csv
from pathlib import Path
from collections import defaultdict
import pandas as pd

# Paths
base_dir = Path("/home/jic823/TTJ Forest of Numbers")
ocr_dir = base_dir / "ocr_results" / "gemini_full"
failed_csv = base_dir / "failed_ocr_images.csv"
parsed_csv = base_dir / "parsed_output" / "ttj_shipments_multipage.csv"
extracted_dir = base_dir / "extracted_zips"

print("Creating TTJ issue inventory...")
print("=" * 80)

# Step 1: Get all OCR files and extract issue dates
print("\n1. Reading OCR files...")
ocr_issues = defaultdict(lambda: {'ocr_files': 0, 'ocr_pages': 0})

for txt_file in ocr_dir.glob("*.txt"):
    filename = txt_file.stem

    # Parse filename: YYYYMMDDp.NNN or YYYYMMDDp.NNN_pXXX
    match = re.match(r'(\d{4})(\d{2})(\d{2})p\.(\d+)', filename)
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        page = match.group(4)

        issue_key = f"{year}-{month}-{day}"
        ocr_issues[issue_key]['ocr_files'] += 1

        # Check if this is a multi-page file
        if '_p' in filename:
            ocr_issues[issue_key]['ocr_pages'] += 1
        else:
            ocr_issues[issue_key]['ocr_pages'] += 1

print(f"   Found {len(ocr_issues)} unique issues with OCR")

# Step 2: Get failed OCR attempts
print("\n2. Reading failed OCR list...")
failed_issues = defaultdict(list)

if failed_csv.exists():
    with open(failed_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['filename']
            # Parse image filename
            match = re.match(r'(\d{4})(\d{2})(\d{2})p\.(\d+)', filename)
            if match:
                year = match.group(1)
                month = match.group(2)
                day = match.group(3)
                issue_key = f"{year}-{month}-{day}"
                failed_issues[issue_key].append({
                    'filename': filename,
                    'error_type': row.get('error_type', 'UNKNOWN')
                })

print(f"   Found {len(failed_issues)} issues with failed OCR")

# Step 3: Get parsed ship counts by issue
print("\n3. Reading parsed shipments...")
parsed_by_issue = defaultdict(int)

if parsed_csv.exists():
    df = pd.read_csv(parsed_csv)

    # Group by source file and count
    for source_file in df['source_file'].unique():
        # Parse source filename
        match = re.match(r'(\d{4})(\d{2})(\d{2})p\.(\d+)', source_file)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            issue_key = f"{year}-{month}-{day}"

            # Count ships from this source file
            count = len(df[df['source_file'] == source_file])
            parsed_by_issue[issue_key] += count

print(f"   Found ship data for {len(parsed_by_issue)} issues")

# Step 4: Get unprocessed PDFs from extracted zips
print("\n4. Reading unprocessed PDFs...")
unprocessed_issues = defaultdict(int)

for pdf_path in extracted_dir.rglob("*.pdf"):
    if "__MACOSX" not in str(pdf_path):
        filename = pdf_path.name
        match = re.match(r'(\d{4})(\d{2})(\d{2})p\.(\d+)', filename)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            issue_key = f"{year}-{month}-{day}"
            unprocessed_issues[issue_key] += 1

print(f"   Found {len(unprocessed_issues)} unprocessed issues")

# Step 5: Combine all data
print("\n5. Combining data...")

# Get all unique issue dates
all_issues = set()
all_issues.update(ocr_issues.keys())
all_issues.update(failed_issues.keys())
all_issues.update(parsed_by_issue.keys())
all_issues.update(unprocessed_issues.keys())

print(f"   Total unique issues: {len(all_issues)}")

# Create output records
output = []

for issue_key in sorted(all_issues):
    year, month, day = issue_key.split('-')

    # OCR status
    has_ocr = issue_key in ocr_issues
    ocr_file_count = ocr_issues[issue_key]['ocr_files'] if has_ocr else 0
    ocr_page_count = ocr_issues[issue_key]['ocr_pages'] if has_ocr else 0

    # Failed status
    has_failed = issue_key in failed_issues
    failed_count = len(failed_issues[issue_key]) if has_failed else 0
    failed_errors = ', '.join(set([f['error_type'] for f in failed_issues[issue_key]])) if has_failed else ''

    # Parsed ships
    ship_count = parsed_by_issue.get(issue_key, 0)

    # Unprocessed PDFs
    unprocessed_count = unprocessed_issues.get(issue_key, 0)

    # Determine status
    if unprocessed_count > 0:
        status = "UNPROCESSED"
    elif has_failed and ocr_file_count == 0:
        status = "FAILED_ONLY"
    elif has_failed and ocr_file_count > 0:
        status = "PARTIAL_FAIL"
    elif has_ocr:
        status = "OCR_COMPLETE"
    else:
        status = "UNKNOWN"

    output.append({
        'issue_date': issue_key,
        'year': year,
        'month': month,
        'day': day,
        'status': status,
        'ocr_files': ocr_file_count,
        'ocr_pages': ocr_page_count,
        'failed_count': failed_count,
        'failed_errors': failed_errors,
        'ships_parsed': ship_count,
        'unprocessed_pdfs': unprocessed_count
    })

# Step 6: Save to CSV
output_file = base_dir / "ttj_issue_inventory.csv"
print(f"\n6. Saving to CSV...")

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['issue_date', 'year', 'month', 'day', 'status',
                  'ocr_files', 'ocr_pages', 'failed_count', 'failed_errors',
                  'ships_parsed', 'unprocessed_pdfs']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output)

print(f"✓ Saved to: {output_file}")

# Step 7: Print summary statistics
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)

df_out = pd.DataFrame(output)

print(f"\nTotal TTJ issues identified: {len(df_out)}")
print(f"\nBy status:")
for status in sorted(df_out['status'].unique()):
    count = len(df_out[df_out['status'] == status])
    print(f"  {status}: {count}")

print(f"\nBy year:")
year_counts = df_out.groupby('year').agg({
    'issue_date': 'count',
    'ships_parsed': 'sum',
    'ocr_files': 'sum',
    'failed_count': 'sum',
    'unprocessed_pdfs': 'sum'
}).rename(columns={'issue_date': 'issues'})

for year in sorted(year_counts.index):
    row = year_counts.loc[year]
    print(f"  {year}: {int(row['issues'])} issues, "
          f"{int(row['ships_parsed'])} ships, "
          f"{int(row['ocr_files'])} OCR files, "
          f"{int(row['failed_count'])} failed, "
          f"{int(row['unprocessed_pdfs'])} unprocessed")

print(f"\nTotal ships parsed: {df_out['ships_parsed'].sum():,}")
print(f"Total OCR files: {df_out['ocr_files'].sum():,}")
print(f"Total failed OCR: {df_out['failed_count'].sum():,}")
print(f"Total unprocessed PDFs: {df_out['unprocessed_pdfs'].sum():,}")

# Identify critical gaps (no OCR and no unprocessed)
gaps = df_out[(df_out['ocr_files'] == 0) & (df_out['unprocessed_pdfs'] == 0)]
if len(gaps) > 0:
    print(f"\n⚠️  CRITICAL GAPS (no OCR, no unprocessed PDFs): {len(gaps)} issues")
    print("   These issues are missing from our collection entirely")
    gap_years = gaps.groupby('year').size()
    for year, count in sorted(gap_years.items()):
        print(f"     {year}: {count} missing issues")

print("\n" + "=" * 80)
print(f"CSV saved to: {output_file}")
print("=" * 80)
