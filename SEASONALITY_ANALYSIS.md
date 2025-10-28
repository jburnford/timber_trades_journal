# TTJ Seasonality Analysis - Anomaly Detection

**Date**: January 27, 2025
**Purpose**: Identify gaps in OCR coverage using expected seasonal patterns in timber shipping

---

## Expected Seasonal Pattern

**Maritime timber trade follows clear seasonal patterns**:
- **WINTER (Nov-Mar)**: Low activity (~90 ships/issue avg) - frozen Baltic ports, storms
- **SPRING (Apr-May)**: Rising activity (~82 ships/issue) - ice breakup, shipping resumes
- **SUMMER (Jun-Sep)**: Peak activity (~176 ships/issue) - ideal sailing conditions
- **FALL (Oct)**: Declining activity (~160 ships/issue) - preparing for winter

**Summer:Winter ratio**: 1.96x (nearly double)

---

## Monthly Ship Arrival Pattern (Baseline)

| Month | Season | Avg Ships/Issue | Total Issues | Total Ships |
|-------|--------|-----------------|--------------|-------------|
| Jan | WINTER | 67.5 | 54 | 3,643 |
| Feb | WINTER | 49.2 | 27 | 1,329 |
| Mar | WINTER | 61.1 | 27 | 1,649 |
| Apr | SPRING | 78.8 | 29 | 2,285 |
| May | SPRING | 86.3 | 30 | 2,590 |
| **Jun** | **SUMMER** | **132.0** | 32 | 4,223 |
| **Jul** | **SUMMER** | **145.9** | 33 | 4,815 |
| **Aug** | **SUMMER** | **211.7** | 35 | 7,411 |
| **Sep** | **SUMMER** | **215.3** | 33 | 7,106 |
| Oct | FALL | 160.2 | 33 | 5,285 |
| Nov | WINTER | 166.8 | 33 | 5,503 |
| Dec | WINTER | 105.5 | 34 | 3,588 |

**Key insight**: August-September are peak months (200+ ships/issue)

---

## Critical Anomalies Detected

### 1. Years with MISSING SUMMER COVERAGE (6 years)

**These years show ZERO summer issues despite having winter data - clear OCR gaps:**

| Year | Issues | Winter Ships | Summer Ships | Problem |
|------|--------|--------------|--------------|---------|
| **1884** | 4 | 491 | **0** | Missing May-Dec (11 months) |
| **1890** | 4 | 282 | **0** | Missing May-Dec (11 months) |
| **1892** | 5 | 458 | **0** | Missing May-Dec (11 months) |
| **1896** | 3 | 124 | **0** | Missing May-Dec (11 months) |
| **1898** | 5 | 271 | **0** | Missing May-Dec (11 months) |
| **1900** | 4 | 21 | **0** | Missing May-Dec (11 months) |

**Impact**: Missing ~60-70% of annual ship arrivals for these years

---

### 2. Years with LOW SUMMER COUNTS (2 years)

**These years have some summer issues but far fewer ships than expected:**

| Year | Summer Issues | Ships/Issue | Expected | Shortfall |
|------|---------------|-------------|----------|-----------|
| **1897** | 4 | 64 | 176 | -64% |
| **1899** | 18 | 76 | 176 | -57% |

**1897 Analysis**:
- Only 4 summer issues processed
- 52 unprocessed PDFs (mostly Jul-Dec 1897)
- **Action**: Processing unprocessed PDFs will fix this

**1899 Analysis**:
- 18 summer issues but only 76 ships/issue (half expected)
- Possible causes:
  - Multi-page issues incomplete
  - Parser detection failures
  - Smaller journal format in late 1890s

---

### 3. Issues with ZERO Ships Parsed (25 issues)

**These issues have OCR files but no ships parsed - likely parser failures:**

| Year | Zero-Ship Issues | Example Dates |
|------|------------------|---------------|
| 1881 | 8 | Jan 1, Jan 29, Feb 26, Mar 12, Mar 19, Apr 2, Apr 9, Dec 31 |
| 1883 | 1 | Feb 3 |
| 1891 | 1 | Feb 14 |
| 1893 | 1 | Feb 4 |
| 1895 | 1 | Nov 16 (4 OCR files!) |
| 1896 | 1 | Jan 4 |
| 1897 | 1 | Jan 16 |
| **1899** | **11** | Mar 11, Apr 1, Apr 8, May 6, Sep 9, Oct 14, Dec 16, Dec 23 |
| **1900** | **4** | Jan 13, Jan 20, Jan 27 |

**Concern**: 1899 has 11 zero-ship issues (21% of all issues that year)

**Likely causes**:
1. Issues contain only advertisements/editorial (unlikely for 11 issues)
2. Parser regex patterns failing on late 1890s format changes
3. Multi-page issues where cargo section is on missing page

---

### 4. Month Coverage Gaps by Year

| Year | Missing Months | Impact |
|------|----------------|--------|
| 1879 | Jan, Feb, Mar, May (4 months) | Partial winter data |
| 1884 | Feb-Dec (11 months) | **CRITICAL** |
| 1890 | Feb-Dec (11 months) | **CRITICAL** |
| 1892 | Feb-Dec (11 months) | **CRITICAL** |
| 1895 | Jan-Jun (6 months) | Missing winter/spring |
| 1896 | Feb-Dec (11 months) | **CRITICAL** |
| 1897 | Jul-Dec (6 months) | Missing summer/fall |
| 1898 | Feb-Dec (11 months) | **CRITICAL** |
| 1900 | Feb-Dec (11 months) | **CRITICAL** |

---

## Anomalously Low Ship Counts

**Issues with suspiciously low counts for their season:**

| Date | Season | Ships | Expected | Possible Cause |
|------|--------|-------|----------|----------------|
| 1889-02-09 | Winter | 2 | >10 | Partial page OCR |
| 1890-01-25 | Winter | 9 | >10 | Partial OCR |
| 1891-03-14 | Winter | 7 | >10 | Parsing issue |
| 1891-07-25 | Summer | 29 | >130 | **CRITICAL** - Multi-page incomplete |
| 1891-08-08 | Summer | 17 | >210 | **CRITICAL** - Multi-page incomplete |
| 1892-01-30 | Winter | 9 | >10 | Parsing issue |

**1891 summer anomalies** are especially concerning - these should have 100+ ships each.

---

## Root Cause Analysis

### Anomaly Type: MISSING_SUMMER (6 years)
**Root cause**: OCR coverage gaps - we don't have source images for summer issues

**Evidence**:
- Years like 1884, 1890, 1892, 1896, 1898, 1900 have only Jan issues
- Pattern matches "even years" identified in OCR_GAP_ANALYSIS.md

**Fix**: Not fixable (missing from source archives)

---

### Anomaly Type: LOW_SUMMER (1897, 1899)
**Root cause**: Multiple factors

**1897**:
- **Solvable** - 52 unprocessed PDFs in extracted zips
- Processing these will bring 1897 to normal levels

**1899**:
- Has 49 issues but low ship counts
- 11 issues with zero ships parsed
- **Root cause**: Parser detection failures or format changes
- **Fix**: Investigate 1899-specific parsing issues

---

### Anomaly Type: ZERO SHIPS (25 issues)
**Root cause**: Parser detection failures

**Patterns**:
1. Early in year (Jan-Apr) - possibly "annual review" issues without cargo lists
2. Late in year (Dec) - possibly holiday issues
3. Clustered in 1899 (11 issues) - format change?

**Fix**:
- Manual inspection of zero-ship OCR files
- Improve parser regex for late 1890s format

---

## Recommendations (Priority Order)

### Priority 1: Process Unprocessed PDFs (Immediate Impact)
**Action**: OCR the 101 unprocessed PDFs
- 52 PDFs from 1897 (Jul-Dec) → will fix 1897 LOW_SUMMER anomaly
- 49 PDFs from 1895 → will improve 1895 coverage

**Expected result**: 1897 goes from 64 → 176 ships/issue (normal)

---

### Priority 2: Investigate 1899 Parser Failures
**Action**: Manual review of zero-ship issues
- Read OCR text for 1899-09-09 (7 OCR files, 0 ships)
- Read OCR text for 1899-10-14 (6 OCR files, 0 ships)
- Identify format changes in late 1890s

**Hypothesis**: TTJ changed format in 1899, parser regex no longer matches

---

### Priority 3: Investigate Summer Issues with Low Counts
**Action**: Check if multi-page issues are incomplete
- 1891-07-25: Should have 130+ ships, has 29 (missing 78%)
- 1891-08-08: Should have 210+ ships, has 17 (missing 92%)

**Check**: Do these issues have all pages in OCR results?

---

### Priority 4: Document Unfixable Gaps
**Action**: Accept that 6 years (1884, 1890, 1892, 1896, 1898, 1900) have incomplete coverage

**Rationale**:
- We don't have source images for summer issues
- Winter-only data is still valuable for analysis
- Can note this limitation in documentation

---

## Impact on London Cargo Count Analysis

**Current anomalies explain some of the gap**:

1. **1897 LOW_SUMMER**: Explains why 1897 has only 1,514 ships total
   - Processing 52 unprocessed PDFs will add 2,000-3,000 ships

2. **1899 PARSER FAILURES**: 11 zero-ship issues losing 1,500+ ships
   - Fixing parser will recover substantial data

3. **6 years with MISSING_SUMMER**: Losing 60-70% of annual data
   - Cannot be recovered (no source images)

---

## Validation Strategy

To confirm these are OCR/parser gaps (not actual quiet periods):

1. **Check human transcription years**: If human data covers 1897-1899, compare ship counts
2. **Inspect zero-ship OCR files**: Manually read text to see if ships are present but not parsed
3. **Compare multi-page issues**: Check if low-count summer issues have incomplete page sequences

---

**Status**: Analysis complete - ready to prioritize fixes
