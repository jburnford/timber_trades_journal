# TTJ Data Processing Pipeline - Complete Guide

**Purpose**: Process raw OCR text files from Timber Trades Journal (1874-1899) into clean, normalized CSV datasets for analysis.

**Last Updated**: October 20, 2025
**Dataset**: 1,866 OCR files → 68,966 unique shipment records

---

## Pipeline Overview

```
Raw OCR Files (*.txt)
    ↓
[STEP 1] Parse OCR → Extract structured records
    ↓
[STEP 2] Deduplicate → Remove OCR hallucinations
    ↓
[STEP 3] Generate CSVs → Split into shipments + cargo
    ↓
[STEP 4] Normalize Ports → Apply human review mappings
    ↓
Final Analysis-Ready Datasets
```

---

## Directory Structure

```
TTJ Forest of Numbers/
├── ocr_results/gemini_full/          # INPUT: Raw OCR text files
├── parsed_output/                     # STEP 1 output
│   └── ttj_shipments_multipage.csv
├── final_output/
│   ├── ttj_shipments.csv             # STEP 3 output (raw)
│   ├── ttj_cargo_details.csv
│   ├── deduped/                      # STEP 2 output
│   │   ├── ttj_shipments_deduped.csv
│   │   └── ttj_cargo_details_deduped.csv
│   └── authority_normalized/         # STEP 4 output
│       ├── ttj_shipments_authority_normalized.csv
│       ├── ttj_cargo_details_authority_normalized.csv
│       ├── ports_completed.csv       # Human review decisions
│       └── ports_needing_review_by_frequency.csv
├── reference_data/
│   ├── canonical_origin_ports.json
│   └── canonical_destination_ports.json
└── tools/                            # Processing scripts
    ├── batch_parse_multipage.py
    ├── deduplicate_all_patterns.py
    ├── generate_two_csv_output.py
    └── apply_normalization.py
```

---

## STEP 1: Parse OCR Files

**Script**: `tools/batch_parse_multipage.py`

### What It Does
- Reads raw OCR text files from `ocr_results/gemini_full/`
- Groups multi-page files (e.g., `file_p001.txt`, `file_p002.txt`)
- Extracts structured shipment data using context-aware parsing
- Handles commodity section headers, date extraction, port identification

### Input
- **Directory**: `ocr_results/gemini_full/`
- **Files**: 1,866 OCR text files (826 document groups)
- **Format**: Plain text output from Gemini 2.5 Pro Vision

### Output
- **File**: `parsed_output/ttj_shipments_multipage.csv`
- **Records**: ~75,000 raw shipments (before deduplication)
- **Fields**:
  - `source_file`, `line_number`, `ship_name`, `origin_port`, `destination_port`
  - `cargo`, `merchant`, `arrival_day`, `arrival_month`, `arrival_year`
  - `publication_day`, `publication_month`, `publication_year`
  - `is_steamship`, `format_type`, `confidence`, `raw_line`

### How to Run
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
python3 batch_parse_multipage.py
```

### Expected Runtime
- ~2-5 minutes for full dataset
- Processes ~300-400 files per minute

### Key Features
- **Multi-page awareness**: Maintains context across page boundaries
- **Skip headers**: Filters out 69 non-port headers (journal sections, commodities, ads)
- **City context tracking**: Attempts to prepend city names to docks (limited effectiveness)
- **Date extraction**: Pulls arrival dates from text when available, falls back to publication dates

### Common Issues
- **Commodity headers parsed as ports**: Add to SKIP_HEADERS in `ttj_parser_v3.py` (line 23-69)
- **Missing ships**: Check if port header pattern needs adjustment (line 38)
- **Encoding errors**: Accented characters may need encoding fixes

---

## STEP 2: Deduplicate Records

**Script**: `tools/deduplicate_all_patterns.py`

### What It Does
- Removes OCR hallucination duplicates (where OCR looped over same line)
- Uses signature matching: (ship_name, origin_port, destination_port, arrival_date)
- Preserves legitimate repeat voyages
- Links cargo records to deduplicated shipments

### Input
- **File**: `parsed_output/ttj_shipments_multipage.csv`

### Output
- **Shipments**: `final_output/deduped/ttj_shipments_deduped.csv`
- **Cargo**: `final_output/deduped/ttj_cargo_details_deduped.csv`
- **Stats**: `final_output/deduped/deduplication_stats.json`

### How to Run
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
python3 deduplicate_all_patterns.py
```

### Expected Results
- **Typical reduction**: 5-8% duplicates removed
- **Major pattern**: "Carl XV. from Oresund" had 1,409 duplicates (known OCR loop)
- **Output**: ~69,000 unique shipments

### Verification
After running, check for duplicates:
```bash
cd "/home/jic823/TTJ Forest of Numbers"
# Should return 1 (only the legitimate voyage)
grep "Carl XV." final_output/deduped/ttj_shipments_deduped.csv | grep "Oresund" | wc -l
```

### Important Note
**ALWAYS use the deduped files as input for subsequent steps**, not the raw parsed output.

---

## STEP 3: Generate Two CSV Files

**Script**: `tools/generate_two_csv_output.py`

### What It Does
- Reads raw parsed data (NOT used in current pipeline - we use deduped in Step 4)
- Splits into two relational tables:
  1. **Shipments**: One row per ship arrival
  2. **Cargo Details**: One row per cargo item (linked by `record_id`)
- Parses cargo strings into individual items with quantity/unit/commodity

### Input
- **File**: `parsed_output/ttj_shipments_multipage.csv`

### Outputs

#### 1. Shipments CSV
- **File**: `final_output/ttj_shipments.csv`
- **Structure**: One row per ship arrival
- **Fields**:
  - `record_id` (auto-generated, links to cargo)
  - `source_file`, `line_number`
  - `ship_name`, `origin_port`, `destination_port`
  - `merchant` (ship-level)
  - `arrival_day`, `arrival_month`, `arrival_year`
  - `publication_day`, `publication_month`, `publication_year`
  - `is_steamship`, `format_type`, `confidence`
- **Count**: ~75,000 records (raw) or ~69,000 (deduped)

#### 2. Cargo Details CSV
- **File**: `final_output/ttj_cargo_details.csv`
- **Structure**: One row per cargo item
- **Fields**:
  - `cargo_id` (auto-generated)
  - `record_id` (links to shipments table)
  - `source_file`, `line_number`
  - `quantity`, `unit`, `commodity`
  - `merchant` (item-level or inherited from ship)
  - `raw_cargo_segment` (original text)
- **Count**: ~105,000-113,000 items (avg 1.5 items per ship)

### How to Run
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
python3 generate_two_csv_output.py
```

### Expected Runtime
- ~1-2 minutes

### Why Two CSVs?
- **Shipments**: Enables route analysis, temporal patterns, ship frequency
- **Cargo**: Enables commodity analysis, volume tracking, merchant networks
- **Relational design**: Join on `record_id` for complex queries
- **Avoids duplication**: Ship data not repeated for each cargo item

### Current Pipeline Note
This step generates the raw two-CSV output, but **Step 4 should read from the deduped files**, not these raw files.

---

## STEP 4: Apply Port Normalization

**Script**: `tools/apply_normalization.py`

### What It Does
- Normalizes port names using three-tier strategy
- Applies human review decisions from `ports_completed.csv`
- Auto-normalizes using fuzzy matching against canonical lists
- Marks parsing errors for removal

### Input Files
1. **Data**: `final_output/deduped/ttj_shipments_deduped.csv` ⚠️ **MUST use deduped version**
2. **Human Review**: `final_output/authority_normalized/ports_completed.csv`
3. **Canonical Lists**:
   - `reference_data/canonical_origin_ports.json`
   - `reference_data/canonical_destination_ports.json`

### Normalization Strategy (Three-Tier)

#### Tier 1: Human Review Decisions (Highest Priority)
From `ports_completed.csv`, three action types:

**ACCEPT**: Port verified as legitimate variant
```csv
origin,Oresund,1409,,,unmapped,1885-1885,ACCEPT,,Øresund Sound - legitimate reporting point
```
→ Added to canonical list, kept as-is

**MAP**: Port mapped to canonical form
```csv
origin,Memel,713,,,unmapped,1874-1888,MAP,Klaipeda,Auto-mapped (known variant)
destination,TILBURY DOCK,355,,,unmapped,1891-1899,MAP,London (Tilbury Docks),User-mapped
```
→ Original replaced with canonical name

**ERROR**: OCR error, remove from dataset
```csv
destination,PITWOOD,350,,,unmapped,1879-1879,ERROR,,Commodity not a port
```
→ Field set to empty string

#### Tier 2: Automatic Fuzzy Matching
For ports NOT in human review:
- **Exact match**: Port in canonical list → keep as-is
- **Variant match**: Port in known variant map → apply mapping
- **Fuzzy high** (≥90% similarity): Auto-normalize
- **Fuzzy medium** (85-89% similarity): Auto-normalize with caution
- **Fuzzy low** (<85%): Leave unchanged, flag for review

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

#### 1. Normalized Shipments
- **File**: `final_output/authority_normalized/ttj_shipments_authority_normalized.csv`
- **Count**: 68,966 ships (deduplicated)
- **Coverage**:
  - Origin: 83.1% canonical
  - Destination: 91.3% canonical

#### 2. Normalized Cargo
- **File**: `final_output/authority_normalized/ttj_cargo_details_authority_normalized.csv`
- **Note**: Cargo doesn't have port fields; normalization via shipments link

#### 3. Statistics
- **File**: `final_output/authority_normalized/normalization_stats.json`
- **Contains**:
  - Total ships processed
  - Origin: auto-normalized, human-mapped, human-accepted, errors
  - Destination: auto-normalized, human-mapped, human-accepted, errors

### How to Run
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
python3 apply_normalization.py
```

### Expected Runtime
- ~1-2 minutes

### Critical Configuration Check
**VERIFY INPUT FILES** in `apply_normalization.py` (lines 216, 224):
```python
# ✅ CORRECT (uses deduped files)
input_csv = base_dir / "final_output" / "deduped" / "ttj_shipments_deduped.csv"
input_csv = base_dir / "final_output" / "deduped" / "ttj_cargo_details_deduped.csv"

# ❌ WRONG (would include duplicates)
input_csv = base_dir / "final_output" / "ttj_shipments.csv"
input_csv = base_dir / "final_output" / "ttj_cargo_details.csv"
```

**If this is wrong, you'll see 1,409 "Carl XV. from Oresund" duplicates in output.**

---

## Human Review Process

### When to Review Ports

Run analysis to identify unmapped ports:
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
python3 << 'EOF'
import csv
from collections import Counter

# Load review decisions
reviewed_ports = set()
with open('../final_output/authority_normalized/ports_completed.csv', 'r', encoding='latin-1') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['port_type'] in ['origin', 'destination']:
            reviewed_ports.add((row['port_type'], row['original_port']))

# Load original and normalized data
with open('../final_output/deduped/ttj_shipments_deduped.csv', 'r', encoding='utf-8') as f:
    original = list(csv.DictReader(f))

with open('../final_output/authority_normalized/ttj_shipments_authority_normalized.csv', 'r', encoding='utf-8') as f:
    normalized = list(csv.DictReader(f))

# Find unmapped ports
unmapped_origins = Counter()
unmapped_dests = Counter()

for i, (orig, norm) in enumerate(zip(original, normalized)):
    # Origin ports
    if orig['origin_port'] and orig['origin_port'] == norm['origin_port']:
        if ('origin', orig['origin_port']) not in reviewed_ports:
            unmapped_origins[orig['origin_port']] += 1

    # Destination ports
    if orig['destination_port'] and orig['destination_port'] == norm['destination_port']:
        if norm['destination_port']:  # Skip removed errors
            if ('destination', orig['destination_port']) not in reviewed_ports:
                unmapped_dests[orig['destination_port']] += 1

# Save to CSV
with open('../final_output/authority_normalized/ports_needing_review_by_frequency.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['port_type', 'port_name', 'ship_count'])

    writer.writerow([])
    writer.writerow(['=== DESTINATION PORTS ===', '', ''])
    for port, count in unmapped_dests.most_common():
        writer.writerow(['destination', port, count])

    writer.writerow([])
    writer.writerow(['=== ORIGIN PORTS ===', '', ''])
    for port, count in unmapped_origins.most_common():
        writer.writerow(['origin', port, count])

print(f"Unmapped origin ports: {len(unmapped_origins)}")
print(f"Unmapped destination ports: {len(unmapped_dests)}")
print("\nSaved to: ports_needing_review_by_frequency.csv")
EOF
```

### Adding Review Decisions

Append to `ports_completed.csv`:
```bash
cat >> "final_output/authority_normalized/ports_completed.csv" << 'EOF'
destination,TILBURY DOCK,355,,,unmapped,1891-1899,MAP,London (Tilbury Docks),User-mapped - London dock,
destination,QUEEN'S DOCK,326,,,unmapped,1891-1899,MAP,Hull (Queen's Dock),User-mapped - Hull dock,
destination,RUNCORN,101,,,unmapped,1891-1899,MAP,Runcorn,User-mapped - River Mersey port town,
EOF
```

Then re-run normalization:
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
python3 apply_normalization.py
```

### Review CSV Format
```csv
port_type,original_port,ship_count,best_match_canonical,similarity_score,normalization_tier,year_range,action,map_to_port,notes,web_search_query
destination,TILBURY DOCK,355,,,unmapped,1891-1899,MAP,London (Tilbury Docks),User-mapped - London dock,TILBURY DOCK British port timber 1890s
```

**Fields**:
- `port_type`: "origin" or "destination"
- `original_port`: Port name as appears in data
- `ship_count`: Frequency (prioritize high-count ports)
- `action`: ACCEPT, MAP, or ERROR
- `map_to_port`: Canonical name (if MAP)
- `notes`: Explanation of decision

---

## Quality Checks

### 1. Verify Deduplication
```bash
cd "/home/jic823/TTJ Forest of Numbers"

# Should be 1 (unique record)
grep "Carl XV." final_output/authority_normalized/ttj_shipments_authority_normalized.csv | grep "Oresund" | wc -l

# Should be 68,966 (deduped count), NOT 74,894
wc -l final_output/authority_normalized/ttj_shipments_authority_normalized.csv
```

### 2. Calculate True Coverage
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
python3 << 'EOF'
import csv
import json

# Load canonical ports
with open('../reference_data/canonical_origin_ports.json', 'r') as f:
    canonical_origin = set(json.load(f))
with open('../reference_data/canonical_destination_ports.json', 'r') as f:
    canonical_dest = set(json.load(f))

# Load normalized data
with open('../final_output/authority_normalized/ttj_shipments_authority_normalized.csv', 'r', encoding='utf-8') as f:
    normalized = list(csv.DictReader(f))

total_ships = len(normalized)
ships_with_origin = sum(1 for r in normalized if r['origin_port'])
ships_with_dest = sum(1 for r in normalized if r['destination_port'])

valid_origin = sum(1 for r in normalized if r['origin_port'] in canonical_origin)
valid_dest = sum(1 for r in normalized if r['destination_port'] in canonical_dest)

print(f"Total ships: {total_ships:,}")
print(f"\nOrigin Coverage: {valid_origin/ships_with_origin*100:.1f}% ({valid_origin:,}/{ships_with_origin:,})")
print(f"Destination Coverage: {valid_dest/ships_with_dest*100:.1f}% ({valid_dest:,}/{ships_with_dest:,})")
EOF
```

**Expected**:
- Total ships: 68,966
- Origin coverage: ~83%
- Destination coverage: ~91%

### 3. Check for Parsing Errors
```bash
cd "/home/jic823/TTJ Forest of Numbers"
grep -i "TIMBER\|CURRENT PRICES\|DIVIDENDS\|PETITION" \
  final_output/authority_normalized/ttj_shipments_authority_normalized.csv | \
  cut -d',' -f6 | sort | uniq -c | sort -rn
```

If these appear as destination ports, add them to SKIP_HEADERS in `ttj_parser_v3.py`.

---

## Adding New OCR Files - Quick Guide

### 1. Add OCR Files
Place new `.txt` files in: `ocr_results/gemini_full/`

### 2. Run Complete Pipeline
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"

# Step 1: Parse
python3 batch_parse_multipage.py

# Step 2: Deduplicate
python3 deduplicate_all_patterns.py

# Step 3: Generate CSVs (optional, not used if going straight to normalization)
python3 generate_two_csv_output.py

# Step 4: Normalize (uses deduped files)
python3 apply_normalization.py

# Step 5: Analyze unmapped ports
python3 << 'EOF'
# [Insert analysis script from "Human Review Process" section above]
EOF
```

### 3. Review New Ports
- Open: `final_output/authority_normalized/ports_needing_review_by_frequency.csv`
- Add decisions to: `final_output/authority_normalized/ports_completed.csv`
- Re-run Step 4 (normalization)

### Expected Runtime (Full Pipeline)
- Parse: 2-5 minutes
- Deduplicate: 30 seconds
- Generate CSVs: 1-2 minutes
- Normalize: 1-2 minutes
- **Total: ~5-10 minutes**

---

## Troubleshooting

### Issue: Duplicates Not Removed
**Symptom**: "Carl XV. from Oresund" appears 1,409 times

**Cause**: Normalization reading from raw files instead of deduped

**Fix**: Check `apply_normalization.py` lines 216, 224:
```python
# Should be:
input_csv = base_dir / "final_output" / "deduped" / "ttj_shipments_deduped.csv"
```

### Issue: Commodity Names as Ports
**Symptom**: "PINE", "SPRUCE", "MAHOGANY" appear as destination ports

**Cause**: Missing from SKIP_HEADERS

**Fix**: Add to `ttj_parser_v3.py` line 23-69:
```python
SKIP_HEADERS = {
    # ... existing entries ...
    'PINE', 'SPRUCE', 'MAHOGANY', 'OAK',
}
```

### Issue: Journal Headers as Ports
**Symptom**: "TIMBER TRADES JOURNAL", "CURRENT PRICES" as ports

**Cause**: Missing from SKIP_HEADERS

**Fix**: Same as above, add to SKIP_HEADERS set

### Issue: Low Coverage Percentage
**Symptom**: Coverage < 85%

**Diagnosis**:
1. Check if using deduped files (not raw)
2. Check if human review decisions applied
3. Look at unmapped port list - are they legitimate variants or errors?

**Fix**:
- Add legitimate variants to canonical lists
- Map common variants in `ports_completed.csv`
- Mark parsing errors as ERROR

### Issue: Encoding Errors (Accented Characters)
**Symptom**: "GÃ¤vle", "VÃ¤stervik" instead of "Gävle", "Västervik"

**Cause**: Mixed encodings in review CSV

**Workaround**: Currently handled in `apply_normalization.py` with multi-encoding try/except (lines 22-37)

---

## File Dependencies

### Critical Files
1. **Parser**: `tools/ttj_parser_v3.py` - Core parsing logic
   - SKIP_HEADERS set (lines 23-69)
   - Port header pattern (line 38)
   - Date header pattern (line 39)

2. **Normalization**: `tools/apply_normalization.py`
   - ⚠️ Input file paths (lines 216, 224) - MUST use deduped
   - Review file path (line 199)

3. **Human Review**: `final_output/authority_normalized/ports_completed.csv`
   - Must be updated manually with review decisions
   - Format: CSV with specific columns (see Review CSV Format above)

4. **Canonical Lists**: `reference_data/*.json`
   - Origin ports: `canonical_origin_ports.json`
   - Destination ports: `canonical_destination_ports.json`

### Generated Files (Can be Deleted and Regenerated)
- `parsed_output/ttj_shipments_multipage.csv`
- `final_output/ttj_shipments.csv`
- `final_output/ttj_cargo_details.csv`
- `final_output/deduped/*`
- `final_output/authority_normalized/ttj_shipments_authority_normalized.csv`
- `final_output/authority_normalized/ttj_cargo_details_authority_normalized.csv`

---

## Performance Notes

### Processing Speed
- **OCR**: ~119 seconds per page (Gemini 2.5 Pro)
- **Parsing**: ~300-400 files per minute
- **Deduplication**: ~30 seconds for 75K records
- **Normalization**: ~1-2 minutes for 69K records

### Data Sizes
- **Raw OCR**: 1,866 text files
- **Parsed**: ~75K shipments, ~113K cargo items
- **Deduped**: 68,966 shipments, ~105K cargo items
- **Final CSV sizes**:
  - Shipments: ~11 MB
  - Cargo: ~16 MB

---

## Validation Results (1883 Sample)

Based on validation against human-transcribed 1883 London imports:

### Categorical Fields (Excellent)
- **Ports**: 94% perfect matches
- **Commodities**: 93% perfect matches
- **Units**: 97% exact or similar

### Numerical Fields (Moderate)
- **Quantities**: 37.6% exact, 44.3% within 10%
- **Recommendation**: Use for aggregate trends, not individual precision

### Overall Quality
- Categorical data: High reliability for research
- Temporal data: Good coverage (69% arrival dates)
- Route analysis: Excellent
- Volume analysis: Aggregate trends only

---

## Summary - Complete Pipeline Command Sequence

```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"

# Parse OCR files
python3 batch_parse_multipage.py

# Remove duplicates
python3 deduplicate_all_patterns.py

# Apply port normalization (uses deduped files)
python3 apply_normalization.py

# Analyze coverage
python3 << 'EOF'
import csv, json
with open('../reference_data/canonical_origin_ports.json') as f:
    canonical_origin = set(json.load(f))
with open('../reference_data/canonical_destination_ports.json') as f:
    canonical_dest = set(json.load(f))
with open('../final_output/authority_normalized/ttj_shipments_authority_normalized.csv', encoding='utf-8') as f:
    data = list(csv.DictReader(f))
total = len(data)
origin = sum(1 for r in data if r['origin_port'])
dest = sum(1 for r in data if r['destination_port'])
valid_o = sum(1 for r in data if r['origin_port'] in canonical_origin)
valid_d = sum(1 for r in data if r['destination_port'] in canonical_dest)
print(f"Total: {total:,} | Origin: {valid_o/origin*100:.1f}% | Dest: {valid_d/dest*100:.1f}%")
EOF
```

**Expected Final Output**:
```
Total: 68,966 | Origin: 83.1% | Dest: 91.3%
```

**Final Datasets**:
- `final_output/authority_normalized/ttj_shipments_authority_normalized.csv`
- `final_output/authority_normalized/ttj_cargo_details_authority_normalized.csv`

---

**End of Documentation**
