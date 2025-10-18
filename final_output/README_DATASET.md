# Timber Trades Journal (TTJ) Dataset - 1874-1899
## Parsed Ship Arrival Records from Historical Trade Journals

**Generated:** October 17, 2025
**Source Material:** Timber Trades Journal OCR text files (659 files, 244 document groups)
**Coverage:** 1874-1899 (25 years of British timber trade data)

---

## Dataset Overview

This dataset contains **35,870 ship arrival records** extracted from the Timber Trades Journal, documenting timber and wood product imports to British ports during the late 19th century. The data has been parsed from OCR text and structured into two relational CSV files for analysis.

### Key Statistics

- **Total ship arrivals:** 35,870
- **Cargo line items:** 58,602 (avg 1.6 items per ship)
- **Time period:** 1874-1899
- **Geographic coverage:** Global origin ports → British destination ports
- **Merchant records:** 82.6% of ships have merchant data
- **Cargo details:** 94.7% of ships have parsed cargo information

---

## File Structure

### 1. `ttj_shipments.csv` (35,870 records)
**One row per ship arrival**

| Field | Description | Coverage |
|-------|-------------|----------|
| `record_id` | Unique identifier (1-35870) | 100% |
| `source_file` | Original OCR filename | 100% |
| `line_number` | Line number in source file | 100% |
| `ship_name` | Name of vessel | 100% |
| `origin_port` | Port of departure | 100% |
| `destination_port` | British port of arrival | 99.4% |
| `merchant` | Receiving merchant/consignee | 82.6% |
| `arrival_day` | Day of arrival | 68.9% |
| `arrival_month` | Month of arrival | 68.9% |
| `arrival_year` | Year of arrival | 100% |
| `publication_day` | Journal publication day | 100% |
| `publication_month` | Journal publication month | 100% |
| `publication_year` | Journal publication year | 100% |
| `is_steamship` | Steam (True) vs sail (False) | 100% |
| `format_type` | Record format variant | 100% |
| `confidence` | Parser confidence score (0.7-1.0) | 100% |

**Note on dates:** Arrival dates are extracted from content when available (68.9% coverage). Publication dates are always available and provide approximate arrival timing (journals published weekly, reporting arrivals from preceding days).

### 2. `ttj_cargo_details.csv` (58,602 records)
**Multiple rows per ship - one row per cargo item**

| Field | Description | Coverage |
|-------|-------------|----------|
| `cargo_id` | Unique cargo item identifier | 100% |
| `record_id` | Links to ttj_shipments.csv | 100% |
| `source_file` | Original OCR filename | 100% |
| `line_number` | Line number in source file | 100% |
| `quantity` | Numeric quantity | ~60% |
| `unit` | Unit of measurement (pcs., bdls., fms., etc.) | ~40% |
| `commodity` | Type of wood/product | 100% |
| `merchant` | Merchant for this cargo item | ~85% |
| `raw_cargo_segment` | Original text segment (100 char limit) | 100% |

**Joining the files:** Use `record_id` to link cargo details to ship records.

---

## Data Quality

### Port Coverage
- **Destination ports:** 99.4% coverage (35,637/35,870 records)
  - Missing: 233 records (0.6%) from files starting mid-document
  - Total unique destination ports: 282
- **Origin ports:** 100% coverage
  - Total unique origin ports: 1,755 (includes OCR variants)

### Date Coverage
- **Publication dates:** 100% coverage (year, month, day from filenames)
- **Arrival dates:** 68.9% coverage (24,697/35,870 records)
  - Remaining 31.1% use publication dates as fallback
  - Publication typically ~1-7 days after arrival

### Merchant Coverage
- **82.6% of ships** have merchant data (29,619/35,870)
- Extracted from two sources:
  1. Dedicated merchant field (standard_dash and condensed formats)
  2. Cargo field parsing (early_at format with embedded merchants)

### Cargo Detail Coverage
- **94.7% of ships** have parsed cargo items (33,970/35,870)
- **58,602 total cargo line items**
- Commodities extracted with quantities and units where available
- Multiple merchants per ship handled via cargo_details table

---

## Format Types

The journal evolved through several format variants over 25 years:

### 1. Early @ Format (1874-1878)
**Pattern:** `Date Ship @ Origin,—cargo, Merchant`
**Example:** `April 27. Andreas @ Fredrikstad,—54,266 boards, Nil.`
- Merchants embedded in cargo field
- @ symbol delimits origin port

### 2. Standard Dash Format (1879-1890)
**Pattern:** `Date Ship-Origin-Cargo-Merchant`
**Example:** `Sept. 11 Essex (s)-Konigsberg-sleepers-Order`
- Dedicated merchant field
- (s) indicates steamship
- Dash-delimited structure

### 3. Condensed Format (1881+)
**Pattern:** `Ship-Origin-Cargo-Merchant` (no date prefix)
**Example:** `Fatfield (s)-Memel-sleepers, deals-Order`
- Same as standard but dates inferred from context

### 4. Transition Period (1879-1880)
- Mixed formats within same issues
- Parser handles all variants via pattern matching

---

## Parsing Methodology

### Context-Aware Line Parsing
The parser maintains **persistent context** across file boundaries to handle:

1. **Multi-page documents:** Port headers and date contexts carry across pages
2. **Port headers:** All-caps port names (e.g., "LONDON.") apply to subsequent records
3. **Date propagation:** Dates prefix first ship of each day, apply to following ships
4. **Cross-page continuity:** Records at top of pages inherit context from previous page

**Key Innovation:** Instance-level context tracking allows a single parser to process multi-page document groups sequentially, eliminating the 10.1 percentage point gap in port coverage (89.3% → 99.4%).

### Cargo Parsing
Cargo strings are parsed to extract structured items:
- **Pattern 1:** `quantity unit commodity` (e.g., "102 bgs. wood pulp")
- **Pattern 2:** `quantity commodity` (e.g., "1,300 staves")
- Handles semicolon-delimited multiple cargo items
- Extracts merchant names from segments
- Preserves raw text for verification

### Date Extraction
- **From content:** Month/day patterns in record lines and headers
- **From filenames:** Two patterns supported:
  1. Numeric: YYYYMMDD (e.g., "18790426")
  2. Descriptive: "Month Day Year" (e.g., "May 1 1875")
- Handles OCR errors (e.g., "Augus" → "August")

---

## Reference Data Sources

### Human-Transcribed Validation Data
Three Excel files provided ground truth for normalization:

1. **Export Ports.xlsx**
   - 336 canonical export port names

2. **London Timber imports data ttj.xlsx**
   - 16,594 commodity records (1883, 1889, 1897 samples)
   - Fields: Date, Port, Quantity, Unit, Product, Merchant
   - Transcribed by research team (French column names)

3. **Timber Trades Journal Data.xlsx**
   - Ship records from England & Wales, Scotland, Canada
   - Fields: Port of Entry, Date, Ship Name, Port of Origin, British Receivers

### Extracted Dictionaries
From human transcripts and parsed data:
- **974 canonical port names**
- **1,034 commodity types** (with frequency counts)
- **80 unit abbreviations** (pcs., bdls., fms., lds., doz., etc.)
- **1,755 origin port variants** (includes OCR variations)
- **282 destination port variants**

Dictionary files in: `/reference_data/*.json`

---

## Top Commodities (from cargo parsing)

| Rank | Commodity | Frequency |
|------|-----------|-----------|
| 1 | firewood | 1,849 |
| 2 | deals | 1,562 |
| 3 | timber | 1,447 |
| 4 | oak timber | 1,433 |
| 5 | pipe staves | 1,422 |
| 6 | birch timber | 1,397 |
| 7 | white pine timber | 1,384 |
| 8 | lathwood | 1,314 |
| 9 | pitwood | 1,275 |
| 10 | deals and battens | 1,261 |

**Full commodity list:** See `/reference_data/commodities.json`

---

## Top Origin Ports

| Rank | Port | Ship Arrivals |
|------|------|---------------|
| 1 | Riga | 1,970 |
| 2 | Gothenburg | 1,417 |
| 3 | Oresund | 1,409 |
| 4 | Quebec | 1,374 |
| 5 | Cronstadt | 1,205 |
| 6 | New York | 1,086 |
| 7 | Christiania | 947 |
| 8 | Sundswall | 908 |
| 9 | Bordeaux | 821 |
| 10 | Memel | 713 |

**Geographic diversity:** Baltic (Riga, Memel, Danzig), Scandinavia (Gothenburg, Christiania), North America (Quebec, New York), France (Bordeaux)

---

## Research Applications

### Supply Chain Analysis
- **Port-to-port trade routes:** Origin → destination patterns
- **Commodity specialization:** Which ports exported which products
- **Merchant networks:** Who handled which commodities from which origins
- **Temporal patterns:** Seasonal variations, long-term trends (1874-1899)

### British Trade Networks
- **Regional specialization:** Different British ports sourcing from different regions
- **Competitive dynamics:** Multiple merchants in same commodity/port combinations
- **Technology adoption:** Steamship vs sail patterns over time
- **Volume metrics:** Quantities (where recorded) show trade scale

### Comparative Analysis
- **Human-transcribed validation:** 16,594 London records (1883, 1889, 1897) for OCR accuracy testing
- **Cross-reference:** Compare parsed data against manual transcriptions
- **Quality metrics:** Validate commodity extraction, port normalization

---

## Known Limitations

### OCR Challenges
1. **Port name variants:** 1,755 unique origin ports include OCR spelling variations
   - Example: "Fredrikstad" vs "F'stad" vs "Frederikstad"
   - **Mitigation:** Reference dictionaries for fuzzy matching

2. **Quantity precision:** Numbers may have OCR errors
   - Example: "1,300" might be "1,800" in original
   - **Mitigation:** Validate against human-transcribed samples

3. **Commodity normalization:** 1,034 commodity types include variations
   - Example: "deals" vs "deal" vs "sawn fir deals"
   - **Mitigation:** Keyword-based grouping for analysis

### Data Gaps
1. **Missing destination ports:** 233 records (0.6%)
   - Cause: Files starting mid-document, no port header
   - Workaround: Use filename metadata or context from previous files

2. **Missing arrival dates:** 11,173 records (31.1%)
   - Cause: Condensed format lacks date prefixes
   - Workaround: Use publication dates (within 1-7 days of arrival)

3. **Missing merchants:** 6,251 records (17.4%)
   - Cause: "Order" placeholders or cargo without merchant info
   - Impact: Reduced network analysis scope for these records

### Format Complexity
1. **Units inconsistency:** Same commodity measured in different units
   - Example: deals in "pcs." vs "doz." vs "stds."
   - **Not normalized to cubic meters** due to conversion complexity
   - Recommendation: Focus on commodity types and ship counts rather than volume aggregation

2. **Merchant parsing:** Some merchants truncated or incomplete
   - Example: "H. & R." instead of "H. & R. Fowler"
   - Cause: Punctuation-based pattern matching
   - Impact: May require manual merchant name consolidation

---

## Technical Implementation

### Tools and Scripts
Located in `/tools/` directory:

1. **`ttj_parser_v3.py`** - Core parser with context awareness
   - Pattern matching for three format types
   - Persistent port/date context tracking
   - Publication date extraction from filenames

2. **`batch_parse_multipage.py`** - Batch processor
   - Groups multi-page documents
   - Processes 244 document groups sequentially
   - Maintains context across page boundaries

3. **`cargo_parser.py`** - Cargo detail extractor
   - Quantity/unit/commodity parsing
   - Merchant name extraction
   - Handles complex multi-item cargo strings

4. **`extract_reference_dictionaries.py`** - Reference data extractor
   - Processes Excel validation files
   - Generates canonical port/commodity lists
   - Analyzes parsed data for normalization

5. **`generate_two_csv_output.py`** - Final output generator
   - Creates shipments and cargo_details CSVs
   - Links records via record_id
   - Handles merchant field merging

### Processing Pipeline
```
OCR Text Files (659 files)
    ↓
Group Multi-page Documents (244 groups)
    ↓
Parse with Context Tracking (ttj_parser_v3.py)
    ↓
Extract Cargo Details (cargo_parser.py)
    ↓
Generate Two CSVs (generate_two_csv_output.py)
    ↓
ttj_shipments.csv + ttj_cargo_details.csv
```

### Performance Metrics
- **Processing time:** ~5 minutes for 659 files
- **Success rate:** 100% (0 failures)
- **Memory usage:** Handles files with 1M+ character fields
- **Output size:**
  - ttj_shipments.csv: ~7 MB
  - ttj_cargo_details.csv: ~12 MB

---

## Version History

### v1.0 (October 17, 2025)
- Initial release
- 35,870 ship records parsed
- 58,602 cargo line items extracted
- 99.4% destination port coverage
- 100% publication date coverage
- Two-CSV relational structure

### Future Enhancements (Planned)
1. **Fuzzy matching normalization**
   - Map 1,755 origin port variants to canonical 974 ports
   - Consolidate commodity synonyms
   - Standardize merchant names

2. **Single-CSV option**
   - Aggregate cargo items into commodity lists
   - One row per ship for simplified analysis
   - Preserve two-CSV structure for detailed work

3. **GIS integration**
   - Geocode ports for spatial analysis
   - Route mapping visualization
   - Distance calculations

---

## Citation

If you use this dataset in your research, please cite:

```
Timber Trades Journal Ship Arrival Dataset, 1874-1899.
Parsed from Timber Trades Journal digitized collections.
Dataset compiled by [Your Research Team], October 2025.
```

**Source material:** Timber Trades Journal, London (1874-1899)
**OCR processing:** Google Gemini Pro 2.5
**Parsing system:** Claude Code (Anthropic)

---

## Contact and Collaboration

**Research Team:**
- Primary researcher: [Your Name/Institution]
- Collaboration: Stéphane (Université du Québec à Trois-Rivières)

**Dataset Location:**
- Primary: `/home/jic823/TTJ Forest of Numbers/final_output/`
- Parsed source: `/home/jic823/TTJ Forest of Numbers/parsed_output/`
- Reference data: `/home/jic823/TTJ Forest of Numbers/reference_data/`

**For questions or collaboration:**
- Dataset issues: Check `/final_output/README_DATASET.md` (this file)
- Technical documentation: See `/tools/*.py` source code
- Validation data: See Excel files in root directory

---

## Acknowledgments

- **Source journals:** Timber Trades Journal (1874-1899)
- **Digitization:** Historical journal preservation projects
- **OCR processing:** Google Gemini Pro 2.5 API
- **Human transcription:** Research team validation samples
- **Parsing development:** Claude Code (Anthropic AI assistant)

---

**Last updated:** October 17, 2025
**Dataset version:** 1.0
**File count:** 2 CSV files + reference dictionaries
