# Zip File Inventory Report

**Date**: January 27, 2025
**Purpose**: Catalog newly extracted PDFs and identify OCR processing needs

---

## Extraction Summary

### Zip Files Processed
1. **`The Timber Trades Journal - July to December.zip`** (420MB)
   - Location: 1897 data
   - Sections: London Section + Scotland Section
   - PDFs extracted: 52

2. **`The Timber Trades Journal 1895 vol. 38 2.zip`** (371MB)
   - Location: 1895 data
   - Section: Scotch Section
   - PDFs extracted: 49

**Total PDFs extracted**: 101 (49 from 1895, 52 from 1897)

---

## Current OCR Status

### Existing OCR Coverage
- **OCR text files**: 1,866 files
- **Unique documents**: 826 base documents
- **Coverage**: 1874-1899 (incomplete, with gaps)

### Failed OCR Images (from previous processing)
- **Total failed**: 45 images
- **Failure types**:
  - MAX_TOKENS: 35 files
  - COPYRIGHT: 5 files
  - OTHER: 5 files
- **Years affected**: 1875 (15), 1877 (8), 1881 (8), 1885 (10), 1887 (3)

---

## Unprocessed PDFs Identified

**Total unprocessed**: 101 PDFs (ALL files from extracted zips)

### Breakdown by Year
- **1895**: 49 PDFs (Scotch Section)
- **1897**: 52 PDFs (London + Scotland Sections)

**Finding**: None of the PDFs in these zip files have been OCR processed yet.

---

## OCR Processing Plan

### Phase 1: Convert PDFs to Images (101 PDFs)
These PDFs need to be converted to images before OCR can be applied.

**Tools available**:
- `process_pdf_for_ocr.py` - Existing preprocessing script
- Converts PDF → PNG at 300 DPI
- Applies rotation correction and OCR enhancements

**Action**: Run PDF → image conversion for all 101 PDFs

---

### Phase 2: Process with Gemini 2.5 Pro (NEW images)
Once converted, process the 101 new images with Gemini OCR.

**Method**: Use existing `gemini_ocr_processor.py`
**Model**: Gemini 2.5 Pro Vision
**Expected output**: ~101 text files (may be more if multi-page PDFs)

---

### Phase 3: GPT-4o Comparison Testing (10 images)
To evaluate alternative OCR for failed images.

**Test set composition**:
- 7 images that failed Gemini OCR (from `failed_ocr_images.csv`)
- 3 images that succeeded with Gemini (for quality comparison)

**Purpose**: Determine if GPT-4o can handle images that failed with Gemini

---

### Phase 4: Process Failed Images (45 images)
Based on GPT-4o test results, decide:
- If GPT-4o succeeds: Process all 45 failed images with GPT-4o
- If GPT-4o also fails: Try alternative OCR (Tesseract, Azure)

---

## Expected Impact

### Current London Cargo Records
- **Current**: 14,217 London cargo records (26 years)
- **Target**: ~130,000-150,000 (full coverage)

### After Processing New Images
**1897 data (52 PDFs)**: Expected to add 2,000-5,000 London cargo records
- London Section explicitly included in zip
- July-December 1897 period

**1895 data (49 PDFs)**: Expected to add 1,500-4,000 records
- Scotch Section (Glasgow, Leith, Grangemouth, etc.)
- May include London imports at Scottish ports

**Failed images (45 files)**: Expected to add 500-1,500 records
- Scattered across multiple years
- Quality depends on OCR success rate

**Total expected addition**: 4,000-10,000 cargo records

---

## File Locations

### Extracted PDFs
- `/home/jic823/TTJ Forest of Numbers/extracted_zips/zip1_july_december/`
- `/home/jic823/TTJ Forest of Numbers/extracted_zips/zip2_1895_vol38/`

### Unprocessed PDF List
- `/home/jic823/TTJ Forest of Numbers/unprocessed_pdfs_list.txt`

### Failed OCR Images
- `/home/jic823/TTJ Forest of Numbers/failed_ocr_images.csv`

### OCR Output Directory
- `/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full/`

---

## Next Steps (Priority Order)

1. **Convert 101 PDFs to images** (1-2 hours processing time)
2. **Process new images with Gemini 2.5 Pro** (4-6 hours, API costs)
3. **Select 10 test images** (7 failed + 3 successful)
4. **Run GPT-4o test** (cost: ~$0.10-0.20 for 10 images)
5. **Evaluate results** and decide on failed image strategy
6. **Process remaining failed images** with best-performing OCR
7. **Run complete pipeline** on expanded dataset:
   - Parsing (ttj_parser_v3.py with bug fixes)
   - Deduplication
   - Port normalization
   - Cargo normalization
8. **Validate final London cargo counts** against human transcription

---

## Cost Estimates

### Gemini 2.5 Pro (101 new images)
- **Rate**: ~$0.002-0.004 per image (estimated)
- **Total**: $0.20-0.40

### GPT-4o Testing (10 images)
- **Rate**: ~$0.01-0.02 per image (estimated)
- **Total**: $0.10-0.20

### GPT-4o Failed Images (45 images, if needed)
- **Rate**: ~$0.01-0.02 per image
- **Total**: $0.45-0.90

**Total estimated cost**: $0.75-1.50 USD

---

## Documentation Updated
- `OCR_GAP_ANALYSIS.md` - Still relevant for overall gap analysis
- `ZIP_INVENTORY_REPORT.md` - THIS FILE (new)
- `failed_ocr_images.csv` - Existing list of failed images
- `unprocessed_pdfs_list.txt` - NEW list of 101 PDFs to process

---

**Status**: Ready to begin Phase 1 (PDF → Image conversion)
