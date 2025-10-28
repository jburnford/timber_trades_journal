# Timber Trades Journal Historical Dataset

**A comprehensive dataset of timber shipments to Britain from the 1870s-1890s, extracted from the Timber Trades Journal using OCR and LLM parsing.**

## Project Overview

This repository contains tools and processed data from the Timber Trades Journal, a historical trade publication documenting timber shipments arriving at British ports. The dataset captures:

- **69,303 ship arrival records** (after deduplication)
- **105,235 cargo detail records**
- **Coverage: 1874-1899** (26 years, near-complete)
- **Origins**: 621 ports worldwide (Norway, Sweden, Canada, Russia, France, Spain, etc.)
- **Destinations**: British ports (London, Liverpool, Grimsby, Bristol, Tyne, etc.)
- **Commodities**: 2,297 timber products (deals, staves, props, battens, timber, etc.)

## Dataset Files

### Primary Datasets (Cleaned & Normalized)

Located in `final_output/authority_normalized/`:

- **`ttj_shipments_authority_normalized.csv`** - 69,303 ship arrival records
  - Ship name, origin port, destination port, arrival date
  - Source file references for verification
  - Port names normalized to canonical forms

- **`ttj_cargo_details_artifacts_fixed.csv`** - 105,235 cargo records
  - Linked to shipments via `record_id`
  - Commodity types, quantities, units, merchants
  - Commodities normalized and parsing artifacts removed

### Analytical Datasets

Located in `final_output/analytical_datasets/`:

- **`detailed_shipments_long.csv`** - Master file with all details (one row per cargo item)
- **`trade_routes_by_year.csv`** - Geographic trade patterns by year
- **`commodity_flows_by_year.csv`** - Commodity trends over time
- **`route_commodity_matrix.csv`** - Combined route + commodity analysis
- **`port_activity_summary.csv`** - Port importance over time

### Data Quality

- **Origin port coverage:** 91.25% (63,227 of 69,293 ships normalized)
- **Destination port coverage:** 99%+ (highly standardized)
- **Commodity coverage:** 98.1% (103,192 of 105,235 records)
- **Quantity data:** 97.2% coverage
- **Documentation:** See `DATA_QUALITY_REPORT.md` for complete metrics

## Repository Structure

```
timber_trades_journal/
├── tools/                          # Processing pipeline
│   ├── process_pdf_for_ocr.py     # Image preprocessing
│   ├── gemini_ocr_processor.py    # OCR with Gemini
│   ├── ttj_parse.py               # Data extraction
│   ├── deduplicate_all_patterns.py # Remove LLM duplicates
│   ├── normalize_with_authority_review.py # Port normalization
│   ├── fix_cargo_artifacts.py     # Commodity cleaning
│   └── generate_analytical_datasets.py # Analysis-ready outputs
├── final_output/                   # Processed datasets
│   ├── deduped/                   # Deduplicated shipments/cargo
│   ├── authority_normalized/      # Normalized datasets
│   ├── analytical_datasets/       # Research-ready aggregations
│   └── OCR_DUPLICATION_ISSUES.md  # Methods documentation
├── reference_data/                 # Canonical port lists
├── DATA_QUALITY_REPORT.md         # Complete quality metrics
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
- **Port Normalization:** Map variants to canonical names (91.25% coverage)
- **Commodity Normalization:** Remove parsing artifacts, standardize terminology
- **Analytical Aggregation:** Generate research-ready datasets at multiple levels

## Data Quality

The dataset has undergone extensive quality assurance:

### Port Coverage
- **Origin ports:** 91.25% coverage (63,227 of 69,293 ships)
  - 621 canonical ports identified
  - 74 port mappings added through human review
  - 2,103 low-frequency ports remain unmapped
- **Destination ports:** 99%+ coverage (highly standardized)

### Commodity Data
- **Coverage:** 98.1% (103,192 of 105,235 records have commodities)
- **Quality:** 95%+ clean after normalization
- **Top commodities:** deals (18,537), staves (5,214), props (4,550), battens (4,134)

### Known Limitations
- **9% unmapped origin ports** (primarily low-frequency, 1-4 ships each)
- **2% commodity noise** (acceptable for historical data)
- **Merchant data:** Variable quality, not fully normalized
- **Ship names:** ~70% coverage (format variations, OCR quality)

**Complete metrics available in:** `DATA_QUALITY_REPORT.md`

## Usage

### Quick Start

```python
import pandas as pd

# Load normalized datasets
ships = pd.read_csv('final_output/authority_normalized/ttj_shipments_authority_normalized.csv')
cargo = pd.read_csv('final_output/authority_normalized/ttj_cargo_details_artifacts_fixed.csv')

# Or use analytical datasets for research
routes = pd.read_csv('final_output/analytical_datasets/trade_routes_by_year.csv')
commodities = pd.read_csv('final_output/analytical_datasets/commodity_flows_by_year.csv')

# Example: Top origin ports
ships['origin_port'].value_counts().head(10)
# Output: Riga (3,738), Archangel (2,934), Quebec (2,848), etc.

# Example: Trade routes by volume
routes.nlargest(10, 'ship_count')
# Output: New York → Liverpool (891 ships), Riga → London (721 ships), etc.

# Example: Commodity trends
commodities.pivot(index='year', columns='commodity', values='cargo_count')
```

### Analytical Datasets

Five research-ready datasets available in `final_output/analytical_datasets/`:

1. **detailed_shipments_long.csv** - Master file with complete detail (105,235 rows)
2. **trade_routes_by_year.csv** - Geographic trade patterns (20,979 routes)
3. **commodity_flows_by_year.csv** - Commodity trends (6,009 flows)
4. **route_commodity_matrix.csv** - What each route carried (50,067 combinations)
5. **port_activity_summary.csv** - Port importance rankings (7,924 entries)

### Port Normalization Reference

The `authority_normalized/` directory contains port normalization work:
- `ports_completed.csv` - 235 reviewed ports with ACCEPT/MAP/ERROR decisions
- `ports_for_user_review.csv` - 2,103 unmapped ports for human review
- `canonical_origin_ports.json` - 621 authoritative port names

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
Timber Trades Journal Historical Dataset (1874-1899)
Extracted from digitized journal pages using OCR and LLM parsing
69,303 ship arrivals | 105,235 cargo records | 621 global ports
GitHub: https://github.com/jburnford/timber_trades_journal
```

## Documentation

Comprehensive methodology and quality documentation:

- **`DATA_QUALITY_REPORT.md`** - Complete quality metrics and validation
- **`OCR_DUPLICATION_ISSUES.md`** - LLM hallucination patterns and deduplication
- **`PLAN_TO_95_PERCENT.md`** - Port normalization strategy
- **`CARGO_PARSER_IMPROVEMENT_PLAN.md`** - Commodity parsing methodology
- **`README_OCR_PIPELINE.md`** - Technical OCR pipeline documentation

## Contributing

- **Port Review:** Help classify remaining 2,103 unmapped ports
- **Data Validation:** Spot-check normalized ports and commodities
- **Additional Coverage:** Process 1891-1899 batch when ready
- **Analysis:** Use analytical datasets to discover new historical insights

## License

**Dataset:** Public domain (historical documents)
**Code:** MIT License (see LICENSE)

## Acknowledgments

- **Source:** Timber Trades Journal (1870s-1890s)
- **Digitization:** Archive.org / Internet Archive
- **OCR:** Google Gemini Pro 2.5 Vision
- **Processing:** Claude Code (Anthropic)

---

**Last Updated:** January 27, 2025
**Dataset Version:** 2.0-normalized
**Status:** Production-ready (91.25% port coverage, 98.1% commodity coverage)
