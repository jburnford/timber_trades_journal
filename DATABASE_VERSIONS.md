# TTJ Forest of Numbers - Database Version History

**Last Updated:** November 12, 2025

---

## Current Production Databases (USE THESE)

### 1. Shipments Database
**File:** `final_output/ttj_shipments.csv`
- **Records:** 150,592
- **Created:** Nov 12, 2025 19:35
- **Status:** ✅ PRODUCTION - Use this version
- **Features:**
  - Origin coordinates: 84.7% coverage (125,908 ships)
  - Destination coordinates: 93.1% coverage (140,223 ships)
  - Deduplicated (2,392 duplicates removed from parser output)
  - Port name normalization applied (109 rules)
  - Foreign destinations removed (UK/Ireland only)
  - Columns: 24 (includes origin_latitude, origin_longitude, destination_latitude, destination_longitude)

### 2. Cargo Database
**File:** `final_output/ttj_cargo_details_cleaned.csv`
- **Records:** 306,202
- **Created:** Nov 12, 2025 19:30
- **Status:** ✅ PRODUCTION - Use this version
- **Features:**
  - Ship names included
  - Origin/destination ports included
  - Coordinates included (80.7% complete routes)
  - Props consolidated: 19,714 records (props + pit props + pit-props → "pit props")
  - Parsing errors removed (1,338 cleaned: long commodities, prices, dates)
  - Columns: 19

---

## Intermediate/Archive Versions (DO NOT USE FOR ANALYSIS)

### Parser Output (Morning - Pre-Geocoding)
**Location:** `parsed_output/`

#### ttj_shipments_normalized_v4.3.csv
- Records: 152,641
- Created: Nov 12, 2025 08:58
- Status: ⚠️ INTERMEDIATE - Parser output before deduplication
- Missing: Coordinates, deduplication
- Purpose: Archive of parser v4.3 output

#### ttj_shipments_final.csv  
- Records: 152,984
- Created: Nov 12, 2025 08:59
- Status: ⚠️ INTERMEDIATE - Parser output before geocoding
- Missing: Coordinates, deduplication, port normalization
- Purpose: Raw parser output (all records including duplicates)

#### ttj_shipments_normalized.csv
- Records: 150,592
- Created: Nov 12, 2025 19:09
- Status: ⚠️ INTERMEDIATE - After normalization, before foreign cleanup
- Missing: Foreign destination cleanup
- Purpose: Intermediate step in geocoding pipeline

### Cargo Intermediate Versions

#### ttj_cargo_details.csv
- Records: 306,202
- Status: ⚠️ DO NOT USE - Missing ship names and ports
- Purpose: Raw cargo parser output

#### ttj_cargo_details_enriched.csv
- Records: 306,202
- Status: ⚠️ DO NOT USE - Props not consolidated, errors not cleaned
- Purpose: Intermediate after adding ship/port data

---

## Processing Pipeline

```
PARSER OUTPUT (Morning)
  ↓
parsed_output/ttj_shipments_final.csv (152,984 records)
  ↓
DEDUPLICATION (-2,392 duplicates)
  ↓
parsed_output/ttj_shipments_normalized.csv (150,592 records)
  ↓
PORT NORMALIZATION (109 rules applied)
  ↓
GEOCODING (coordinates added)
  ↓
FOREIGN DESTINATION CLEANUP (1,899 records cleaned)
  ↓
final_output/ttj_shipments.csv (150,592 records) ✅ FINAL
```

---

## Record Count Explanation

**Why did we go from 152,984 → 150,592 records?**

1. **Deduplication:** -2,392 duplicate records removed
   - OCR parser sometimes created duplicates from multi-page entries
   - Deduplicated based on record_id

2. **No records lost in geocoding/normalization**
   - Port normalization: Changed port names, didn't remove records
   - Geocoding: Added coordinates, didn't remove records
   - Foreign cleanup: Cleared coordinates but kept records

---

## How to Verify You're Using the Correct File

### For Shipments Analysis:
```bash
# Check file has coordinates
head -1 final_output/ttj_shipments.csv | grep "origin_latitude"

# Check record count
wc -l final_output/ttj_shipments.csv
# Should show: 150593 (including header)

# Check modification date
ls -lh final_output/ttj_shipments.csv
# Should show: Nov 12 19:35
```

### For Cargo Analysis:
```bash
# Check file has ship names and ports
head -1 final_output/ttj_cargo_details_cleaned.csv | grep "ship_name"

# Check props consolidated
python3 -c "import pandas as pd; df = pd.read_csv('final_output/ttj_cargo_details_cleaned.csv'); print(f\"props: {(df['commodity']=='props').sum()}, pit props: {(df['commodity']=='pit props').sum()}\")"
# Should show: props: 0, pit props: 19714
```

---

## Related Files

### Analysis Outputs
- `analysis/annual_port_statistics/` - Port statistics by year (3 CSV files)
- `analysis/london_supply_network/` - London commodity analysis (4 CSV files)

### Reference Data
- `Ports_Master.geojson` - 558 ports with coordinates
- `reference_data/manual_port_matches.json` - 109 normalization rules
- `reference_data/unmapped_origin_ports_analysis.csv` - Analysis of unmapped ports

---

## Questions?

**Q: Which file should I use for mapping?**
A: `final_output/ttj_shipments.csv` - Has coordinates for 84.7% of origins and 93.1% of destinations

**Q: Which file should I use for commodity analysis?**
A: `final_output/ttj_cargo_details_cleaned.csv` - Has ship names, ports, coordinates, and quality improvements

**Q: Why are there so many files in parsed_output/?**
A: Those are checkpoints and intermediate versions from the parsing/geocoding pipeline. Only use files in `final_output/`.

**Q: Should I delete the old versions?**
A: Keep them for now as archives. They document the processing pipeline.

---

**Document maintained by:** Claude Code
**Last verified:** November 12, 2025 19:45
