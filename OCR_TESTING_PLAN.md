# OCR Testing Plan - British Library Newspaper Collection

## Dataset Overview

**Location**: `/home/jic823/ocr_bldata/25439023/BLN600/`
- **Images**: 600 newspaper page images (TIF/JPG format)
- **Ground Truth**: 600 corresponding transcriptions
- **Source**: Gale's British Library Newspaper Collection

**Important**: Ground truth data must NEVER be committed to GitHub (copyrighted/licensed data).

---

## Purpose

This dataset provides a perfect testbed for:

1. **OCR Quality Assessment**
   - Test Gemini OCR vs. ground truth
   - Measure character error rate (CER) and word error rate (WER)
   - Identify systematic OCR errors

2. **Parser Validation**
   - If any pages contain shipping/commerce data, test cargo parser
   - Validate merchant extraction
   - Test port/location recognition

3. **Comparison Baseline**
   - Compare different OCR engines (Gemini vs. Tesseract vs. EasyOCR)
   - Benchmark parsing accuracy improvements

---

## Testing Strategy

### Phase 1: OCR Quality Baseline (1-2 hours)

**Objective**: Measure current Gemini OCR accuracy

**Steps**:
1. Select sample (N=50 images, stratified random)
2. Run Gemini OCR on sample
3. Calculate metrics vs. ground truth:
   - Character Error Rate (CER)
   - Word Error Rate (WER)
   - Line accuracy
   - Properly formatted text percentage

**Script**: `tools/test_ocr_accuracy.py`

```python
def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate character error rate using edit distance."""

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate word error rate."""

def test_ocr_sample(image_dir, gt_dir, sample_size=50):
    """Run OCR on sample and compare to ground truth."""
```

### Phase 2: Error Analysis (30 minutes)

**Identify systematic issues**:
- Common character misrecognitions (l/I, 0/O, etc.)
- Layout problems (column confusion, headers/footers)
- Special character handling
- Historical typography issues (long s, ligatures)

**Output**: `ocr_error_analysis.csv` with:
- Error type (substitution, insertion, deletion)
- Frequency
- Context (surrounding characters)
- Impact on parsing

### Phase 3: Parser Testing (if applicable)

**Check if dataset contains relevant content**:
- Sample 100 ground truth files
- Search for shipping/commerce indicators:
  - Port names
  - Ship names
  - Cargo terminology (timber, deals, staves)
  - Merchant names

**If relevant data found**:
- Run improved cargo parser
- Compare extraction quality vs. ground truth
- Measure precision/recall on:
  - Commodity extraction
  - Merchant extraction
  - Quantity+unit extraction

### Phase 4: Comparative Testing (optional)

**Compare OCR engines** (if time/resources available):

| Engine | Pros | Cons | Speed |
|--------|------|------|-------|
| Gemini | High accuracy, multimodal | API cost | Moderate |
| Tesseract | Free, local | Lower accuracy on complex layouts | Fast |
| EasyOCR | Good for handwriting | Slower | Slow |

**Test setup**:
- Same 50-image sample
- Run all three engines
- Compare CER/WER
- Compare processing time
- Compare cost

---

## Implementation Plan

### Step 1: Create Testing Infrastructure

**File**: `tools/test_ocr_accuracy.py`

Functions needed:
- `calculate_cer()` - Character error rate
- `calculate_wer()` - Word error rate
- `normalize_text()` - Standardize whitespace, punctuation for comparison
- `run_gemini_ocr()` - OCR a single image
- `compare_to_ground_truth()` - Full comparison with metrics

### Step 2: Sample Selection

```python
import random
import os

def select_stratified_sample(image_dir, n=50):
    """
    Select random sample, ensuring variety.

    Stratify by:
    - File size (proxy for content density)
    - File format (TIF vs JPG)
    """
    images = [f for f in os.listdir(image_dir)
              if f.endswith(('.tif', '.jpg'))]

    # Stratify by size
    sizes = [(f, os.path.getsize(f)) for f in images]
    # Sort by size, sample evenly across quintiles

    return sample_ids
```

### Step 3: Run OCR Tests

```bash
# Test on sample
python tools/test_ocr_accuracy.py \
    --image-dir /home/jic823/ocr_bldata/25439023/BLN600/Images \
    --gt-dir "/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth" \
    --sample-size 50 \
    --output ocr_test_results.csv
```

### Step 4: Analyze Results

Generate report with:
- Overall CER/WER statistics
- Error distribution by type
- Most common misrecognitions
- Recommendations for improvement

---

## Metrics to Track

### Accuracy Metrics

**Character Error Rate (CER)**:
```
CER = (substitutions + insertions + deletions) / total_characters
```
- **Target**: <5% for good OCR
- **Acceptable**: <10%
- **Poor**: >10%

**Word Error Rate (WER)**:
```
WER = (substitutions + insertions + deletions) / total_words
```
- **Target**: <10% for good OCR
- **Acceptable**: <20%
- **Poor**: >20%

### Processing Metrics

- **Speed**: Pages per minute
- **Cost**: API calls and pricing
- **Reliability**: Success rate (% of pages processed without errors)

### Parser Metrics (if applicable)

- **Commodity extraction**:
  - Precision: % of extracted commodities that are correct
  - Recall: % of true commodities that were extracted
  - F1 Score: Harmonic mean of precision and recall

- **Quantity extraction**:
  - Exact match rate
  - Off-by-one tolerance rate

---

## Test Data Management

### Directory Structure

```
/home/jic823/ocr_test_workspace/
├── bl_sample/
│   ├── images/              # Symlinks to BL images
│   ├── ground_truth/        # Symlinks to ground truth
│   └── sample_ids.txt       # List of selected IDs
├── ocr_output/
│   ├── gemini/             # Gemini OCR results
│   ├── tesseract/          # Tesseract results (if tested)
│   └── easyocr/            # EasyOCR results (if tested)
├── metrics/
│   ├── cer_wer_results.csv
│   ├── error_analysis.csv
│   └── ocr_comparison.csv
└── reports/
    ├── ocr_accuracy_report.md
    └── error_patterns.md
```

### .gitignore Updates

Add to TTJ repository `.gitignore`:
```
# OCR test data (copyrighted)
/home/jic823/ocr_bldata/
/home/jic823/ocr_test_workspace/
ocr_test_results.csv
ocr_error_analysis.csv

# But DO track
ocr_accuracy_report.md  # Summary statistics only
error_patterns.md       # Anonymized error patterns
tools/test_ocr_accuracy.py  # Testing scripts
```

---

## Expected Outcomes

### Success Metrics

1. **Baseline Established**
   - Know current Gemini OCR CER/WER on newspaper data
   - Documented error patterns

2. **Validation Tool**
   - Reusable testing infrastructure
   - Can test TTJ parsing improvements

3. **Informed Decisions**
   - Whether to adjust OCR approach
   - Whether to add post-OCR correction
   - Which errors to prioritize in parser

### Potential Findings

**If CER is <5%**:
- OCR quality is excellent
- Parser improvements will have high ROI
- Focus on cargo/merchant parsing

**If CER is 5-10%**:
- OCR quality is good but improvable
- Consider post-OCR correction for critical fields
- Parser should be robust to minor OCR errors

**If CER is >10%**:
- May need different OCR approach
- Or BL newspaper images differ significantly from TTJ
- Test on actual TTJ pages for comparison

---

## Next Steps

### Immediate (this session if desired)

1. Create `tools/test_ocr_accuracy.py`
2. Run on small sample (N=10) to verify pipeline
3. Examine a few comparisons manually
4. Decide whether to continue with full 50-sample test

### Short Term (next session)

1. Full 50-sample OCR test
2. Generate accuracy metrics
3. Error analysis and report
4. Compare to TTJ OCR quality

### Medium Term (future)

1. Test parser on BL data (if relevant content found)
2. Compare parser v1 vs. improved parser
3. Use as validation set for cargo parser improvements

---

## Open Questions

1. **Relevance to TTJ**:
   - Are these newspaper pages similar to TTJ content?
   - Do they contain shipping/commerce data?
   - Or is this a general news corpus?

2. **Ground Truth Quality**:
   - How was ground truth created (manual transcription)?
   - What standards were used (verbatim vs. normalized)?
   - Are there known issues with ground truth?

3. **Testing Scope**:
   - Test OCR only, or also parser?
   - Compare multiple OCR engines, or focus on Gemini?
   - Use for TTJ validation, or independent assessment?

---

## Decision Point

**What would you like to do?**

A. **Quick exploratory test** (30 min)
   - Run Gemini OCR on 5-10 sample images
   - Manual comparison to ground truth
   - Get sense of relevance and quality

B. **Full OCR accuracy test** (2-3 hours)
   - Implement testing infrastructure
   - Run on 50-image sample
   - Generate comprehensive metrics

C. **Defer for now**
   - Focus on cargo parser improvements first
   - Return to OCR testing after parser validated

D. **Different approach**
   - Check what's already in dataset metadata
   - Determine if TTJ-relevant first
   - Then decide on testing approach

**Recommendation**: Start with Option A (quick exploratory test) to assess relevance and quality before investing in full testing infrastructure.
