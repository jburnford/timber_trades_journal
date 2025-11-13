# British Ports Needing Coordinate Research

**Date:** 2025-11-12
**Total:** 12 ports, 1,167 ships

---

## Ports to Research

| # | Port Name | Ships | Location Notes | Priority |
|---|-----------|-------|----------------|----------|
| 1 | **LERWICK** | 252 | Shetland Islands, Scotland | HIGH |
| 2 | **DEPTFORD** | 155 | London Thames dock area | HIGH |
| 3 | **DEPTFORD BUOYS** | 138 | Same as Deptford | HIGH |
| 4 | **BORDEN** | 102 | Possibly Borden, Kent | MEDIUM |
| 5 | **GRANTON** | 92 | Edinburgh port, Scotland | MEDIUM |
| 6 | **WMW** | 81 | Unclear abbreviation | LOW |
| 7 | **CLIFFE CREEK** | 77 | Cliffe, Kent (Thames Estuary) | MEDIUM |
| 8 | **SILVERTOWN** | 71 | London Thames dock area | MEDIUM |
| 9 | **SDD** | 69 | Unclear abbreviation | LOW |
| 10 | **FIFE** | 46 | Possibly Methil or other Fife port, Scotland | MEDIUM |
| 11 | **SKIBBEREEN** | 44 | County Cork, Ireland | MEDIUM |
| 12 | **PURFLEET** | 40 | Thames Estuary, Essex | MEDIUM |

**Total: 1,167 ships**

---

## Research Tasks

### For each port, please verify:

1. **Does it already exist in Ports_Master.geojson?**
   - Check for alternative spellings (e.g., "Lerwick" vs "LERWICK")
   - Check for nearby coordinates (within 5km)

2. **If missing, provide coordinates:**
   - Port name (canonical spelling)
   - Latitude, Longitude
   - Country/Region
   - Any alternative names

3. **If it's not a real port:**
   - Mark as parsing error or abbreviation
   - Note what it might represent

---

## Likely Candidates Already in GeoJSON

These ports probably exist in the GeoJSON with proper case:

- **LERWICK** → Lerwick (Shetland port, well-known)
- **DEPTFORD** → Deptford (London Thames)
- **GRANTON** → Granton (Edinburgh)
- **SILVERTOWN** → Silvertown (London)
- **PURFLEET** → Purfleet (Thames Estuary)

**Action:** Check if case-insensitive match exists first before researching coordinates.

---

## Uncertain Entries

These may be abbreviations or parsing errors:

- **WMW** (81 ships) - Unknown abbreviation
- **SDD** (69 ships) - Unknown abbreviation
- **FIFE** (46 ships) - Region name, not specific port?
- **BORDEN** (102 ships) - Small location, verify if timber port

---

## Output Format

Please provide coordinates in this format:

```csv
port_name,latitude,longitude,country,notes
Lerwick,60.1545,-1.1449,Scotland,Shetland Islands
Deptford,51.4814,-0.0253,England,London Thames
```

Or if already in GeoJSON:

```
LERWICK → Lerwick (already in GeoJSON)
DEPTFORD → Deptford (already in GeoJSON)
```
