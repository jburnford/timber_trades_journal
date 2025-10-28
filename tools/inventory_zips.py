#!/usr/bin/env python3
"""
Inventory extracted zip files and identify what needs processing.
"""
import os
import re
from pathlib import Path
import csv

# Paths
base_dir = Path("/home/jic823/TTJ Forest of Numbers")
extracted_dir = base_dir / "extracted_zips"
ocr_dir = base_dir / "ocr_results" / "gemini_full"
failed_csv = base_dir / "failed_ocr_images.csv"

# Find all PDFs
pdfs = []
for pdf_path in extracted_dir.rglob("*.pdf"):
    if "__MACOSX" not in str(pdf_path):
        pdfs.append(pdf_path)

print(f"Found {len(pdfs)} PDFs in extracted zips")
print()

# Extract basenames and years
pdf_info = []
for pdf in sorted(pdfs):
    filename = pdf.name
    # Extract year from filename (18yymmdd format)
    match = re.match(r'(\d{4})(\d{2})(\d{2})p\.(.*?)\.pdf', filename)
    if match:
        year = match.group(1)
        pdf_info.append({
            'path': str(pdf),
            'filename': filename,
            'year': year
        })

# Group by year
years = {}
for info in pdf_info:
    year = info['year']
    if year not in years:
        years[year] = []
    years[year].append(info)

print("PDFs by year:")
for year in sorted(years.keys()):
    print(f"  {year}: {len(years[year])} PDFs")
print()

# Check existing OCR
existing_ocr = set()
for txt_file in ocr_dir.glob("*.txt"):
    # Remove extension and page suffix
    basename = txt_file.stem
    # Remove _pNNN suffix if present
    basename = re.sub(r'_p\d{3}$', '', basename)
    existing_ocr.add(basename)

print(f"Existing OCR files: {len(list(ocr_dir.glob('*.txt')))} text files")
print(f"Unique base documents: {len(existing_ocr)}")
print()

# Check failed OCR
failed_images = set()
if failed_csv.exists():
    with open(failed_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            failed_images.add(row['filename'])
    print(f"Failed OCR images: {len(failed_images)}")
print()

# Identify unprocessed PDFs
# These are PDFs where we don't have OCR yet
unprocessed = []
for info in pdf_info:
    # Get base filename without .pdf extension
    base = info['filename'].replace('.pdf', '')

    # Check if we have OCR for this (exact match or with page suffixes)
    has_ocr = False
    for ocr_base in existing_ocr:
        if ocr_base.startswith(base):
            has_ocr = True
            break

    if not has_ocr:
        unprocessed.append(info)

print(f"\nUNPROCESSED PDFs (need OCR with Gemini 2.5 Pro):")
print(f"Total: {len(unprocessed)}")
if unprocessed:
    years_unprocessed = {}
    for info in unprocessed:
        year = info['year']
        if year not in years_unprocessed:
            years_unprocessed[year] = []
        years_unprocessed[year].append(info['filename'])

    for year in sorted(years_unprocessed.keys()):
        print(f"  {year}: {len(years_unprocessed[year])} PDFs")

    # Save to file
    output_file = base_dir / "unprocessed_pdfs_list.txt"
    with open(output_file, 'w') as f:
        for info in sorted(unprocessed, key=lambda x: x['filename']):
            f.write(f"{info['path']}\n")
    print(f"\nSaved list to: {output_file}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total PDFs extracted: {len(pdfs)}")
print(f"Existing OCR files: {len(existing_ocr)} base documents")
print(f"Failed OCR images: {len(failed_images)}")
print(f"Unprocessed PDFs needing Gemini 2.5 Pro: {len(unprocessed)}")
print()
print("Next steps:")
print("1. Convert unprocessed PDFs to images")
print("2. Process with Gemini 2.5 Pro OCR")
print("3. Select 10 test images (7 failed + 3 successful) for GPT-4o comparison")
