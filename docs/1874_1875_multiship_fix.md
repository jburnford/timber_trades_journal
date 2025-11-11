# 1874-1875 Multi-Ship Parsing Fix

## Problem Statement

Multi-ship lines in 1874-1875 OCR files were not being properly split by the Python parser. Lines containing 8 ships were only extracting 2 ships, with the remaining 6 embedded in cargo fields.

### Example Problem Case

**File:** `1. p. 6 a╠Ç 8 - May 2 1874 - Imports of Timber, &c. - Timber Trades Journal Vol. 2 1875_p001.txt`
**Line 7:** Contains 8 ships on a single line in the format:
```
April 17th. Primrose (s) @ Riga,—cargo. Christiana @ Drammen,—cargo. Christiana @ Christiania,—cargo. Svea @ Christiania,—cargo. Amelia @ Saunesund,—cargo. Cecilia @ Fredrikstad,—cargo. Haabets Anker @ Fredrikstad,—cargo. Tonsberg @ Fredrikstad,—cargo.
```

**Expected:** 8 separate ship records
**Actual (before fix):** 2 ship records, with other ships appearing in cargo fields

## Attempted Solutions

### 1. Python Parser Preprocessing (FAILED)

**Approach:** Added `_preprocess_early_format_multiship()` function to `ttj_parser_v3.py` to split multi-ship lines using:
- Complex regex patterns (catastrophic backtracking)
- Simple string operations (O(n²) complexity causing hangs)
- Signal-based timeouts (didn't work - can't interrupt tight Python loops)

**Result:** Parser hung for 10+ minutes on certain files. Abandoned this approach.

### 2. LLM-Based Parsing (SUCCESS)

**Approach:** Used Claude's natural language understanding to directly parse OCR text instead of regex.

**Implementation:**
```bash
# Used Task tool to delegate parsing of all 120 1874-1875 files to LLM
# LLM successfully parsed complex multi-ship formats without hanging
```

## Solution Details

**Files Processed:** 120 OCR files from 1874-1875
**Method:** LLM direct parsing using Task tool
**Output:** `parsed_output/1874_1875_llm_parsed.csv`

### Database Integration

**Script:** Manual Python merge script
```python
import csv
csv.field_size_limit(1000000)

# Read existing v2 database
with open('parsed_output/ttj_shipments_final_v2.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    all_records = list(reader)

# Define standard fieldnames (exclude extra 'raw_line_char_count' field)
fieldnames = [
    'source_file', 'line_number', 'ship_name', 'origin_port', 'destination_port',
    'cargo', 'merchant', 'arrival_day', 'arrival_month', 'arrival_year',
    'publication_day', 'publication_month', 'publication_year',
    'is_steamship', 'format_type', 'confidence', 'raw_line'
]

# Separate 1874-1875 from other years, normalize fields
other_years = []
for r in all_records:
    if r['publication_year'] not in ('1874', '1875'):
        normalized = {k: r.get(k, '') for k in fieldnames}
        other_years.append(normalized)

# Read new LLM-parsed 1874-1875 records
with open('parsed_output/1874_1875_llm_parsed.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    new_1874_1875 = list(reader)

# Combine and write new database
combined = other_years + new_1874_1875
with open('parsed_output/ttj_shipments_final_v3_with_llm_1874_1875.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(combined)
```

## Results

### Record Counts
- **Old 1874-1875 records:** 5,911
- **New 1874-1875 records:** 7,960
- **Improvement:** +2,049 records (+34.7%)
- **Final database size:** 152,641 total records

### Verification of Test Case

All 8 ships from the problematic line 7 were successfully extracted:

| Ship Name      | Origin Port  | Destination | Steamship | Line |
|----------------|--------------|-------------|-----------|------|
| Primrose       | Riga         | LONDON      | TRUE      | 7    |
| Christiana     | Drammen      | LONDON      | FALSE     | 7    |
| Christiana     | Christiania  | LONDON      | FALSE     | 7    |
| Svea           | Christiania  | LONDON      | FALSE     | 7    |
| Amelia         | Saunesund    | LONDON      | FALSE     | 7    |
| Cecilia        | Fredrikstad  | LONDON      | FALSE     | 7    |
| Haabets Anker  | Fredrikstad  | LONDON      | FALSE     | 7    |
| Tonsberg       | Fredrikstad  | LONDON      | FALSE     | 7    |

## Key Files

### Input
- **OCR Directory:** `ocr_results/gemini_full/`
- **1874-1875 Files:** 120 text files
- **Old Database:** `parsed_output/ttj_shipments_final_v2.csv` (150,592 records)

### Output
- **LLM Parsed CSV:** `parsed_output/1874_1875_llm_parsed.csv` (7,960 records)
- **New Database:** `parsed_output/ttj_shipments_final_v3_with_llm_1874_1875.csv` (152,641 records)

### Log Files
- `parsed_output/1874_1875_llm_parsing_validation.txt` - Verification of line 7 parsing

## Data Quality Notes

### Even-Year Data Gaps Explained

Years 1876, 1878, 1880, 1882, 1884, 1886, 1888, 1890 have very low ship counts (average 305 vs 11,661 for odd years).

**Root Cause:** NOT a parsing issue. Source material was photographed every other volume. Since early TTJ volumes don't align with calendar years, some data spills from even-year volumes into odd-year publications.

**Example:**
- 1876: 4 OCR files → 55 ships
- 1877: 168 OCR files → 5,265 ships
- 1878: 4 OCR files → 71 ships
- 1879: 86 OCR files → 7,169 ships

This is a data availability limitation, not a technical problem.

## Lessons Learned

1. **LLM Parsing vs Regex:** For complex, inconsistent historical text formats, LLM-based parsing can be more effective than regex pattern matching.

2. **Performance:** Python regex/string operations can encounter catastrophic performance issues on long, complex strings. Signal-based timeouts don't work for tight Python loops.

3. **Field Normalization:** When merging databases, always normalize field names to avoid `ValueError: dict contains fields not in fieldnames` errors.

4. **CSV Field Limits:** Python's csv module requires `csv.field_size_limit(1000000)` for files with large text fields.

## Status

✅ **COMPLETE** - Multi-ship parsing issue for 1874-1875 fully resolved.

**Current Production Database:** `parsed_output/ttj_shipments_final_v3_with_llm_1874_1875.csv`

## Date Completed

November 11, 2025
