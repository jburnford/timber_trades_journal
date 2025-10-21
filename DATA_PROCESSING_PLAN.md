# TTJ Data Processing Plan - Complete Pipeline Documentation

## Overview
This document describes the complete data processing pipeline for the Timber Trades Journal (TTJ) OCR project, processing 1,866 OCR'd pages covering 1874-1899.

**Date**: October 20, 2025
**Status**: Executing Step 1 (Parsing)
**Previous Processing**: Based on 1,293 OCR files (62,991 shipments)
**New Processing**: Full dataset of 1,866 OCR files (~100K shipments estimated)

---

## Pipeline Architecture

### Data Flow
```
Raw OCR Text Files (1,866 .txt files)
    ↓
[STEP 1] Parse OCR → Structured Shipment Records
    ↓
[STEP 2] Generate Two CSVs → Shipments + Cargo Details
    ↓
[STEP 3] Apply Port Normalization → Authority-Normalized Data
    ↓
[STEP 4] Analyze New Ports → Generate Review File
    ↓
Final Output: Analysis-Ready Dataset
```

---

## Step 1: Parse OCR Files

### Script
`tools/batch_parse_multipage.py`

### Purpose
Parse raw Gemini OCR text files into structured shipment records, handling multi-page documents and maintaining context across page boundaries.

### Input
- **Directory**: `ocr_results/gemini_full/`
- **Files**: 1,866 OCR text files
- **Format**: Raw OCR output from Gemini 2.5 Pro Vision model
- **Document Groups**: 826 (files grouped by base document, handling multi-page splits)

### Processing Logic
1. **Group multi-page files**: Files like `18830106p.12_p001.txt`, `18830106p.12_p002.txt` are treated as one document
2. **Sequential processing**: Pages processed in order to maintain context
3. **Extract shipment data**: Parse using TTJContextParser (v3)
   - Ship name
   - Origin port
   - Destination port
   - Cargo description
   - Merchant names
   - Arrival dates (if available)
   - Publication dates (from filename)
   - Steamship indicator
   - Format type (standard, condensed, etc.)
   - Confidence score

### Output
- **File**: `parsed_output/ttj_shipments_multipage.csv`
- **Expected Records**: ~90,000-100,000 shipments (up from 62,991)
- **Fields**:
  - `source_file`, `line_number`, `ship_name`, `origin_port`, `destination_port`
  - `cargo`, `merchant`, `arrival_day`, `arrival_month`, `arrival_year`
  - `publication_day`, `publication_month`, `publication_year`
  - `is_steamship`, `format_type`, `confidence`, `raw_line`

### Key Features
- **Multi-page awareness**: Maintains context across page boundaries
- **Date extraction**: Pulls arrival dates from text when available
- **Publication date**: Extracted from filename (YYYYMMDD pattern)
- **Format detection**: Identifies different TTJ table formats over time

---

## Step 2: Generate Two CSV Files

### Script
`tools/generate_two_csv_output.py`

### Purpose
Split parsed data into two related CSVs: one for ship arrivals, one for individual cargo items.

### Input
- **File**: `parsed_output/ttj_shipments_multipage.csv`

### Processing Logic
1. **Parse cargo field**: Use CargoParser to extract individual cargo items from combined cargo string
2. **Generate shipments CSV**: One row per ship arrival (basic fields only)
3. **Generate cargo details CSV**: One row per cargo item (parsed from cargo field)
   - Extracts: quantity, unit, commodity, merchant (if item-specific)
   - Links to ship via `record_id`

### Outputs

#### File 1: `final_output/ttj_shipments.csv`
**Structure**: One row per ship arrival
**Fields**:
- `record_id` (auto-generated)
- `source_file`, `line_number`
- `ship_name`, `origin_port`, `destination_port`
- `merchant` (ship-level merchant if available)
- `arrival_day`, `arrival_month`, `arrival_year`
- `publication_day`, `publication_month`, `publication_year`
- `is_steamship`, `format_type`, `confidence`

**Expected**: ~90-100K records

#### File 2: `final_output/ttj_cargo_details.csv`
**Structure**: One row per cargo item
**Fields**:
- `cargo_id` (auto-generated)
- `record_id` (links to shipments table)
- `source_file`, `line_number`
- `quantity`, `unit`, `commodity`
- `merchant` (item-level or inherited from ship)
- `raw_cargo_segment` (original text)

**Expected**: ~140-160K records (avg 1.5-1.6 cargo items per ship)

### Why Two CSVs?
- **Shipments**: Enables ship-level analysis (routes, frequency, timing)
- **Cargo Details**: Enables commodity-level analysis (volumes, trade patterns)
- **Relational**: Linked via `record_id` for complex queries

---

## Step 3: Apply Port Normalization

### Script
`tools/apply_normalization.py`

### Purpose
Normalize port names using human-reviewed mapping decisions, ensuring consistency for analysis.

### Input Files
1. **Data**: `final_output/ttj_shipments.csv` (from Step 2)
2. **Review Decisions**: `final_output/authority_normalized/ports_completed.csv`
3. **Canonical Lists**:
   - `reference_data/canonical_origin_ports.json`
   - `reference_data/canonical_destination_ports.json`

### Normalization Strategy (Three-Tier)

#### Tier 1: Human-Reviewed Decisions (Highest Priority)
**Source**: `ports_completed.csv` - Your completed port review work

Three action types:
1. **ACCEPT**: Port name verified as legitimate
   - Example: "Oresund" → ACCEPT (Øresund Sound, legitimate reporting point)
   - Action: Add to canonical list, keep as-is

2. **MAP**: Port name mapped to canonical form
   - Example: "Memel" → MAP to "Klaipeda" (known historical variant)
   - Example: "Cronstadt" → MAP to "Kronstadt"
   - Action: Replace with canonical name

3. **ERROR**: OCR error, remove from dataset
   - Example: Garbled text recognized as port name
   - Action: Set field to empty string

#### Tier 2: Automatic Fuzzy Matching
For ports NOT in human review file:
- **Exact match**: Port exactly in canonical list → keep as-is
- **Variant match**: Port in known variant map → apply mapping
- **Fuzzy high confidence** (≥90% similarity): Auto-normalize
- **Fuzzy medium** (85-89% similarity): Auto-normalize with caution
- **Fuzzy low** (<85%): Flag for human review

#### Tier 3: Unchanged
Ports that don't match anything → left unchanged, flagged for review

### Processing Logic
```python
For each port in dataset:
    1. Check if in ERROR list → remove (set to empty)
    2. Check if in MAP decisions → apply mapping
    3. Check if in ACCEPT decisions → add to canonical, keep as-is
    4. Check if exact match in canonical → keep as-is
    5. Check if in variant map → apply variant mapping
    6. Try fuzzy matching against canonical:
       - If ≥85% similarity → normalize
       - Else → flag for review
```

### Outputs

#### Data Files
1. **`ttj_shipments_authority_normalized.csv`**
   - Same structure as input
   - Port names normalized
   - Expected: ~90-100K records

2. **`ttj_cargo_details_authority_normalized.csv`**
   - Copy of cargo details (ports normalized via shipments link)
   - Expected: ~140-160K records

#### Statistics
**`normalization_stats.json`**
- Total ships processed
- Origin ports: auto-normalized, human-mapped, human-accepted, errors
- Destination ports: auto-normalized, human-mapped, human-accepted, errors

### Example Mappings Applied

**Origin Ports**:
- Memel → Klaipeda (713 ships)
- Archangel → Arkhangelsk (558 ships)
- Dram → Drammen (228 ships)
- Drontheim → Trondheim (106 ships)

**Destination Ports**:
- LONDON → London (3,336 ships)
- SURREY COMMERCIAL DOCKS → London (Surrey Commercial Docks) (2,001 ships)
- MILLWALL DOCKS → London (Millwall Docks) (466 ships)
- BO'NESS → Borrowstounness (287 ships)

---

## Step 4: Analyze New Unreviewed Ports

### Script
`tools/normalize_with_authority_review.py` (analysis mode)

### Purpose
Identify port names that weren't in your original review and need human decisions.

### Processing Logic
1. **Load human-reviewed ports**: All ports from `ports_completed.csv`
2. **Scan normalized data**: Find all unique port names
3. **Identify new ports**: Ports NOT in reviewed set
4. **For each new port**:
   - Count frequency (number of ships)
   - Determine year range (first/last occurrence)
   - Attempt fuzzy matching to canonical lists
   - Categorize by confidence level
5. **Generate review file**: CSV for human review

### Output
**File**: `final_output/authority_normalized/ports_for_review_NEW.csv`

**Structure**:
- `port_type` (origin/destination)
- `original_port` (as appears in data)
- `ship_count` (frequency)
- `best_match_canonical` (auto-suggested match)
- `similarity_score` (confidence of match)
- `normalization_tier` (exact/variant/fuzzy_high/fuzzy_medium/fuzzy_low/unmapped)
- `year_range` (first-last occurrence)
- `action` (ACCEPT/MAP/ERROR - blank for human to fill)
- `map_to_port` (canonical name - blank for human to fill)
- `notes` (human notes)
- `web_search_query` (pre-populated search term)

### Expected New Ports
**Estimate**: 50-100 new port variants
- New years (1891-1899) may introduce new ports or spelling variants
- OCR from later years may have different formatting
- Some legitimate new ports as trade routes evolved

---

## Data Quality Expectations

### From 1883 Validation Study

Based on validation against human-transcribed 1883 London imports (1,769 matched pairs):

#### Categorical Fields (Excellent)
- **Ports**: 94% perfect matches, 6% minor variations (typos, abbreviations)
- **Commodities**: 93% perfect matches, 7% variations (plural/singular)
- **Units**: 97% exact or similar matches

**Port Error Types**:
- 85% are 1-2 character differences (Fredrikstadt/Fredrikstad)
- 15% are substring matches (Liscomb/Liscombe)
- Fuzzy matching handles these excellently

**Commodity Error Types**:
- 91% are plural/singular differences (sleeper/sleepers)
- 8% are compound term variations
- <1% are actual typos

#### Numerical Fields (Moderate)
- **Quantities**: 37.6% exact matches, 44.3% within 10%
- **Large errors**: 55% of non-exact matches differ by >50%
- **First digit wrong**: 75% of errors have incorrect first digit

**Implications**:
- Categorical data reliable for analysis
- Quantities useful for aggregate trends, not individual precision
- Manual verification recommended for quantity-dependent research

---

## Processing History

### Previous Processing (Oct 17-19, 2025)
- **OCR Files**: 1,293
- **Parsed Shipments**: 62,991
- **Cargo Items**: 97,468
- **Port Normalization**: Applied with human review
- **Reviewed Ports**: ~50 variants mapped or accepted

### Current Processing (Oct 20, 2025)
- **OCR Files**: 1,866 (573 new files)
- **Expected Shipments**: ~90-100K
- **Expected Cargo Items**: ~140-160K
- **Additional Processing**: New ports will need review

### OCR Performance
- **Total Images**: 2,080 processed
- **Success Rate**: 96.9% (1,012 new + 1,003 skipped previously processed / 2,080 total)
- **Failure Rate**: 3.1% (65 failed)
- **Processing Time**: 33.9 hours (122,018 seconds)
- **Average Speed**: 119.5 seconds per page

---

## File Organization

### Input Directories
```
ocr_results/gemini_full/          # Raw OCR text files (1,866 files)
reference_data/                    # Canonical port lists
final_output/authority_normalized/ # Human review decisions
```

### Output Directories
```
parsed_output/                     # Step 1 output
  └── ttj_shipments_multipage.csv

final_output/                      # Steps 2 output
  ├── ttj_shipments.csv
  └── ttj_cargo_details.csv

final_output/authority_normalized/ # Step 3 & 4 output
  ├── ttj_shipments_authority_normalized.csv
  ├── ttj_cargo_details_authority_normalized.csv
  ├── normalization_stats.json
  └── ports_for_review_NEW.csv (if new ports found)
```

---

## Next Steps After Pipeline Completion

### Immediate
1. **Review new ports**: Check `ports_for_review_NEW.csv` if generated
2. **Validate statistics**: Review `normalization_stats.json`
3. **Spot-check data**: Sample records from normalized CSVs

### Analysis Phase
1. **Temporal trends**: Track trade volumes by year
2. **Route analysis**: Origin-destination pairs, changes over time
3. **Commodity patterns**: What was traded when/where
4. **Port specialization**: Which ports handled which commodities
5. **Merchant networks**: Track trading companies across routes

### Quality Assurance
1. **Compare to previous run**: Verify ~40K new records make sense
2. **Check year coverage**: Ensure 1891-1899 well represented
3. **Port distribution**: Verify new ports are legitimate
4. **Duplicate detection**: Check for any processing artifacts

---

## Key Scripts Reference

### Core Processing Scripts
1. `batch_parse_multipage.py` - OCR text → structured records
2. `generate_two_csv_output.py` - Split into shipments + cargo
3. `apply_normalization.py` - Apply port normalization
4. `normalize_with_authority_review.py` - Analyze unreviewed ports

### Supporting Scripts
- `ttj_parser_v3.py` - Core parsing logic (contextual parser)
- `cargo_parser.py` - Parse cargo strings into items
- `PortNormalizer` class in `normalize_with_authority_review.py`

### Validation Scripts (from Oct 19)
- `prepare_validation_data.py` - Export human/auto data for comparison
- `match_cargo_records.py` - Fuzzy match with 14-day date window
- `analyze_quantity_accuracy.py` - Detailed accuracy metrics

---

## Methodology Notes

### Why This Approach?

1. **Two-CSV Structure**: Enables both ship-level and commodity-level analysis
2. **Human-in-the-Loop**: Port normalization requires domain expertise
3. **Three-Tier Normalization**: Balances automation and human oversight
4. **Fuzzy Matching**: Handles historical spelling variations
5. **Relational Design**: Maintains data relationships via IDs

### Lessons from 1883 Validation

1. **Date windows work better than exact matching**: 14-day window yielded 4.9x more matches
2. **Categorical data is highly accurate**: 93-94% perfect matches
3. **Quantities need caution**: Only 44% within 10%, use for trends not precision
4. **OCR limitations are structural**: Not just character errors, but parsing issues
5. **Human transcription has errors too**: Found 1889 data in "1883" spreadsheet

### Known Limitations

1. **Quantity accuracy**: ~38% exact, ~44% within 10%
2. **Arrival dates**: Only ~49% of records have extracted arrival dates
3. **Publication dates**: Used as fallback (51% of records)
4. **OCR failures**: 3.1% of pages failed processing
5. **Format variations**: Earlier years have different table formats

---

## Success Criteria

### Data Completeness
- ✓ All 1,866 OCR files processed
- ✓ ~90-100K shipment records extracted
- ✓ ~140-160K cargo items parsed
- ✓ All recognized port names normalized

### Data Quality
- ✓ >90% of ports auto-normalized or reviewed
- ✓ Consistent port naming across dataset
- ✓ Cargo items properly linked to shipments
- ✓ Date fields populated (arrival or publication)

### Deliverables
- ✓ Two analysis-ready CSV files
- ✓ Normalization statistics
- ✓ New port review file (if needed)
- ✓ Processing documentation (this file)

---

## Contact & Maintenance

**Project**: TTJ Forest of Numbers - Timber Trade Historical Analysis
**Processing Date**: October 20, 2025
**Workflow**: Established and validated October 17-19, 2025
**Validation**: 1883 London imports (1,769 matched pairs, 70% precision)

**Notes**:
- This pipeline is repeatable and can be re-run if new OCR files added
- Port review file can be iteratively updated as new ports discovered
- Methodology documented for publication/replication
