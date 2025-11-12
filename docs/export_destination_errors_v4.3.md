# Export Destination Parsing Errors Fixed - V4.3

**Date:** November 12, 2025
**Issue:** Three "export destinations" incorrectly parsed as British ports
**Solution:** OCR context analysis to distinguish parsing errors from legitimate records

---

## Problem Identified

User observation: "Look into Redwood and Quebec and New York as destinations (they are exporting ports)."

**Investigation revealed THREE distinct parsing errors:**

### 1. REDWOOD (297 records) - Commodity Section Header

**Source:** Pricing table in September 29, 1877 issue (line 12)

```
PREPARED FLOORING.
REDWOOD.
(At per square of 180 feet run.)
```

**What happened:**
- Parser captured "REDWOOD" as section header
- Incorrectly associated it with subsequent ship import listings
- Line 42: "LONDON.—From September 13th to 26th." (actual imports)
- Line 139: "HULL.—From September 13th to 25th." (actual imports)

**Evidence of parsing error:**
- All 297 records from same date: September 1877
- "Ship names" are cargo items: "logs pia.", "cedar.", "sacks chalk.", "Bark."
- Raw lines show format: "cargo. Ship.—quantity, cargo. Ship.—quantity"
- Many ships listed as "MISSING_FROM_OCR"

**Example raw lines:**
```
cedar. Coax.—112 logs, cedar. Alexander,—125 logs, cedar.
logs pia. Russian.—263 Cuban logs, 278 crowns. Nurews,—820 logs pia.
160 sacks chalk. Hero.—18 bales copra, cargo. Argocane,—2 deals
```

### 2. QUEBEC (157 records) - Correspondence Section Header

**Source:** "American Intelligence" section in various issues

```
American Intelligence.
QUEBEC.
(From our own Correspondent.)
December 24th, 1875.
```

**What happened:**
- Journal had regular "American Intelligence" correspondence sections
- "QUEBEC" was section header for market reports
- Parser confused section header with destination port
- Subsequent narrative text parsed as ship records

**Evidence of parsing error:**
- "Ship names" are narrative sentences:
  - "Let them imagine every roof covered with snow..."
  - "Number and Tonnage of lumber-laden vessels..."
  - "Red Pine. We have no recent sales to note."
- Raw lines contain market commentary, not ship data

**Legitimate records identified:** 33 records
- Format: "Ship @ Port,—cargo details"
- Example: "Inveresk @ Pugwash,—25,668 deals, 2,337 ends, Order."
- These are British ships arriving from various ports with cargoes for Quebec export

### 3. NEW YORK (201 records) - Similar Pattern

**Source:** Similar correspondence sections and cargo descriptions

**What happened:**
- Similar to QUEBEC - section headers and narrative text
- Some records mention "via New York" as ultimate cargo destination
- Concentrated in specific years: 1879 (98 records), 1885 (61 records)

**Evidence of parsing error:**
- "Ship names" include narrative fragments
- Many records lack proper ship structure

**Legitimate records identified:** 7 records
- Format: "Ship @ Port,—cargo details"
- Example: "Wassenaar @ Fredrikstad,—29,892 staves, 77,098 boards, 485 spars"
- These may be British ships arriving with cargoes destined for New York

---

## Solution: Context-Based Error Detection

### Methodology

**1. REDWOOD Detection**
- All REDWOOD records are parsing errors (commodity header, not place)
- Set all 297 records to empty destination

**2. QUEBEC/NEW YORK Detection**
- Check ship name patterns for narrative text:
  - Length > 40 characters
  - Contains common narrative words: "the", "and", "would", "been", etc.
  - Example: "Number and Tonnage of..."
- Check raw line format for legitimate ship records:
  - Contains "@" symbol: "Ship @ Port,—cargo"
  - Structured cargo description

**3. Assignment Rules**
```
IF ship_name is narrative text:
    → Set destination to empty (parsing error)
ELIF raw_line contains "@ Port,—cargo" pattern:
    → Keep destination (legitimate export record)
ELSE:
    → Set destination to empty (parsing error)
```

### Implementation

**Script:** `tools/fix_export_destination_errors.py`

**Key Functions:**

```python
def extract_actual_destination_from_redwood(row, all_records_by_file):
    """All REDWOOD records are parsing errors."""
    return ''

def is_narrative_text(ship_name, raw_line):
    """Detect if this is narrative text, not a ship record."""
    narrative_markers = [
        'the ', 'and ', 'would ', 'been ', 'every ', 'them ',
        'number and tonnage', 'left column', 'from our'
    ]
    if len(ship_name) > 40:
        return True
    for marker in narrative_markers:
        if marker in ship_name.lower():
            return True
    return False

def is_legitimate_ship_record(raw_line):
    """Check if raw line looks like legitimate ship record."""
    return '@' in raw_line
```

---

## Results - V4.3

### Corrections Applied

| Issue | Total Records | Set to Empty | Kept as Exports |
|-------|--------------|--------------|-----------------|
| **REDWOOD** | 297 | 297 (100%) | 0 |
| **QUEBEC** | 157 | 124 (79%) | 33 (21%) |
| **NEW YORK** | 201 | 194 (97%) | 7 (3%) |
| **TOTAL** | **655** | **615 (94%)** | **40 (6%)** |

### V4.2 vs V4.3 Comparison

| Metric | V4.2 | V4.3 | Change |
|--------|------|------|--------|
| Total records | 152,641 | 152,641 | No data loss |
| Records with empty destination | 3,740 | 4,355 | +615 (parsing errors removed) |
| REDWOOD destinations | 84 → varied | 0 | -297 (all removed) |
| QUEBEC destinations | 157 | 33 | -124 (narrative removed) |
| NEW YORK destinations | 201 | 7 | -194 (narrative removed) |

### Legitimate Export Records Retained (40 total)

**QUEBEC (33 records)** - British ships with export cargoes:
```
Inveresk @ Pugwash,—25,668 deals, 2,337 ends
Glencairn @ Charlotte Town P.E.I.,—230 deals
Atlas @ Gefle,—5,101 deals
Annie Austin @ Maccaw, N.S.,—good deal ends, 661 pcs. timber
```

**NEW YORK (7 records)** - British ships with export cargoes:
```
Wassenaar @ Fredrikstad,—29,892 staves, 77,098 boards, 485 spars
Johann Frederick @ Memel, —641 pcs. timber, 30 wainscot logs
Pennsylvania @ Philadelphia,—7,000 staves, 2,000
```

---

## Root Cause Analysis

### Why Did This Happen?

**1. OCR Stage (Correct)**
- OCR correctly captured text: "REDWOOD", "QUEBEC", "NEW YORK"
- These appear as section headers, commodity types, or in narrative text

**2. Parsing Stage (Error)**
- Parser uses pattern matching to extract: ship | origin | destination | cargo
- Section headers like "REDWOOD" or "QUEBEC" were captured as destinations
- Narrative text following section headers was parsed as ship records

### Journal Structure Challenges

**Typical TTJ page layout:**
```
[Pricing Tables]
  PREPARED FLOORING.
  REDWOOD.
  (prices...)

[Import Listings]
  LONDON.—From September 13th to 26th.
  Hewn Timber (loads).
  Russia—4,145 Burt & Co.
  ...

[Correspondence]
  American Intelligence.
  QUEBEC.
  (From our own Correspondent.)
  [Narrative market report...]
```

Parser difficulty: Distinguishing section headers from actual destinations

---

## Verification

### Sample Checks

**1. REDWOOD completely removed:**
```bash
# V4.2: 297 REDWOOD destinations
# V4.3: 0 REDWOOD destinations (all set to empty)
grep -c "REDWOOD" parsed_output/ttj_shipments_normalized_v4.3.csv
```

**2. Legitimate exports retained:**
```python
# QUEBEC records with '@' pattern kept
# Example: "Inveresk @ Pugwash,—25,668 deals"
df = pd.read_csv('ttj_shipments_normalized_v4.3.csv')
quebec = df[df['destination_port_normalized'] == 'QUEBEC']
print(quebec[['ship_name', 'origin_port', 'raw_line']].head())
```

**3. Narrative text removed:**
```python
# QUEBEC records with narrative text removed
# Example: "Let them imagine every roof covered with snow..."
# destination_port_normalized set to empty
```

---

## Quality Assurance

### Tests Performed

✅ **Record count verification**: 152,641 records preserved
✅ **REDWOOD elimination**: All 297 records set to empty
✅ **Narrative detection**: 318 narrative text records identified
✅ **Legitimate exports preserved**: 40 records retained
✅ **Pattern validation**: '@' symbol indicates legitimate ship format

### Known Limitations

⚠️ **Export records ambiguous**: The 40 retained records are **potential** exports
- Format suggests legitimate ship arrivals with export cargoes
- Could be British ships collecting cargoes for North American destinations
- Could also be parsing errors with different structure
- Recommend manual review of these 40 records

⚠️ **Other export destinations not investigated**: Only REDWOOD, QUEBEC, NEW YORK examined
- Other North American ports may have similar issues
- Future work: Scan for other suspicious export destinations

---

## Files Created

### Output Files
- **Database:** `parsed_output/ttj_shipments_normalized_v4.3.csv` (152,641 records)
- **Script:** `tools/fix_export_destination_errors.py`
- **Documentation:** `docs/export_destination_errors_v4.3.md` (this file)

---

## Impact

### Data Quality Improvements

✅ **Cleaner destination data**: 615 parsing errors removed
✅ **No false exports**: REDWOOD commodity header no longer appears as destination
✅ **Narrative text removed**: Journal commentary no longer parsed as ship records
✅ **Legitimate exports identified**: 40 potential export records flagged for review

### Analysis Capabilities Enhanced

✅ **Port frequency accuracy**: False destinations no longer inflate counts
✅ **Trade route clarity**: Removed nonsensical "export" destinations from import journal
✅ **Export records identified**: 40 legitimate export records can be analyzed separately

---

## Lessons Learned

1. **OCR vs Parsing distinction crucial**: OCR was correct; parsing logic had issues
2. **Context matters**: Section headers can appear anywhere, not just as destinations
3. **Pattern validation important**: '@' symbol is strong indicator of ship arrival format
4. **Narrative detection needed**: Long ship names with common words indicate text, not ships
5. **Conservative approach best**: When in doubt, set to empty rather than guess

---

## Next Steps

### Immediate Actions

1. **Review 40 retained export records** - Manual verification needed
2. **Check for other export destinations** - Scan for Boston, Philadelphia, etc.
3. **Update statistics** - Recalculate port rankings with v4.3 data

### Future Work

**Phase 3 Verification:**
- Spot-check top 100 unchanged origin ports
- Spot-check top 100 unchanged destination ports
- Create final production dataset

---

## Usage

### Loading V4.3 Database

```python
import pandas as pd
import csv

csv.field_size_limit(1000000)
df = pd.read_csv('parsed_output/ttj_shipments_normalized_v4.3.csv')

# Count empty destinations (parsing errors removed)
empty_dest = df[df['destination_port_normalized'] == ''].shape[0]
print(f"Empty destinations: {empty_dest}")  # 4,355 (up from 3,740)

# Check for REDWOOD
redwood = df[df['destination_port'] == 'REDWOOD']
print(f"REDWOOD records: {len(redwood)}")  # 297 raw, 0 normalized

# View potential export records
quebec = df[df['destination_port_normalized'] == 'QUEBEC']
print(f"QUEBEC exports: {len(quebec)}")  # 33 records
print(quebec[['ship_name', 'origin_port', 'raw_line']].head())
```

### Comparing V4.2 vs V4.3

```python
df_v42 = pd.read_csv('parsed_output/ttj_shipments_normalized_v4.2.csv')
df_v43 = pd.read_csv('parsed_output/ttj_shipments_normalized_v4.3.csv')

# Count changes
v42_empty = (df_v42['destination_port_normalized'] == '').sum()
v43_empty = (df_v43['destination_port_normalized'] == '').sum()

print(f"V4.2 empty destinations: {v42_empty}")  # 3,740
print(f"V4.3 empty destinations: {v43_empty}")  # 4,355
print(f"Records cleaned: {v43_empty - v42_empty}")  # 615
```

---

## See Also

- `docs/hull_victoria_dock_correction_v4.2.md` - Proximity-based dock assignments
- `docs/port_normalization_v4_phase1_complete.md` - Phase 1 improvements
- `docs/port_normalization_gaps_v3.md` - Original gap analysis
- `tools/fix_export_destination_errors.py` - Implementation script
