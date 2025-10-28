# British Library Newspaper OCR Testing

## Overview

This setup allows you to test Gemini OCR on the British Library Newspaper Collection (BLN600 dataset) and compare results against ground truth transcriptions to measure accuracy.

**Dataset**: 600 Victorian-era British newspaper pages with ground truth transcriptions
**Location**: `/home/jic823/ocr_bldata/25439023/BLN600/`

---

## Files Created

### 1. Main Testing Script
**`tools/test_bl_newspaper_ocr.py`**

Comprehensive OCR testing tool that:
- Converts PDFs to images (300 DPI)
- Processes with Gemini OCR (using flash model for speed/cost)
- Compares OCR output against ground truth
- Calculates Character Error Rate (CER) and Word Error Rate (WER)
- Generates detailed reports with statistics

**Key Features**:
- ✅ Appropriate prompt for Victorian newspaper content
- ✅ Handles single-page PDFs
- ✅ Calculates edit distance metrics (CER/WER)
- ✅ Generates both detailed and summary reports
- ✅ Saves individual results as JSON and text files
- ✅ Random sampling with reproducible seed
- ✅ Rate limiting to avoid API throttling

### 2. Runner Script
**`run_bl_ocr_test.sh`**

Convenience script that:
- Sets up correct paths
- Checks/installs dependencies
- Runs test with sensible defaults
- Starts with 10-sample test for validation

---

## Usage

### Quick Start (10-sample test)

```bash
cd "/home/jic823/TTJ Forest of Numbers"
./run_bl_ocr_test.sh
```

This will:
1. Test 10 randomly selected PDFs
2. Generate OCR with Gemini 2.0 Flash
3. Compare against ground truth
4. Calculate CER/WER metrics
5. Create report in `./bl_ocr_test_results/`

**Expected runtime**: ~3-5 minutes (2 seconds delay between API calls)

### Full Test (50 samples)

```bash
python3 tools/test_bl_newspaper_ocr.py \
    --pdf-dir "/home/jic823/ocr_bldata/25439023/BLN600/pdf" \
    --gt-dir "/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth" \
    --output ./bl_ocr_test_50_samples \
    --sample-size 50 \
    --delay 2.0
```

**Expected runtime**: ~15-20 minutes

### Test All 600 Files

```bash
python3 tools/test_bl_newspaper_ocr.py \
    --pdf-dir "/home/jic823/ocr_bldata/25439023/BLN600/pdf" \
    --gt-dir "/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth" \
    --output ./bl_ocr_test_full \
    --all \
    --delay 1.5
```

**Expected runtime**: ~2-3 hours
**Estimated cost**: ~$0.60-1.20 (600 images × ~$0.001-0.002 per image)

---

## Command Line Options

```
--pdf-dir PATH          Directory containing PDF files (required)
--gt-dir PATH           Directory containing ground truth files (required)
-o, --output PATH       Output directory for results (required)
-n, --sample-size N     Number of files to test (default: 50)
--all                   Process all files (ignores sample-size)
--delay SECONDS         Delay between API calls (default: 1.0)
--seed N                Random seed for sampling (default: 42)
-m, --model NAME        Gemini model (default: gemini-2.0-flash-exp)
-k, --api-key-file      Path to API key file
-d, --debug             Enable debug logging
```

---

## Output Files

After running, the output directory contains:

### Summary Files
- **`ocr_test_report.md`** - Human-readable summary report with statistics
- **`ocr_test_results.csv`** - CSV with all results for analysis
- **`bl_ocr_test_TIMESTAMP.log`** - Detailed processing log

### Individual Results (per file)
- **`FILEID_result.json`** - Full comparison with metrics and both texts
- **`FILEID_ocr.txt`** - Just the OCR output text

### Example Report Contents
```
## Summary Statistics
- Total Files Processed: 10
- Successfully Evaluated: 10
- Failed: 0
- No Ground Truth: 0

## Accuracy Metrics
- Average CER: 3.45%
- Average WER: 8.21%
- CER Range: 1.2% - 8.7%

## Quality Assessment
✅ EXCELLENT - CER < 5% indicates high-quality OCR

## Best/Worst Results
[Lists files by CER for error analysis]
```

---

## Understanding the Metrics

### Character Error Rate (CER)
```
CER = (substitutions + insertions + deletions) / total_characters
```

**Quality Thresholds**:
- **<5%** = Excellent (high-quality OCR)
- **5-10%** = Good (acceptable for most purposes)
- **10-20%** = Moderate (may need correction)
- **>20%** = Poor (significant issues)

### Word Error Rate (WER)
```
WER = edit_distance_words / total_words
```

Generally higher than CER since one character error can make entire word wrong.

**Typical**: WER ≈ 2-3× CER

---

## Dependencies

Auto-installed by runner script:
- `google-generativeai` - Gemini API
- `pymupdf` (fitz) - PDF to image conversion
- `pillow` - Image handling

Optional (speeds up edit distance calculation):
- `python-Levenshtein` - Fast edit distance

```bash
# Install all at once
python3 -m pip install --break-system-packages \
    google-generativeai pymupdf pillow python-Levenshtein
```

---

## Comparison with TTJ Pipeline

### Similarities
- Same Gemini OCR approach
- Similar prompt structure for historical documents
- JSON + text output format

### Differences
| Aspect | BL Test | TTJ Pipeline |
|--------|---------|--------------|
| **Input** | Single-page PDFs | Multi-page PDFs → images |
| **Content** | Victorian crime news | Timber trade journals |
| **Validation** | Ground truth comparison | Manual review |
| **Output** | CER/WER metrics | Parsed cargo data |
| **Purpose** | OCR quality assessment | Historical data extraction |

---

## Next Steps

### 1. Initial Validation (Do This First)
```bash
./run_bl_ocr_test.sh
```

Check the 10-sample results:
- Are CER/WER metrics reasonable?
- Does OCR output look correct?
- Any systematic errors?

### 2. If Results Look Good
Run larger sample (50 or all 600) for comprehensive analysis

### 3. Error Analysis
Use the JSON results to identify:
- Common OCR mistakes (character substitutions)
- Layout issues (column confusion)
- Historical typography problems
- Poor quality originals

### 4. Apply Findings to TTJ
If BL OCR quality is good:
- Validates Gemini approach
- Similar quality expected for TTJ
- Focus on parsing improvements

If BL OCR has issues:
- Investigate differences (image quality, layout, fonts)
- Test on actual TTJ pages
- Consider OCR post-processing

---

## Cost Estimation

Using **Gemini 2.0 Flash Exp** (cheapest, fast, still high quality):

**Per Image**:
- ~1 image × ~$0.001-0.002 = $0.001-0.002

**Estimates**:
- 10 samples: ~$0.01-0.02
- 50 samples: ~$0.05-0.10
- 600 files (full dataset): ~$0.60-1.20

**Very affordable** for comprehensive testing.

---

## Troubleshooting

### "No API key found"
Create `gemini_api_key.txt` with your API key, or:
```bash
export GOOGLE_AI_API_KEY="your-key-here"
```

### "Missing dependencies"
```bash
python3 -m pip install --break-system-packages google-generativeai pymupdf pillow
```

### PDFs not converting
Check PDF structure:
```bash
pdfinfo "/home/jic823/ocr_bldata/25439023/BLN600/pdf/3200797029.pdf"
```

### Ground truth not found
Check filename matches:
```bash
# PDF: 3200797029.pdf
# Ground truth: 3200797029.txt (same ID)
```

---

## Repository Status

**These files should be committed**:
- ✅ `tools/test_bl_newspaper_ocr.py` - Testing script
- ✅ `run_bl_ocr_test.sh` - Runner script
- ✅ `BL_OCR_TEST_README.md` - This documentation

**Never commit** (add to `.gitignore`):
- ❌ Ground truth data (copyrighted)
- ❌ OCR output texts (derived from copyrighted material)
- ❌ Individual result files

**OK to commit**:
- ✅ Summary statistics (CER/WER averages)
- ✅ Anonymized error patterns
- ✅ Methodology and findings

---

## Questions?

See `OCR_TESTING_PLAN.md` for:
- Detailed methodology
- Statistical analysis approaches
- Error analysis techniques
- Comparison with other OCR engines

---

## Quick Reference

```bash
# Quick 10-sample test
./run_bl_ocr_test.sh

# Custom sample size
python3 tools/test_bl_newspaper_ocr.py \
    --pdf-dir "/home/jic823/ocr_bldata/25439023/BLN600/pdf" \
    --gt-dir "/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth" \
    --output ./results \
    --sample-size 25

# Process all 600 files
python3 tools/test_bl_newspaper_ocr.py \
    --pdf-dir "/home/jic823/ocr_bldata/25439023/BLN600/pdf" \
    --gt-dir "/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth" \
    --output ./full_results \
    --all

# View results
cat ./bl_ocr_test_results/ocr_test_report.md
```
