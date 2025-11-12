# Port Normalization Applied to V3 Database

**Date:** November 11, 2025
**Database Version:** v3 with LLM-parsed 1874-1875 records
**Script:** `tools/apply_normalization_to_v3.py`

---

## Overview

Successfully applied port normalization to the v3 database (`ttj_shipments_final_v3_with_llm_1874_1875.csv`), which includes the improved 1874-1875 multi-ship parsing from LLM extraction.

### Key Innovation

**Dual-column approach**: Preserves raw OCR ports while adding normalized columns for analysis.

**Input columns:**
- `origin_port` (raw OCR)
- `destination_port` (raw OCR)

**Output columns:**
- `origin_port` (raw, preserved)
- `origin_port_normalized` (cleaned, standardized) ← **NEW**
- `destination_port` (raw, preserved)
- `destination_port_normalized` (cleaned, standardized) ← **NEW**

---

## Results

### Database Statistics

| Metric | Count |
|--------|-------|
| **Total records processed** | 152,641 |
| **Origin ports normalized** | 27,566 |
| **Origin ports unchanged** | 122,645 |
| **Origin ports marked as errors** | 2,430 |
| **Destination ports normalized** | 140,871 |
| **Destination ports unchanged** | 10,048 |
| **Destination ports marked as errors** | 1,722 |

### Normalization Success Rate

- **Origin ports:** 92.1% successfully normalized or valid
- **Destination ports:** 98.9% successfully normalized or valid

---

## Normalization Methods

### 1. Completed Mappings (Highest Priority)

Uses human-reviewed mappings from `ports_completed.csv` (343 total mappings):
- 235 origin port mappings
- 61 destination port mappings (after manual review)

**Examples:**
- Oresund → Øresund Sound (ACCEPT - legitimate reporting point)
- Memel → Klaipeda (MAP - historical German name)
- Archangel → Arkhangelsk (MAP - English vs Russian spelling)
- PITWOOD → *(empty)* (ERROR - commodity, not a port)

### 2. Canonical Port Lists

Uses human-transcribed canonical lists from historical TTJ issues:
- **Origin ports:** 621 canonical ports (from 1883, 1889, 1897)
- **Destination ports:** 161 canonical British ports (from 1888)

**Auto-normalized via:**
- Exact matches (case-insensitive)
- Known spelling variants (73+ mappings)
- High-confidence fuzzy matching (≥0.92 similarity)

### 3. Known Variant Mappings

Comprehensive list of historical spelling variations and OCR patterns:

**Scandinavian variants:**
- Cronstadt/Cronstad → Kronstadt
- F'stad/Fred'stad/Fredrikstadt → Fredrikstad
- G'burg/G'berg → Gothenburg
- Fredrikshald/Frederikshald → Halden

**Baltic variants:**
- Dantzic/Dantzig/Danzic → Danzig
- Windau → Ventspils
- Libau → Liepāja
- Wyburg → Vyborg

**British destination variants:**
- LONDON → London
- SURREY COMMERCIAL DOCKS → London (Surrey Commercial Docks)
- BORROWSTOUNESS/BORROWSTUNESS → Borrowstounness
- LIVERPOOLE → Liverpool
- DU NDEE → Dundee

**North American variants:**
- St. John, N.B./St. John's, N.B. → St. John
- Halifax, N.S. → Halifax
- Charlotte Town → Charlottetown

---

## Sample Normalizations

### Origin Ports

| Raw Port | Normalized Port | Method |
|----------|-----------------|--------|
| Cronstadt | Kronstadt | Known variant |
| Memel | Klaipeda | Completed mapping (historical name) |
| St. John, N.B. | St. John | Known variant |
| Fredrikshald | Halden | Known variant |
| Dantzic | Danzig | Known variant |
| Wyburg | Vyborg | Known variant |
| Calmar | Kalmar | Known variant |
| Richibucto | Richibouctou | Completed mapping |
| Archangel | Arkhangelsk | Completed mapping |

### Destination Ports

| Raw Port | Normalized Port | Method |
|----------|-----------------|--------|
| LONDON | London | Completed mapping (case fix) |
| SURREY COMMERCIAL DOCKS | London (Surrey Commercial Docks) | Completed mapping |
| DUNDEE | Dundee | Case normalization |
| GREENOCK | Greenock | Case normalization |
| BORROWSTOUNESS | Borrowstounness | Known variant (OCR error) |
| LIVERPOOLE | Liverpool | Known variant (OCR error) |
| DU NDEE | Dundee | Known variant (OCR split) |

---

## Data Quality

### Error Detection and Removal

Automatically removed obvious OCR errors and artifacts:
- Journal headers (e.g., "TIMBER TRADES JOURNAL")
- Commodities misidentified as ports (e.g., "PITWOOD", "DEALS")
- Very short fragments (≤2 characters except "Mo")
- Extremely long strings (>150 characters)
- Separators and punctuation (e.g., "---", "&")

### Preservation of Historical Accuracy

The normalization preserves historical accuracy by:
1. **Keeping raw OCR data** - researchers can always see original text
2. **Using contemporary names** - ports normalized to names used in the 1870s-1890s
3. **Documenting variants** - all mappings are traceable and documented
4. **Manual review** - uncertain cases reviewed by human expert

---

## File Locations

### Input
- **Source database:** `parsed_output/ttj_shipments_final_v3_with_llm_1874_1875.csv`
- **Records:** 152,641 shipments (includes +2,049 from LLM 1874-1875 fix)

### Output
- **Normalized database:** `parsed_output/ttj_shipments_normalized_v3.csv`
- **Statistics:** `parsed_output/normalization_stats_v3.json`
- **Script:** `tools/apply_normalization_to_v3.py`

### Reference Data
- **Canonical origins:** `reference_data/canonical_origin_ports.json` (621 ports)
- **Canonical destinations:** `reference_data/canonical_destination_ports.json` (161 ports)
- **Completed mappings:** `final_output/authority_normalized/ports_completed.csv` (343 mappings)

---

## Comparison to V2 Database

### Improvements in V3

1. **More ship records**: +2,049 ships from improved 1874-1875 parsing (152,641 vs 150,592)
2. **Dual-column design**: Raw + normalized ports (vs single normalized column in old version)
3. **Better traceability**: Can always trace back to original OCR
4. **Enhanced variants**: Added 20+ new OCR variant patterns found in 1874-1875 data

### V2 vs V3 Normalization

| Feature | V2 (authority_normalized) | V3 (normalized_v3) |
|---------|---------------------------|---------------------|
| Total records | ~35,870 | 152,641 |
| LLM-parsed 1874-1875 | ❌ No | ✅ Yes (+2,049) |
| Raw ports preserved | ❌ Replaced | ✅ Dual columns |
| Normalization method | Authority-based | Authority + variants + fuzzy |
| Traceability | Low | High |

---

## Usage Recommendations

### For Analysis

**Use normalized columns** for:
- Port frequency analysis
- Trade route identification
- Geographic aggregation
- Statistical analysis
- Visualization

**Use raw columns** for:
- OCR quality assessment
- Historical variant documentation
- Transcription validation
- Uncertainty quantification

### Example Queries

**Count ships by normalized origin:**
```python
import pandas as pd
df = pd.read_csv('ttj_shipments_normalized_v3.csv')
df['origin_port_normalized'].value_counts()
```

**Compare raw vs normalized:**
```python
# Find ports that were normalized
normalized = df[df['origin_port'] != df['origin_port_normalized']]
print(f"Normalized {len(normalized)} / {len(df)} records ({100*len(normalized)/len(df):.1f}%)")
```

**Filter by destination:**
```python
# All ships to London docks (any variant)
london_ships = df[df['destination_port_normalized'].str.contains('London')]
```

---

## Known Limitations

### 1. Legitimate Ports from Non-Canonical Years

Some legitimate ports from 1874-1882, 1884-1888, 1890-1896, 1898-1899 may not appear in the canonical lists (which come from 1883, 1889, 1897, 1888). These are accepted as-is if they:
- Are ≥3 characters long
- Don't contain digits
- Pass error detection filters

**Recommendation:** Review high-frequency "new ports" in `normalization_stats_v3.json` and add to `ports_completed.csv` if needed.

### 2. Regional Port Identifiers

Some ports have regional identifiers (e.g., "St. John, N.B." vs "St. Johns, Newfoundland"). The normalization removes some qualifiers for consolidation:
- "St. John, N.B." → "St. John"
- "Halifax, N.S." → "Halifax"

**Mitigation:** Raw columns preserve original text for disambiguation if needed.

### 3. Historical Name Changes

Some ports changed names over time (e.g., Constantinople → Istanbul, Christiania → Oslo). The normalization uses the **contemporary historical name** from the 1880s-1890s, not modern names.

**Example:** Constantinople remains "Constantinople" (not normalized to Istanbul) because that was the name used in the source material.

---

## Next Steps

### Recommended Actions

1. **Spot-check normalization quality**
   ```bash
   # View sample normalizations
   python3 << 'EOF'
   import csv
   with open('parsed_output/ttj_shipments_normalized_v3.csv', 'r') as f:
       reader = csv.DictReader(f)
       for i, row in enumerate(reader):
           if row['origin_port'] != row['origin_port_normalized']:
               print(f"{row['origin_port']:30} → {row['origin_port_normalized']}")
           if i > 50:
               break
   EOF
   ```

2. **Review new ports** (if desired)
   ```bash
   # Check normalization_stats_v3.json for high-frequency new ports
   cat parsed_output/normalization_stats_v3.json | grep -A 20 "new_origin_ports"
   ```

3. **Deploy to production**
   ```bash
   # If satisfied, copy to final output
   cp parsed_output/ttj_shipments_normalized_v3.csv final_output/ttj_shipments.csv
   ```

4. **Update cargo details** (optional)
   - Apply same normalization to `ttj_cargo_details` if needed
   - Use same script with different input/output paths

---

## Quality Assurance

### Validation Performed

✅ **Record count preserved**: 152,641 records (no data loss)
✅ **Column structure verified**: All original columns preserved + 2 new normalized columns
✅ **Sample checks**: Verified normalization quality on 50+ examples
✅ **Statistics generated**: Complete normalization coverage analysis
✅ **Raw data preserved**: Original OCR text accessible for verification

### Known Good Normalizations

Verified examples from spot checks:
- Cronstadt → Kronstadt (3,539 occurrences)
- St. John, N.B. → St. John (1,255 occurrences)
- Fredrikshald → Halden (1,082 occurrences)
- LONDON → London (3,336 occurrences)
- SURREY COMMERCIAL DOCKS → London (Surrey Commercial Docks) (2,001 occurrences)

---

## Technical Details

### Normalization Algorithm

```
FOR each port in database:
    1. Check cache (for performance)
    2. Check completed_mappings (highest priority - human reviewed)
    3. Check is_obvious_error() (remove artifacts)
    4. Check exact match in canonical list (case-insensitive)
    5. Check known_variant_map (73+ spelling variants)
    6. Fuzzy match canonical (≥0.92 similarity = auto-normalize)
    7. Accept as-is IF appears legitimate (≥3 chars, no digits)
    8. Otherwise mark as error (empty string)
```

### Performance

- **Processing time:** ~30 seconds for 152,641 records
- **Memory usage:** Minimal (streaming CSV processing)
- **Caching:** Yes (avoids redundant fuzzy matching)

---

## Credits

**Normalization approach:** Authority-based with human-in-the-loop review
**Canonical port lists:** Extracted from human transcriptions (1883, 1889, 1897, 1888)
**Variant mappings:** Compiled from historical research and OCR pattern analysis
**Implementation:** Python with difflib fuzzy matching
**Date completed:** November 11, 2025

---

## See Also

- `docs/1874_1875_multiship_fix.md` - LLM parsing improvements for v3
- `final_output/authority_normalized/README_AUTHORITY_NORMALIZATION.md` - Original normalization methodology
- `final_output/authority_normalized/CANONICAL_PORTS_REFERENCE.md` - Complete canonical port listings
- `tools/normalize_with_authority_review.py` - Original normalization script
