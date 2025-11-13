# TTJ Port Geocoding Improvement Project

**Date:** 2025-01-12
**Objective:** Improve port geocoding coverage from 77.6% to 90%
**Status:** Ready for implementation

---

## 📊 Summary of Improvements

### Current State
- **Coverage:** 77.6% (116,008 / 149,564 ships with coordinates)
- **Missing:** 33,556 ships without coordinates

### After Improvements
- **Port normalization:** ~26,527 ships improved (17.7% of dataset)
- **New ports added:** ~13,573 ships improved (71 unique ports)
- **Total improvement:** ~40,100 ships fixed
- **Projected coverage:** ~83-85% (still short of 90% goal, but significant improvement)

---

## 📁 Key Files Created

### 1. Port Normalization
**File:** `reference_data/manual_port_matches.json`
**Purpose:** Maps alternative port spellings to canonical names
**Status:** ✅ Ready to use
**Rules added:** 58 normalization mappings

**Key examples:**
- `"Memel" → "Klaipeda"` (2,701 ships)
- `"Windau" → "Ventspils"` (716 ships)
- `"Libau" → "Liepaja"` (687 ships)
- `"Dantzig" → "Danzig"` (historical name)
- `"Chatham (N.B.)" → "Chatham, N. B."` (124 ships)
- `"Porsgrunn" → "Porsgrund"` (62 ships)

### 2. Normalization Script
**File:** `tools/normalize_port_names.py`
**Purpose:** Apply normalization rules to shipments data
**Usage:**
```bash
cd "/home/jic823/TTJ Forest of Numbers"
python3 tools/normalize_port_names.py
```

**Output:**
- `parsed_output/ttj_shipments_normalized.csv` - Shipments with normalized port names
- `parsed_output/port_normalization_report.txt` - Detailed statistics

### 3. New Ports to Add
**File:** `reference_data/new_ports_truly_unique.csv` ⭐ **USE THIS FILE**
**Purpose:** 71 unique ports with coordinates ready to add to GeoJSON
**Status:** ✅ Verified unique, no duplicates with existing GeoJSON

**Format:**
```csv
port_name,ship_count,latitude,longitude,country,alternative_names,notes
```

**Top ports:**
1. Klaipeda (Lithuania): 2,701 ships
2. Bayonne (France): 1,082 ships
3. Ventspils (Latvia): 716 ships
4. Brevig (Norway): 700 ships
5. Liepāja (Latvia): 687 ships

### 4. Documentation Files
- `reference_data/geocoding_fixes_needed.md` - Comprehensive tracking document
- `reference_data/coordinate_duplicates_report.txt` - Duplicate analysis
- `reference_data/GEOCODING_IMPROVEMENT_README.md` - This file

---

## 🔧 Implementation Steps

### Step 1: Apply Port Normalization
Run the normalization script to create normalized shipments:
```bash
cd "/home/jic823/TTJ Forest of Numbers"
python3 tools/normalize_port_names.py
```

This will:
- Create `parsed_output/ttj_shipments_normalized.csv`
- Normalize 26,527 ship records with alternative port spellings
- Generate a detailed report

### Step 2: Add New Ports to GeoJSON
Add the 71 ports from `reference_data/new_ports_truly_unique.csv` to `Ports_Master.geojson`

**Important:** These ports have been verified as:
- ✅ Not already in GeoJSON (coordinate-checked within 5km)
- ✅ No internal duplicates
- ✅ Coordinates verified via web research and GIS vetting
- ✅ Fixed issues (Chatham N.B., Porsgrunn, Trangsund/Vysotsk, coordinate corrections)

**Method:** Load the CSV in QGIS or your GIS software and:
1. Review coordinates on map for accuracy
2. Export as points
3. Merge with existing `Ports_Master.geojson`

**OR** programmatically add them:
```python
import json
import pandas as pd

# Load new ports
new_ports = pd.read_csv('reference_data/new_ports_truly_unique.csv')

# Load existing GeoJSON
with open('Ports_Master.geojson', 'r') as f:
    geojson = json.load(f)

# Add new ports as features
for idx, row in new_ports.iterrows():
    feature = {
        "type": "Feature",
        "properties": {
            "Name": row['port_name'],
            "Country": row['country'],
            "AltNames": row['alternative_names'],
            "Notes": row['notes']
        },
        "geometry": {
            "type": "Point",
            "coordinates": [row['longitude'], row['latitude']]
        }
    }
    geojson['features'].append(feature)

# Save updated GeoJSON
with open('Ports_Master_Updated.geojson', 'w') as f:
    json.dump(geojson, f, indent=2)
```

### Step 3: Re-run Geocoding
Use the normalized shipments and updated GeoJSON:
```bash
# Use your existing geocoding script with:
# - Input: parsed_output/ttj_shipments_normalized.csv
# - GeoJSON: Ports_Master_Updated.geojson
```

### Step 4: Measure Results
Check the new coverage:
```python
import pandas as pd

df = pd.read_csv('final_output/ttj_shipments_geocoded.csv')
total = len(df)
with_coords = len(df[df['origin_latitude'].notna()])
coverage = with_coords / total * 100

print(f"Coverage: {coverage:.1f}% ({with_coords:,} / {total:,})")
```

**Expected:** ~83-85% coverage

---

## 🗺️ Geographic Distribution of New Ports

| Country        | Ports | Ships |
|----------------|-------|-------|
| Lithuania      | 1     | 2,701 |
| France         | 7     | 2,279 |
| Norway         | 18    | 2,232 |
| United States  | 7     | 1,508 |
| Latvia         | 2     | 1,403 |
| Canada         | 7     | 841   |
| Denmark        | 3     | 506   |
| Sweden         | 5     | 302   |
| Russia         | 2     | 214   |
| Finland        | 3     | 199   |
| **Others**     | 17    | 1,450 |
| **TOTAL**      | **71**| **13,573** |

---

## ⚠️ Known Issues Fixed

### Issue 1: Chatham (N.B.)
**Problem:** New ports CSV had Chatham at wrong coordinates (47.017, -65.0)
**Solution:** Removed from new ports, added to manual_port_matches.json
**Maps to:** "Chatham, N. B." in existing GeoJSON at (47.043, -65.459)
**Status:** ✅ Fixed

### Issue 2: Trangsund
**Problem:** Initially used Swedish Trangsund (Stockholm suburb) coordinates
**Solution:** Corrected to Russian Vysotsk (formerly Finnish Trångsund)
**Correct coords:** 60.6333°N, 28.5667°E (Gulf of Finland)
**Status:** ✅ Fixed

### Issue 3: Internal Duplicates
**Problem:** 27 ports accidentally added twice during CSV building
**Solution:** Deduplicated via `new_ports_truly_unique.csv`
**Status:** ✅ Fixed

### Issue 4: Porsgrunn Duplicate (GIS Vetting)
**Problem:** Porsgrunn (59.085, 9.646) discovered during GIS vetting
**Solution:** Already exists as "Porsgrund" in GeoJSON at (59.143, 9.657) - only 4.29 km away
**Action:** Removed from new ports, added normalization rule `"Porsgrunn" → "Porsgrund"`
**Ships affected:** 62 ships
**Status:** ✅ Fixed

### Issue 5: Coordinate Corrections (GIS Vetting)
**Problem:** Three ports had incorrect or imprecise coordinates identified during GIS vetting
**Corrections:**
- **Egersund:** 58.383, 6.041 → 58.4497, 6.0087
- **Brevig:** 59.0642, 9.6961 → 59.05544, 9.69593
- **Moss:** 59.3756, 10.654 → 59.459167, 10.700833
**Status:** ✅ Fixed

---

## 📈 Why We Didn't Reach 90%

After investigating the missing ports, we found:

1. **Parsing Errors:** "Address", "Saw", "British" - not real ports (814 ships)
2. **One-off Mentions:** 6,300+ ports with 1-20 ships each
3. **Ambiguous Names:** Ports without enough context to locate accurately
4. **Historical Names:** Obscure historical spellings that couldn't be matched

**Decision:** Focus on legitimate high-volume ports (10+ ships) to capture 85% of meaningful trade rather than chase diminishing returns.

---

## 📋 Files Overview

### Use These Files ✅
- `reference_data/new_ports_truly_unique.csv` - 71 ports to add
- `reference_data/manual_port_matches.json` - 58 normalization rules
- `tools/normalize_port_names.py` - Normalization script

### Reference/Backup Files 📚
- `reference_data/new_ports_to_add.csv` - Original research (160 ports, has duplicates)
- `reference_data/new_ports_to_add_cleaned.csv` - After name dedup
- `reference_data/new_ports_to_add_deduplicated.csv` - After internal dedup
- `reference_data/new_ports_to_add_final.csv` - Before coordinate checking
- `reference_data/coordinate_duplicates_report.txt` - Duplicate analysis
- `reference_data/geocoding_fixes_needed.md` - Full tracking document

### Generated Output Files 📊
- `parsed_output/ttj_shipments_normalized.csv` - Normalized shipments
- `parsed_output/port_normalization_report.txt` - Statistics

---

## 🔍 Validation Checklist

Before finalizing:
- [x] Verify no coordinate duplicates with existing GeoJSON (5km threshold)
- [x] Remove internal CSV duplicates
- [x] Fix Chatham (N.B.) coordinates
- [x] Fix Trangsund/Vysotsk location
- [x] Visual review in GIS for any remaining issues (Porsgrunn duplicate found, coordinates corrected)
- [ ] Test geocoding with normalized data + new ports
- [ ] Measure final coverage percentage

---

## 📝 Next Steps After Implementation

1. **Quality Check:** Review geocoded results for any new issues
2. **Missing Ports Analysis:** Analyze remaining ~15% for patterns
3. **Manual Correction:** Consider manual fixes for high-value missing ports
4. **Documentation:** Update main project documentation with results

---

## 📞 Notes

- All coordinates researched via web search (primarily maritime databases)
- 5km threshold used for duplicate detection (appropriate for port areas)
- Manual matches take precedence over GeoJSON to handle spelling variants
- Normalization preserves original port names in separate column for reference

**Last Updated:** 2025-11-12 (GIS vetting completed)
**Ready for Implementation:** Yes ✅
