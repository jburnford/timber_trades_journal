# Recovery Plan: Extracting Missed Ships from High Character Count Records

## Problem Statement

Analysis of `ttj_shipments_final.csv` reveals that **1,664 records (1.1%)** have character counts >300, indicating multiple ship records were concatenated into single CSV rows. The parser extracted only the first ship from each multi-ship line.

## Key Findings

### Distribution
- **Total records**: 152,984
- **Normal records (0-300 chars)**: 151,320 (98.9%)
- **High-count records (>300 chars)**: 1,664 (1.1%)
- **Average ships per high-count record**: 4.75 (based on @ symbol count)
- **Estimated missed ships**: **6,000-10,000+**

### Critical Cases

**Case 1: Massive Page Concatenation**
- Files: `11. 171-173 - September 15 1877_p002.txt`
- Character counts: 176,908 and 176,045 chars
- Ships per record: **1,389 and 1,377** ships
- Problem: Entire multi-page documents concatenated into single records
- These 2 records alone contain **2,766 ships**!

**Case 2: Standard Multi-Ship Concatenation**
- Character counts: 2,000-4,500 chars
- Ships per record: 30-60 ships
- Format: Normal `Ship @ Port,—cargo, merchant` repeated
- Problem: Parser only extracted first ship, rest concatenated

**Case 3: Format Variant (Hyphen-Based)**
- File: `18990128p.121_p001.txt`
- Character count: 15,235 chars
- Format: `Toledo (s)-Riga-1,715 deals-Wilson & Son ; 5,118 deal ends-Wilson & Son ; ...`
- Uses HYPHENS (-) instead of em-dashes (—)
- Uses SEMICOLONS (;) to separate entries
- Problem: Different format not recognized by parser

## Root Causes

1. **Multi-page Parsing Failure**: Multi-page documents (p002, p003) failed to split properly
2. **Single-Ship Extraction**: Parser extracted only first ship from concatenated lines
3. **Format Variants**: Hyphen-based format not recognized
4. **No Line Splitting**: Parser didn't split on ship boundaries within a single line

## Recovery Strategy

### Phase 1: Triage and Categorization (Quick)

**Objective**: Categorize the 1,664 high-count records by type

**Script**: `tools/categorize_high_count.py`

**Categories**:
1. **MEGA (>10,000 chars)**: Entire pages (152 records)
2. **HIGH (1,000-10,000 chars)**: Large multi-ship blocks (409 records)
3. **MEDIUM (500-1,000 chars)**: Medium multi-ship blocks (352 records)
4. **LOW (300-500 chars)**: Small multi-ship blocks (751 records)

**Actions**:
- Count @ symbols and — dashes in each
- Identify format variants (hyphen vs em-dash)
- Estimate ships per record
- Priority ranking for recovery

### Phase 2: Extract from Standard Format (Medium Priority)

**Target**: Records with 300-10,000 chars using standard format (@ and —)

**Estimated Recovery**: 3,000-4,000 ships

**Approach**: Multi-ship line splitter
```python
def split_concatenated_ships(raw_line: str, port: str) -> List[ShipRecord]:
    """
    Split concatenated ships using @ as boundary marker.
    Format: Ship1 @ Port1,—cargo1, merchant1. Ship2 @ Port2,—cargo2, merchant2.
    """
    # Find all @ positions
    at_positions = [i for i, c in enumerate(raw_line) if c == '@']

    # Extract ship before each @, parse cargo/merchant after
    ships = []
    for i, at_pos in enumerate(at_positions):
        # Find ship name (text before @)
        start = find_previous_boundary(raw_line, at_pos)
        ship_name = raw_line[start:at_pos].strip()

        # Find port and cargo (text after @)
        end = at_positions[i+1] if i+1 < len(at_positions) else len(raw_line)
        remainder = raw_line[at_pos+1:end]

        port, cargo, merchant = parse_cargo_section(remainder)
        ships.append(ShipRecord(...))

    return ships
```

**Script**: `tools/extract_multi_ship_records.py`

### Phase 3: Extract from MEGA Records (High Priority)

**Target**: 152 records with >10,000 chars

**Estimated Recovery**: 3,000+ ships (including the 2,766 from top 2 records)

**Approach**: Treat as raw OCR text and re-parse
```python
def extract_from_mega_record(raw_line: str, source_file: str) -> List[ShipRecord]:
    """
    Re-parse MEGA records as if they were original OCR text.
    These are essentially entire pages that got concatenated.
    """
    # Split on period + capital letter (sentence boundaries)
    # Each ship record typically ends with period

    potential_ships = []
    sentences = split_sentences(raw_line)

    for sentence in sentences:
        if has_ship_pattern(sentence):  # Contains @ and —
            ship = parse_single_ship(sentence)
            if ship:
                potential_ships.append(ship)

    return potential_ships
```

**Special Handling**:
- Use existing year-specific parsers (1889, 1891, etc.)
- Extract publication year from source_file
- Route to appropriate parser based on year
- These are the files that originally timed out!

**Script**: `tools/extract_mega_records.py`

### Phase 4: Extract from Hyphen Format (Medium Priority)

**Target**: Records using hyphen (-) instead of em-dash (—)

**Estimated Recovery**: 500-1,000 ships

**Format**: `Ship (s)-Port-Cargo-Merchant ; ...`

**Approach**: Format-specific parser
```python
def extract_hyphen_format(raw_line: str) -> List[ShipRecord]:
    """
    Parse hyphen-based format with semicolon separators.
    Format: Ship-Port-Cargo-Merchant ; Ship-Port-Cargo-Merchant ; ...
    """
    # Split on semicolons
    entries = raw_line.split(';')

    ships = []
    for entry in entries:
        # Split on hyphens
        parts = entry.split('-')
        if len(parts) >= 3:
            ship = ShipRecord(
                ship_name=parts[0].strip(),
                origin_port=parts[1].strip(),
                cargo=parts[2].strip(),
                merchant=parts[3].strip() if len(parts) > 3 else ''
            )
            ships.append(ship)

    return ships
```

**Script**: `tools/extract_hyphen_format.py`

## Implementation Plan

### Step 1: Categorize (30 minutes)
```bash
python3 tools/categorize_high_count.py
# Output: analysis/high_count_categories.csv
```

### Step 2: Extract Multi-Ship (Standard Format) (2 hours)
```bash
python3 tools/extract_multi_ship_records.py
# Input: Records with 300-10,000 chars, standard format
# Output: parsed_output/multi_ship_extracted.csv
# Expected: 3,000-4,000 ships
```

### Step 3: Extract MEGA Records (4 hours)
```bash
python3 tools/extract_mega_records.py
# Input: 152 records with >10,000 chars
# Output: parsed_output/mega_records_extracted.csv
# Expected: 3,000+ ships
```

### Step 4: Extract Hyphen Format (1 hour)
```bash
python3 tools/extract_hyphen_format.py
# Input: Records with hyphen format
# Output: parsed_output/hyphen_format_extracted.csv
# Expected: 500-1,000 ships
```

### Step 5: Merge and Deduplicate (30 minutes)
```bash
python3 tools/merge_recovered_ships.py
# Combine all extracted records
# Remove duplicates (same ship, port, date, cargo)
# Append to ttj_shipments_final.csv
```

## Expected Outcomes

### Conservative Estimate
- Multi-ship standard: 3,000 ships
- MEGA records: 3,000 ships
- Hyphen format: 500 ships
- **Total: 6,500 additional ships**

### Optimistic Estimate
- Multi-ship standard: 4,000 ships
- MEGA records: 5,000 ships (those 2 massive records!)
- Hyphen format: 1,000 ships
- **Total: 10,000 additional ships**

### Final Dataset
- Current: 152,984 records
- After recovery: **159,000-163,000 records**
- **Dataset growth: 4-7%**

## Risk Mitigation

1. **Preserve Originals**: Work on copies, keep ttj_shipments_final_backup.csv
2. **Deduplication**: Check for duplicates between new and existing records
3. **Validation**: Sample-check extracted records for accuracy
4. **Incremental**: Process in phases, validate each before proceeding
5. **Tracking**: Log all extractions with source line numbers for traceability

## Success Criteria

1. Extract at least 6,000 additional ships
2. Maintain >95% accuracy on extracted records
3. No duplicates in final merged dataset
4. All 1,664 high-count records processed
5. Document extraction method for reproducibility

## Timeline

- Phase 1 (Categorize): 30 minutes
- Phase 2 (Multi-ship): 2 hours
- Phase 3 (MEGA): 4 hours
- Phase 4 (Hyphen): 1 hour
- Phase 5 (Merge): 30 minutes
- **Total: 8 hours of development + processing time**

## Next Steps

1. Review and approve this plan
2. Implement categorization script
3. Test extraction on sample of 10-20 high-count records
4. Validate results
5. Run full extraction pipeline
6. Merge and analyze final dataset
