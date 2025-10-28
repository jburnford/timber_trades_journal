# TTJ OCR Gap Analysis & Recovery Plan

**Date**: January 27, 2025
**Issue**: Missing ~90% of expected London cargo records due to incomplete OCR coverage

---

## Executive Summary

### Current Status
- **Total OCR files**: 1,866 files covering 1874-1900
- **Complete coverage**: 11 years (>50 files/year)
- **Incomplete coverage**: 13 years (<50 files/year)
- **Critical gaps**: 1876, 1878, 1880, 1882, 1884, 1886, 1888, 1890 (2-9 files each)

### Impact
- **London cargo records**: 14,217 across 26 years
- **Expected (based on human data)**: ~130,000-150,000 records for complete coverage
- **Missing**: ~90% of potential dataset

---

## OCR Coverage by Year

| Year | Files | Status | Estimated Missing |
|------|-------|--------|-------------------|
| **1874** | 57 | ✓ Good | ~0% |
| **1875** | 63 | ✓ Good | ~0% |
| **1876** | 2 | ❌ Critical | ~95% |
| **1877** | 84 | ✓ Good | ~0% |
| **1878** | 2 | ❌ Critical | ~95% |
| **1879** | 43 | ⚠️ Partial | ~40% |
| **1880** | 3 | ❌ Critical | ~95% |
| **1881** | 124 | ✓ Good | ~0% |
| **1882** | 2 | ❌ Critical | ~95% |
| **1883** | 153 | ✓ Good | ~0% |
| **1884** | 9 | ❌ Critical | ~90% |
| **1885** | 141 | ✓ Good | ~0% |
| **1886** | 4 | ❌ Critical | ~95% |
| **1887** | 130 | ✓ Good | ~0% |
| **1888** | 4 | ❌ Critical | ~95% |
| **1889** | 203 | ✓ Good | ~0% |
| **1890** | 9 | ❌ Critical | ~90% |
| **1891** | 179 | ✓ Good | ~0% |
| **1892** | 15 | ⚠️ Partial | ~75% |
| **1893** | 171 | ✓ Good | ~0% |
| **1895** | 98 | ✓ Good | ~0% |
| **1896** | 7 | ❌ Critical | ~90% |
| **1897** | 90 | ✓ Good | ~0% |
| **1898** | 20 | ⚠️ Partial | ~70% |
| **1899** | 237 | ✓ Good | ~0% |
| **1900** | 16 | ⚠️ Partial | ~75% |

**Pattern**: Even years (1876, 1878, 1880, 1882, 1884, 1886, 1888, 1890) consistently have <10 files

---

## Root Cause Analysis

### Hypothesis: Gemini API Budget Constraints
The pattern suggests OCR processing was interrupted or rationed, with alternating years receiving full vs minimal processing.

**Evidence**:
1. Odd years (1875, 1877, 1881, 1883, 1885, 1887, 1889, 1891, 1893) have 63-237 files
2. Even years consistently have 2-20 files
3. Pattern holds across 14 years (1876-1890)

### Why Gemini OCR Was Limited
- **Cost**: Gemini Pro 2.5 Vision pricing for large-scale OCR
- **Rate limits**: API quotas may have been exhausted
- **Processing strategy**: Prioritized sample years over complete coverage

---

## Alternative OCR Solutions

### Option 1: Google AI Studio (Gemini - Free Tier)
**Pros**:
- Same Gemini model as before (consistency)
- Free tier available (with limits)
- Direct API access

**Cons**:
- Daily/monthly quotas
- Slower than paid API
- May still hit limits for full dataset

**Recommendation**: Test on 1880 (3 files exist, ~70 needed) to validate approach

---

### Option 2: Tesseract 5 (Open Source)
**Pros**:
- Completely free
- No rate limits
- Fast processing
- Can run locally or on cluster

**Cons**:
- Lower accuracy than Gemini on historical documents
- Requires image preprocessing
- May need extensive post-correction

**Accuracy**: ~80-85% on 19th century printed text (vs ~95% for Gemini)

**Recommendation**: Use as backup for years where Gemini isn't feasible

---

### Option 3: Azure Computer Vision OCR
**Pros**:
- High accuracy (comparable to Gemini)
- Good historical document support
- Reasonable pricing

**Cons**:
- Requires Azure account
- Per-page pricing
- Less context-aware than Gemini

**Cost Estimate**: $1-3 per 1,000 pages

---

### Option 4: Hybrid Approach (RECOMMENDED)
1. **Gemini AI Studio**: Process missing even years (free tier)
   - 1876: ~70 pages needed
   - 1878: ~70 pages needed
   - 1880: ~70 pages needed
   - 1882: ~70 pages needed
   - 1884: ~65 pages needed
   - 1886: ~70 pages needed
   - 1888: ~70 pages needed
   - 1890: ~65 pages needed
   - **Total**: ~580 pages for critical even years

2. **Tesseract**: Fill remaining gaps if AI Studio quota exhausted

3. **Validation**: Compare Tesseract vs Gemini on overlapping pages to assess quality trade-off

---

## Testing Plan

### Phase 1: Validate Gemini AI Studio (1-2 hours)
1. Set up Google AI Studio account
2. Test on 10 pages from 1880
3. Compare output quality to existing Gemini results
4. Assess quota limits and feasibility

### Phase 2: Process Critical Even Years (4-6 hours)
1. Identify missing PDF pages for 1880, 1882, 1884, 1886, 1888, 1890
2. Process with Gemini AI Studio (free tier)
3. Run through existing parser pipeline
4. Validate London cargo record counts

### Phase 3: Tesseract Backup (if needed)
1. Test Tesseract 5 on sample pages
2. Compare accuracy to Gemini
3. Process remaining gaps if acceptable quality

### Phase 4: Parser Detection Analysis
1. Sample 50 human-transcribed pages
2. Compare human record counts to parser record counts
3. Identify systematic detection failures
4. Improve regex patterns if needed

---

## Expected Outcomes

### If Critical Even Years Processed (Best Case)
- **Current**: 14,217 London cargo records (26 years)
- **With even years filled**: ~60,000-80,000 London cargo records
- **Coverage**: ~50-60% of full dataset

### If All Missing Years Processed
- **Target**: 130,000-150,000 London cargo records
- **Coverage**: ~95% of full dataset

---

## Recommendations

### Immediate Action (Priority 1)
1. ✅ **COMPLETED**: Fix parser bugs (UK city headers, multi-page context)
2. **IN PROGRESS**: Create list of missing PDF pages
3. **NEXT**: Test Gemini AI Studio on 1880 sample

### Short Term (Priority 2)
1. Process critical even years (1880, 1882, 1884, 1886, 1888, 1890) with AI Studio
2. Validate parser detection with human transcription comparison
3. Re-run complete pipeline with expanded dataset

### Long Term (Priority 3)
1. Process all remaining gaps (1876, 1878, 1892, 1896, 1898, 1900)
2. Consider Tesseract for cost-efficiency if quality acceptable
3. Build automated validation against human ground truth

---

## Parser Detection Analysis (User Question)

### Question
"Is our initial parser phase that detects lines related to ships and distinguishes them from other content missing a lot of ships?"

### Analysis Plan
1. **Ground Truth Comparison**:
   - Take 10-20 pages with human transcription
   - Count ships in human data vs parser output
   - Calculate recall rate (% of human ships detected by parser)

2. **Pattern Analysis**:
   - Identify ship record formats parser may be missing
   - Check for systematic failures (e.g., certain date formats, ship name patterns)

3. **Regex Pattern Review**:
   - Current patterns: `early_at_pattern`, `standard_dash_pattern`, `condensed_dash_pattern`
   - Test against edge cases from human data

### Expected Issues
- **Format variations**: TTJ changed format over 26 years
- **OCR errors**: Malformed dates, missing @/- symbols
- **Multi-ship entries**: Multiple ships in single line
- **Condensed formats**: Ship entries without explicit date

### Recommendation
Run ground truth comparison on 50 pages across different years and formats to quantify detection accuracy.

---

## Next Steps

**Immediate** (this session):
1. Create list of missing PDFs by year
2. Test Gemini AI Studio setup and quotas
3. Begin parser detection analysis

**Short term** (next session):
1. Process 1880 with AI Studio (test case)
2. Validate results and scale to other even years
3. Complete parser detection analysis with human data

**Long term** (future sessions):
1. Fill all OCR gaps
2. Re-process complete dataset
3. Achieve 95%+ coverage target

---

## Questions for User
1. Do you have access to Gemini AI Studio, or should we set it up?
2. Do you have PDF source files for missing years, or are they accessible online?
3. Would you like to prioritize certain years for OCR (e.g., those matching your human transcription period)?
4. Should we test Tesseract as backup, or focus on Gemini AI Studio only?

---

**Status**: Ready to begin Phase 1 (Testing Gemini AI Studio)
