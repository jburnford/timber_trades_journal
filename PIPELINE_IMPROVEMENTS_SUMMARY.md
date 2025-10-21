# TTJ Pipeline Improvements Summary
**Date**: October 21, 2025
**Improvements**: St. John parsing fix, UTF-8 encoding handling, comprehensive port mappings

---

## Pipeline Improvements Applied

### 1. St. John Parsing Fix ✓
**Problem**: Port names with abbreviations like "St. John, N.B." were truncated to just "St"
- **Affected**: 770 records

**Solution**: Modified regex pattern in `ttj_parser_v3.py` line 117:
```python
# OLD: Used period as delimiter, truncating "St. John" to "St"
r'[,\.—]\s*'

# NEW: Uses lookahead for em-dash or digit, preserving full port name
r',?\s*(?=[—\d])'
```

**Result**: 770 instances of "St. John, N.B." now properly captured

**Remaining Issue**: 219 records still show "St" or "ST" - these use different parsing patterns that need investigation

### 2. UTF-8 Encoding Fix ⚠️
**Problem**: Double-encoded UTF-8 characters (GÃ¤vle instead of Gävle)
- **Root Cause**: Corruption exists in OCR source files themselves
- **Affected**: 1,950 port instances

**Solution**: Two-stage approach
1. Added `fix_encoding()` function to parser (lines 50-73) - but doesn't trigger because corruption is literal text
2. **Final fix**: `fix_encoding_final.py` applies pattern replacement at END of pipeline

**Files Created**:
- `ttj_shipments_geocoding_ready.csv` - Clean UTF-8 for geocoding
- `unique_ports_for_geocoding.csv` - 2,943 unique ports with proper encoding

**Result**: ✓ Perfect UTF-8 in geocoding files (1,227 instances of "Gävle" corrected)

### 3. Comprehensive Port Mappings ✓
**Added**: 97 new port mappings in `ports_completed.csv`

#### Variant Spelling Mappings
- **Swedish ports**: GEFLE→Gävle, Goteborg/Gothenberg/Gottenburg→Göteborg, Westerwick→Västervik
- **Norwegian ports**: Multiple Fredrikstad variants, FREDRIKSHALD/F'shald→Halden
- **Finnish ports**: Christinestad variants→Kristinestad, Wasa→Vaasa, Raumo→Rauma
- **Other**: Rugenwalde→Darłowo, Hambro→Hamburg, Dantzie→Gdańsk, Leghorn→Livorno

#### Accepted New Ports (69 additions to canonical list)
- Canadian: Parrsboro, Sheet Harbour, Bathurst, Musquash, Bersimis, etc.
- French: La Tremblade, Paimpol, Brest, Landerneau, St. Estephe
- Swedish: Stocka, Ahlafors, Slite, Stromstad, Arno, Saltvik
- Others: Puebla, Laguna, Cienfuegos, Old Calabar, Buenos Aires

---

## Coverage Results

### Before Improvements
- **Origin Coverage**: 87.59%
- **Destination Coverage**: 96.54%
- **Unmapped ships**: 8,598

### After Improvements
- **Origin Coverage**: 90.38% (+2.79 percentage points)
- **Destination Coverage**: 96.54% (unchanged - already excellent)
- **Unmapped ships**: 6,668 (-1,930 ships mapped)

### Progress Toward 95% Goal
- **Ships still needed**: 3,203
- **Remaining unmapped ports**: 2,220 ports

---

## Remaining Issues

### Top Unmapped Ports (by ship count)
1. **St** (169 ships) + **ST** (50 ships) = 219 total
   - Parsing bug - need to fix other regex patterns beyond `early_at_pattern`
   
2. **W. C. Africa** (54 ships)
   - Mapping exists but variant spelling issue

3. **Small legitimate ports** (~3,000 ships across ~2,200 ports)
   - Many are valid ports with <10 ships each
   - Would require extensive maritime research to verify/map

### Priority Fixes for 95% Goal
To reach 95% coverage (3,203 more ships):
1. Fix remaining "St" parsing bug (219 ships)
2. Add next ~100 high-frequency ports (10+ ships each = ~1,000 ships)
3. Add next ~200 medium-frequency ports (5-9 ships each = ~1,400 ships)
4. Add next ~300 low-frequency ports (3-4 ships each = ~1,000 ships)

OR: Focus on top 300-400 ports to get bulk of improvement

---

## Files Generated

### Analysis Files
- `final_output/authority_normalized/ttj_shipments_authority_normalized.csv` (69,303 ships)
- `final_output/authority_normalized/ttj_cargo_details_authority_normalized.csv` (105,235 items)

### Geocoding Files (Clean UTF-8)
- `final_output/authority_normalized/ttj_shipments_geocoding_ready.csv`
- `final_output/authority_normalized/unique_ports_for_geocoding.csv`

### Review Files
- `final_output/authority_normalized/origin_ports_still_unmapped.csv` (2,220 ports)
- `final_output/authority_normalized/ports_completed.csv` (267 review decisions)

### Pipeline Documentation
- `DATA_PROCESSING_PIPELINE.md` - Complete step-by-step guide
- `METHODOLOGY_NOTES.md` - Validation results and best practices
- `run_complete_pipeline.sh` - Automated pipeline script

---

## Pipeline Script Created

**File**: `tools/run_complete_pipeline.sh`

**Usage**:
```bash
cd "/home/jic823/TTJ Forest of Numbers/tools"
bash run_complete_pipeline.sh
```

**Steps**:
1. Parse OCR files (with St. John fix + encoding fix)
2. Deduplicate records
3. Apply port normalization (with new mappings)
4. Calculate coverage statistics
5. Run final encoding fix for geocoding

**Runtime**: ~5-10 minutes for complete pipeline

---

## Technical Details

### Parser Modifications
**File**: `tools/ttj_parser_v3.py`

**Changes**:
- Lines 23-73: Added `ENCODING_FIXES` dictionary and `fix_encoding()` function
- Line 117: Modified `early_at_pattern` regex for St. John fix
- Lines 340, 358: Apply encoding fix to origin_port and destination_port

### Canonical Lists Updated
**File**: `reference_data/canonical_origin_ports.json`
- **Before**: 511 ports
- **After**: 580 ports (+69)

### Review Decisions Updated
**File**: `final_output/authority_normalized/ports_completed.csv`
- **Before**: 170 decisions
- **After**: 267 decisions (+97)

---

## Recommendations

### To Reach 95% Coverage
1. **Investigate "St" parsing bug** - Find which pattern is failing and apply same fix
2. **Batch add next 500 ports** - Use web research or gazetteers to verify
3. **Consider acceptable threshold** - 90% may be sufficient given long tail of rare ports

### For Future OCR Batches
1. Use `run_complete_pipeline.sh` for automated processing
2. Review `origin_ports_still_unmapped.csv` for new ports to classify
3. Add decisions to `ports_completed.csv` incrementally
4. Re-run normalization step only (fast - 1-2 minutes)

### Data Quality Notes
- **Categorical data**: Excellent (94% ports, 93% commodities)
- **Numerical data**: Moderate (44% quantities within 10%)
- **Use case**: Excellent for route/commodity analysis, aggregate trends only for volumes

---

## Summary

**Major Successes**:
- ✓ St. John parsing fix (770 records corrected)
- ✓ UTF-8 encoding solution (1,950 corrections in geocoding files)
- ✓ +2.79% coverage improvement (1,930 ships newly mapped)
- ✓ Comprehensive pipeline documentation

**Remaining Work**:
- ⚠️ 219 "St" records still truncated (different parsing pattern)
- ⚠️ 3,203 ships needed for 95% coverage goal
- ⚠️ 2,220 low-frequency ports to research/classify

**Overall**: Pipeline now at 90.38% origin coverage, up from 87.59%, with clear path to 95% through systematic port classification.

---

**End of Summary**
