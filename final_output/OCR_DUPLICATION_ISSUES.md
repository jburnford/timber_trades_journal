# OCR Duplication Issues - Gemini LLM Hallucinations

**Issue Type:** LLM repetition errors in OCR output
**Affected Files:** Multiple 1885 Timber Trades Journal pages
**Root Cause:** Gemini OCR model got stuck in repetition loops
**Total Impact:** 3,672 duplicate records out of 35,870 (10.2%)

---

## Overview

During OCR processing with Google Gemini Pro 2.5, certain journal pages experienced **LLM hallucination** where the model repeated the same ship arrival entries multiple times consecutively. This is a known issue with large language models where they can get stuck in repetition patterns.

### Key Characteristic

These are **true duplicates** (same ship + same origin port + same destination port + same date), NOT legitimate repeat voyages. Legitimate repeat voyages would have:
- Different dates
- Different cargo amounts
- Different merchants
- Appearing across multiple journal issues

---

## Affected Files

### Major Issues (≥50 duplicates)

#### 1. **August 8, 1885** - Massive Hallucination
**File:** `10. p. 100-103 - Imports - August 8 1885 - Timber Trades Journal 1885_p001.txt`

**Pattern:** Lines 187-202 repeat 85 times throughout the file (1,625 total lines)

**Affected Ships:**
- **Presto** (Soderhamn): 170 duplicates (169 extras)
- **Preussen** (Dram): 85 duplicates (84 extras)
- **Bjorn** (Gothenburg): 85 duplicates
- **Bifrost** (Christiania): 85 duplicates
- **Zealous** (Finklippan): 85 duplicates (spread across 2 page files)
- **Benbrack** (Pierreville and Quebec): 85 duplicates
- **Sapphire** (Archangel): 85 duplicates
- **Whiddington** (Wyborg): 85 duplicates
- **Veritas** (Bjorneborg): 84 duplicates
- **Finale** (Quebec): 84 duplicates
- **Poltonzo** (Cronstadt): 84 duplicates

**Total from this file:** ~1,000 duplicate records

**Sample Original OCR:**
```
Line 190: Presto (s)-Soderhamn-11 fms. firewood-Order
Line 207: Presto (s)-Soderhamn-11 fms. firewood-Order  [DUPLICATE]
Line 224: Presto (s)-Soderhamn-11 fms. firewood-Order  [DUPLICATE]
Line 241: Presto (s)-Soderhamn-11 fms. firewood-Order  [DUPLICATE]
... repeats 170 times total
```

#### 2. **May 9, 1885** - Carl XV. Repetition
**File:** `19. p. 339-341 - Imports - May 9 1885 -Timber Trades Journal 1885_p003.txt`

**Affected Ship:**
- **Carl XV.** (Oresund): 1,409 duplicates (1,408 extras)

**Pattern:** Lines 12-13 repeat 704 times consecutively

**Sample Original OCR:**
```
Line 12: May 1 Carl XV.-Oresund-1,097 pcs. partly mining timber-Order
Line 13: Apr. 29 Carl XV.-Oresund-1,643 props-Order
Line 14: May 1 Carl XV.-Oresund-1,097 pcs. partly mining timber-Order  [DUPLICATE]
Line 15: Apr. 29 Carl XV.-Oresund-1,643 props-Order  [DUPLICATE]
... repeats 1,409 times total
```

**Note:** Parser only captured the "Apr. 29" line, resulting in 1,409 identical records instead of alternating patterns.

### Minor Issues (5-10 duplicates)

#### 3. **August 29, 1885** - Small Repetitions
**File:** `13. p. 153-155 - Imports - August 29 1885 - Timber Trades Journal 1885_p001.txt`

**Affected Ship:**
- **Medea** (Krageroe): 5 duplicates

**Pattern:** Lines 304-307 repeat 3 times

#### 4. **April 25, 1885** - Small Repetitions
**File:** `17. p. 302-303 - Imports - April 25 1885 - Timber Trades Journal 1885_p002.txt`

**Affected Ship:**
- **Grahant** (Danzig): 3 duplicates

**Pattern:** Lines 50-56 repeat 3 times

### Cross-File Duplicates (Legitimate or Error?)

Several ships appear 5-6 times across **different journal issues** (different files, different dates):
- **Prins Oscar** (Gothenburg → London): 6 occurrences across 6 different 1881 issues
- **Romeo** (Gothenburg → Hull): 6 occurrences across 6 different 1887 issues
- **Cameo** (Christiania → Millwall Docks): 6 occurrences across 6 different 1887 issues

**Assessment:** These are likely **LEGITIMATE repeat voyages** - same ship making multiple trips over months/years. Should be preserved.

---

## Technical Analysis

### Why This Happened

**LLM Repetition Phenomenon:**
- Large language models can get "stuck" in repetition loops
- Occurs when the model's attention mechanism fixates on a pattern
- More common with:
  - Tabular/structured data (like ship arrival lists)
  - Long input sequences
  - When there's existing repetition in the source (like column headers)

**Gemini-Specific:**
- Gemini Pro 2.5 was used for OCR (via olmOCR or similar)
- Known to occasionally hallucinate repetitions in structured documents
- More likely when processing multi-column layouts or tables

### Deduplication Strategy

**Remove if:**
- Same ship name
- Same origin port
- Same destination port
- Same arrival date (day, month, year)
- Multiple occurrences in dataset

**Keep if:**
- Different dates (even if same ship and ports)
- Only occurs once
- Spans multiple years (legitimate repeat business)

---

## Impact Assessment

### Before Deduplication
- Total records: **35,870 ships**
- Cargo items: **58,602 items**

### After Deduplication
- Duplicate patterns: **1,160 patterns**
- Duplicate records to remove: **3,672 records** (10.2%)
- Final dataset: **32,198 ships** (expected)
- Final cargo items: **~55,000 items** (expected)

### Data Quality Impact

**Minimal loss of real information:**
- Only removing exact duplicates (same ship, same date, same route)
- Preserving all legitimate repeat voyages
- Preserving all unique ship arrivals

**Improved data quality:**
- More accurate ship counts
- More accurate commodity volumes
- Cleaner temporal analysis
- Better merchant network analysis

---

## Files Affected by Duplication

### High-Impact Files (≥50 duplicates)
1. `10. p. 100-103 - Imports - August 8 1885 - Timber Trades Journal 1885_p001.txt` (~1,000 duplicates)
2. `19. p. 339-341 - Imports - May 9 1885 -Timber Trades Journal 1885_p003.txt` (1,408 duplicates)

### Medium-Impact Files (10-50 duplicates)
3. `10. p. 100-103 - Imports - August 8 1885 - Timber Trades Journal 1885_p002.txt` (Zealous spillover)

### Low-Impact Files (<10 duplicates)
4. `13. p. 153-155 - Imports - August 29 1885 - Timber Trades Journal 1885_p001.txt` (5 duplicates)
5. `17. p. 302-303 - Imports - April 25 1885 - Timber Trades Journal 1885_p002.txt` (3 duplicates)

### Cross-File Pattern Files
- Multiple 1881 files (Prins Oscar pattern - 6 occurrences, likely legitimate)
- Multiple 1887 files (Romeo, Cameo patterns - 6 occurrences each, likely legitimate)
- Multiple 1885 files (various ships - 5 occurrences each, likely legitimate)

---

## Recommendations

### Immediate Action
✅ **Deduplicate dataset** using signature-based deduplication:
- Signature: (ship_name, origin_port, destination_port, arrival_day, arrival_month, arrival_year)
- Keep first occurrence of each signature
- Remove subsequent duplicates

### Future OCR Improvements
1. **Monitor for repetition patterns** in OCR output
2. **Implement repetition detection** in OCR pipeline
3. **Set max repetition thresholds** (e.g., flag if same line appears >5 times)
4. **Consider alternative OCR models** for problematic pages
5. **Post-process OCR** with repetition removal before parsing

### Validation
- Spot-check deduplicated records against original journal images
- Verify that "repeat voyages" across different dates are preserved
- Confirm cargo volumes make sense after deduplication

---

## Resolution

**Script:** `tools/deduplicate_all_patterns.py`

**Action Taken:**
1. Identified 3,672 duplicate records across 1,160 patterns
2. Kept first occurrence of each unique (ship + port + date) combination
3. Removed subsequent duplicates
4. Generated cleaned dataset in `final_output/deduped/`

**Files Created:**
- `final_output/deduped/ttj_shipments_deduped.csv` (32,198 records)
- `final_output/deduped/ttj_cargo_details_deduped.csv` (corresponding cargo)
- `final_output/duplicate_patterns_report.json` (detailed analysis)

---

## Verification

**How to verify the fix worked:**

```python
import pandas as pd

# Load deduplicated data
df = pd.read_csv('final_output/deduped/ttj_shipments_deduped.csv')

# Check for remaining duplicates
sig = df.groupby(['ship_name', 'origin_port', 'destination_port',
                  'arrival_day', 'arrival_month', 'arrival_year']).size()
duplicates = sig[sig > 1]

print(f"Remaining duplicates: {len(duplicates)}")  # Should be 0
print(f"Total ships: {len(df)}")  # Should be ~32,198
```

**Expected result:** 0 duplicates remaining

---

## Lessons Learned

1. **LLM OCR is powerful but not perfect** - can hallucinate repetitions
2. **Always validate OCR output** - especially for structured/tabular data
3. **Signature-based deduplication works well** for this type of error
4. **Preserve legitimate patterns** - not all repetition is error
5. **Document thoroughly** - for future researchers using this data

---

**Date Created:** October 17, 2025
**Issue Discovered:** During port normalization analysis
**Resolution Status:** ✅ Fixed via deduplication
**Validation Status:** ⏳ Pending manual spot-check
