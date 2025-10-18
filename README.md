# Timber Trades Journal Historical Dataset

**A comprehensive dataset of timber shipments to Britain from the 1870s-1890s, extracted from the Timber Trades Journal using OCR and LLM parsing.**

## Project Overview

This repository contains tools and processed data from the Timber Trades Journal, a historical trade publication documenting timber shipments arriving at British ports. The dataset captures:

- **32,198 ship arrival records** (after deduplication)
- **53,829 cargo detail records**
- Coverage: 1874-1888 (with gaps)
- Origins: Global timber ports (Norway, Sweden, Canada, Russia, France, Spain, etc.)
- Destinations: British ports (primarily London, Liverpool, Hull, Sunderland)

## Dataset Files

### Primary Datasets (Cleaned & Deduplicated)

Located in `final_output/deduped/`:

- **`ttj_shipments_deduped.csv`** - 32,198 ship arrival records
  - Ship name, origin port, destination port, arrival date
  - Source file references for verification

- **`ttj_cargo_details_deduped.csv`** - 53,829 cargo records
  - Linked to shipments via `record_id`
  - Commodity types, quantities, units, merchants

### Data Quality

- **Duplicates removed:** 3,672 records (10.2%) - LLM OCR hallucinations documented
- **Port normalization:** 92.8% complete (108/301 ports normalized)
- **Documentation:** Comprehensive methods documentation for reproducibility

## Repository Structure

```
timber_trades_journal/
├── tools/                          # Processing pipeline
│   ├── process_pdf_for_ocr.py     # Image preprocessing
│   ├── gemini_ocr_processor.py    # OCR with Gemini
│   ├── ttj_parse.py               # Data extraction
│   ├── deduplicate_all_patterns.py # Remove LLM duplicates
│   └── normalize_with_authority_review.py # Port normalization
├── final_output/                   # Processed datasets
│   ├── deduped/                   # Primary cleaned dataset
│   ├── authority_normalized/      # Port normalization work
│   └── OCR_DUPLICATION_ISSUES.md  # Methods documentation
├── reference_data/                 # Canonical port lists
└── README_OCR_PIPELINE.md         # Technical documentation
```

## Data Pipeline

### 1. Image Preprocessing
- Extract pages from PDFs at 300 DPI
- Detect and correct rotation (Hough transform)
- Apply OCR enhancements (denoising, contrast, sharpening)

### 2. OCR Processing
- Google Gemini Pro 2.5 Vision model
- Structured output extraction
- Error handling for LLM hallucinations

### 3. Data Extraction
- Parse ship arrival records
- Extract cargo details (commodity, quantity, unit)
- Link merchants and source files

### 4. Data Cleaning
- **Deduplication:** Remove LLM repetition errors (signature-based)
- **Port Normalization:** Map variants to canonical names
- **Outlier Cleanup:** Remove parsing errors and anomalies

## Known Issues & Limitations

### OCR Errors
- **LLM Hallucinations:** 3,672 duplicate records removed (see `OCR_DUPLICATION_ISSUES.md`)
- **1879 Format Issue:** 350 records with commodity ("PITWOOD") as destination port
- **Port Name Variants:** 193 ports still require human review

### Coverage Gaps
- **Temporal:** Inconsistent coverage (1874-1888 with missing years)
- **Spatial:** Origin ports - 3 years; Destination ports - 1 year (1888)
- **Format Changes:** Journal format evolved, affecting parsing consistency

## Usage

### Quick Start

```python
import pandas as pd

# Load cleaned dataset
ships = pd.read_csv('final_output/deduped/ttj_shipments_deduped.csv')
cargo = pd.read_csv('final_output/deduped/ttj_cargo_details_deduped.csv')

# Example: Top origin ports
ships['origin_port'].value_counts().head(10)

# Example: Cargo by commodity
cargo.groupby('commodity')['quantity'].sum()
```

### Port Normalization

The `authority_normalized/` directory contains ongoing port normalization work:
- `ports_completed.csv` - 108 normalized ports (19,590 ships)
- `ports_for_review2.csv` - 193 ports needing human review (1,515 ships)
- `CANONICAL_PORTS_REFERENCE.md` - Authoritative port name list

## Processing New Data

To process the 1891-1899 batch:

```bash
cd tools
./process_1891_1899_batch.sh  # Preprocess images
# Wait for Gemini API budget approval before OCR
```

## Citation

If you use this dataset in your research, please cite:

```
Timber Trades Journal Historical Dataset (1874-1888)
Extracted from digitized journal pages using OCR and LLM parsing
GitHub: https://github.com/jburnford/timber_trades_journal
```

## Methodology Paper

Comprehensive documentation of:
- OCR pipeline design
- LLM hallucination patterns
- Deduplication methodology
- Port normalization workflow

Available in: `final_output/OCR_DUPLICATION_ISSUES.md`

## Contributing

- **Port Normalization:** Help review remaining 193 ports
- **Parsing Improvements:** Better handling of format variations
- **Additional Years:** Process 1891-1899 batch when ready

## License

**Dataset:** Public domain (historical documents)
**Code:** MIT License (see LICENSE)

## Acknowledgments

- **Source:** Timber Trades Journal (1870s-1890s)
- **Digitization:** Archive.org / Internet Archive
- **OCR:** Google Gemini Pro 2.5 Vision
- **Processing:** Claude Code (Anthropic)

---

**Last Updated:** October 17, 2025
**Dataset Version:** 1.0-deduped
**Status:** Port normalization in progress (92.8% complete)
