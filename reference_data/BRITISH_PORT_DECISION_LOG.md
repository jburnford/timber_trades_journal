# British Destination Port Mapping Decision Log

**Date:** 2025-11-12
**Context:** Analyzing British destination ports for TTJ shipments geocoding

---

## Decision: Exclude Non-British Destinations

### Background
During analysis of British destination ports, we identified several non-British destinations in the dataset:

1. **QUEBEC** → Quebec City, Canada (160 ships)
2. **HAVRE** → Le Havre, France (58 ships)
3. **QUEBEC DOCKS** → Quebec City, Canada (2 ships)
4. **QUEBEC DOCK** → Quebec City, Canada (2 ships)

**Total non-British destinations: 222 ships (0.15% of dataset)**

### Decision
**These non-British destinations will NOT be mapped or geocoded.**

### Rationale
1. **Too few ships to justify parser fixes**: 222 ships represents only 0.15% of the 150,592 total shipments
2. **OCR parsing errors**: These appear to be OCR errors where destination columns were misread
3. **Out of scope**: Project focuses on British timber import ports, not re-export destinations
4. **Diminishing returns**: Time better spent on higher-volume British ports

### Implementation
- Non-British destinations documented but excluded from manual_port_matches.json
- Ships with non-British destinations will remain without coordinates
- No attempt to fix OCR parsing for these entries

---

## Corrections Made: Grimsby OCR Errors

### Issue
OCR misread column separators, creating entries like "GRIMSBY (TILBURY DOCK)" where Grimsby and the actual dock were in different columns.

### Corrections (6 entries, 44 ships):
| Database Port | Corrected Mapping | Ships | Reason |
|---------------|-------------------|-------|--------|
| GRIMSBY (TILBURY DOCK) | Tilbury Docks | 19 | Tilbury is in Essex, not Grimsby |
| GRIMSBY (TILBURY DOCKS) | Tilbury Docks | 7 | Tilbury is in Essex, not Grimsby |
| GRIMSBY (SURREY DOCKS) | Surrey Commercial Docks | 6 | Surrey Docks are in London |
| GRIMSBY (COBURG DOCK) | Liverpool | 6 | Coburg Dock is in Liverpool |
| GRIMSBY (RUNCORN DOCK) | Runcorn | 3 | Runcorn is separate port |
| GRIMSBY (LONDON DOCKS) | London | 3 | London Docks are in London |

**Total corrected: 44 ships**

---

## Corrections Made: Liverpool (Tilbury) Errors

### Issue
Similar OCR error where Liverpool and Tilbury (different columns) were combined.

### Corrections (2 entries, 139 ships):
| Database Port | Corrected Mapping | Ships |
|---------------|-------------------|-------|
| LIVERPOOL (TILBURY DOCK) | Tilbury Docks | 70 |
| LIVERPOOL (TILBURY DOCKS) | Tilbury Docks | 69 |

**Total corrected: 139 ships**

---

## Final Statistics

### Manual Mappings Created
- **Total mappings:** 90 British port mappings
- **Ships covered:** 28,994 ships
- **Non-British excluded:** 218 ships (documented but not mapped)

### Combined Coverage (Manual + Fuzzy + Exact)
- **Exact matches (case-insensitive):** 111,130 ships
- **Fuzzy matches (>=85%):** 886 ships
- **Manual mappings:** 28,994 ships
- **Total British destination coverage:** 141,010 / 150,592 = **93.6%**

### Remaining Work
- 12 British ports need coordinate research (1,167 ships)
- 218 ships have non-British destinations (excluded by design)
- Various parsing errors remain (documented, excluded from geocoding)

---

## Files Created
- `british_port_manual_mappings_corrected.json` - Final corrected mappings (90 ports)
- `british_ports_case_fuzzy_matches.json` - Fuzzy matches (22 ports)
- `british_ports_missing_v2.csv` - Full analysis of missing ports

**Last Updated:** 2025-11-12
