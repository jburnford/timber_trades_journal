# Port Geocoding Fixes Tracking Document

**Last Updated:** 2025-01-12

## Overview

This document tracks ports that need geocoding fixes to improve coordinate coverage.

**Current Coverage:**
- Origin ports: 77.6% of ships have coordinates (116,008 / 149,564)
- Destination ports: 92.3% of ships have coordinates
- Missing: 33,556 ships from origin ports without coordinates

---

## Status Categories

- `READY` - Coordinates found, ready to add to GeoJSON
- `IN_MANUAL_MATCHES` - Already in manual_port_matches.json
- `NEEDS_RESEARCH` - Need to find correct coordinates
- `PARSING_ERROR` - Not a real port, ignore
- `FUZZY_MATCH` - May match existing GeoJSON port with different spelling

---

## High Priority: Top 20 Missing Origin Ports

### 1. Klaipeda (Lithuania) - 2,701 ships
**Status:** `READY`
- **Coordinates:** 55.71722, 21.12861
- **Source:** User provided, geonames.org/598098/klaipeda.html
- **Alternative names:** Memel, Klaipėda
- **Already documented in:** `manual_port_matches.json` (missing_ports_to_add section)
- **Action:** Add to GeoJSON as priority

### 2. Halden (Norway) - 1,186 ships
**Status:** `NEEDS_RESEARCH`
- **Action:** Find coordinates on geonames.org
- **Notes:** Norwegian timber port on Swedish border

### 3. Bayonne (France) - 1,082 ships
**Status:** `NEEDS_RESEARCH`
- **Action:** Find coordinates (likely 43.4925, -1.4742)
- **Notes:** Major French Atlantic port

### 4. Ventspils (Latvia) - 716 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 57.394, 21.561
- **Alternative names:** Windau (German)
- **Notes:** Major Latvian Baltic port

### 5. Brevig (Norway) - 700 ships
**Status:** `NEEDS_RESEARCH`
- **Action:** Research - multiple places named Brevig in Norway
- **Notes:** Likely Brevik near Porsgrunn

### 6. Liepāja (Latvia) - 687 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 56.505, 21.011
- **Alternative names:** Libau (German)
- **Notes:** Major Latvian Baltic port

### 7. Mobile (USA) - 566 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 30.694, -88.043
- **Notes:** Alabama timber port, Gulf Coast

### 8. Lorient (France) - 529 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 47.748, -3.361
- **Notes:** Brittany port

### 9. Address - 528 ships
**Status:** `PARSING_ERROR`
- **Action:** Ignore - not a real port
- **Notes:** OCR parsing error

### 10. Norfolk (USA) - 325 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 36.847, -76.285
- **Notes:** Virginia timber port

### 11. Newport News (USA) - 299 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 37.088, -76.428
- **Notes:** Virginia timber port, Hampton Roads

### 12. Saw - 286 ships
**Status:** `PARSING_ERROR`
- **Action:** Ignore - not a real port (likely "saw mill")
- **Notes:** OCR parsing error

### 13. Moss (Norway) - 275 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 59.434, 10.657
- **Notes:** Norwegian timber port near Oslo

### 14. Rijeka (Croatia) - 249 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 45.327, 14.442
- **Alternative names:** Fiume (Italian/German)
- **Notes:** Major Adriatic port

### 15. Saint-Brieuc (France) - 200 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 48.514, -2.760
- **Notes:** Brittany port

### 16. Vilagarcía de Arousa (Spain) - 200 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 42.596, -8.769
- **Notes:** Galician port

### 17. Matane (Canada) - 199 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 48.849, -67.533
- **Notes:** Quebec timber port, St. Lawrence River

### 18. Hommelvik (Norway) - 198 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 63.411, 10.795
- **Notes:** Norwegian timber port near Trondheim

### 19. Dieppe (France) - 191 ships
**Status:** `NEEDS_RESEARCH`
- **Coordinates:** Likely 49.925, 1.077
- **Notes:** Normandy port

### 20. Chatham (multiple) - 190 ships
**Status:** `NEEDS_RESEARCH`
- **Action:** Determine if Chatham, Kent (UK) or Chatham, New Brunswick (Canada)
- **Notes:** Need to check raw records to determine which

---

## Fuzzy Matches Needing Review

### La Roche-Bernard → Roche Bernard - 179 ships
**Status:** `FUZZY_MATCH`
- **Similarity:** 0.83
- **Action:** Add manual match: `"La Roche-Bernard": "Roche Bernard"`
- **GeoJSON Port:** Roche Bernard (already exists)

### La Tremblade → Tremblade - 100 ships
**Status:** `FUZZY_MATCH`
- **Similarity:** 0.86
- **Action:** Add manual match: `"La Tremblade": "Tremblade"`
- **GeoJSON Port:** Tremblade (already exists)

### Port-Launay → Port Launay - 98 ships
**Status:** `FUZZY_MATCH`
- **Similarity:** 0.91
- **Action:** Add manual match: `"Port-Launay": "Port Launay"`
- **GeoJSON Port:** Port Launay (already exists)

### Kristinestad → Christianstad - 88 ships
**Status:** `FUZZY_MATCH`
- **Similarity:** 0.80
- **Action:** Add manual match: `"Kristinestad": "Christianstad"`
- **GeoJSON Port:** Christianstad (already exists)
- **Notes:** Finnish port, Swedish name variant

### Belize → Elie - 156 ships
**Status:** `FUZZY_MATCH`
- **Similarity:** 0.80
- **Action:** REVIEW - Probably NOT the same port
- **Notes:** Belize is Central America, Elie is Scotland. Likely false match.
- **Correct Action:** Research Belize coordinates separately

---

## Already Fixed

### Boston Issue - COMPLETED
- **Problem:** All 1,457 Boston destinations matched to Boston MA instead of Boston UK
- **Fix:** Modified `create_geocoded_database.py` to prefer UK/Ireland coordinates for duplicate names
- **Result:** All Boston records now correctly point to Boston, England (52.9789, -0.0266)

### Parsing Errors Removed - COMPLETED
- **British ports as origins:** 600 records removed (0.39%)
- **Foreign destinations:** 35 records removed (BREMEN, NEW YORK, FIUME, BOULOGNE)

---

## Action Plan

### Phase 1: Quick Wins (Fuzzy Matches)
1. Add 4 confirmed fuzzy matches to `manual_port_matches.json`
2. Research Belize separately (likely false match)
3. Regenerate geocoded database
4. **Expected gain:** ~377 ships (excluding Belize)

### Phase 2: Major Missing Ports
1. Research coordinates for top 15 legitimate ports (excluding parsing errors)
2. Add to GeoJSON with proper metadata
3. Regenerate geocoded database
4. **Expected gain:** ~10,000+ ships

### Phase 3: Medium Priority
- Ports with 50-200 ships each
- Focus on legitimate timber ports
- Skip obvious parsing errors

---

## Coordinate Research Template

When adding new ports to GeoJSON, use this template:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [LONGITUDE, LATITUDE, 0]
  },
  "properties": {
    "Name": "Port Name",
    "descriptio": "Timber Exporter",
    "Imports": "timber",
    "Sources": "TTJ 1874-1899, geonames.org"
  }
}
```

---

## Files to Update

After finding coordinates:

1. **Add to GeoJSON:** `Ports_Master.geojson`
2. **Add manual matches:** `reference_data/manual_port_matches.json`
3. **Regenerate database:** Run `tools/create_geocoded_database.py`
4. **Regenerate statistics:** Run `tools/create_annual_port_statistics.py`
5. **Verify coverage:** Check total ship counts

---

## Notes

- Focus on ports with >150 ships first
- Many small ports (1-10 ships) can be ignored
- Some "ports" are parsing errors (Address, Saw, etc.)
- Character encoding issues common with Scandinavian ports (å, ä, ö)
- Some ports have multiple names (historical/language variants)

---

## Coverage Goals

**Current:** 77.6% of origin ships have coordinates
**Target:** 85%+ with Phase 1 + Phase 2
**Phase 1 gain:** ~0.3% (377 ships)
**Phase 2 gain:** ~7%+ (10,000+ ships)
