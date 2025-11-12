# Port Normalization Gaps Analysis - V3 Database

**Date:** November 12, 2025
**Database:** `parsed_output/ttj_shipments_normalized_v3.csv`
**Analysis:** Review of 152,641 records to identify remaining normalization needs

---

## Executive Summary

### Current Normalization Status

✅ **Good consolidation achieved:**
- Origin ports: 7,573 raw → 6,631 normalized (12.4% reduction)
- Destination ports: 796 raw → 685 normalized (13.9% reduction)

⚠️ **Significant issues found:**
- **2,139 destination records** are journal artifacts, not ports (FULLY SECURED, BUILDING NEWS, etc.)
- **1,500+ destination records** have dock variants needing consolidation
- **297 destination records** have "REDWOOD" (likely parsing error)
- **Several hundred** stand-alone dock names missing parent port

---

## Top 30 Normalized Ports (Current State)

### Origin Ports - Successfully Normalized

| Port | Ships | Variants Consolidated |
|------|-------|----------------------|
| Riga | 8,071 | 1 |
| Gothenburg | 6,792 | 7 |
| New York | 4,859 | 2 |
| Bordeaux | 4,232 | 5 |
| Quebec | 3,843 | 5 |
| Kronstadt | 3,562 | 4 (Cronstadt, Cronstad, etc.) |
| Sundswall | 3,389 | 5 |
| Christiania | 3,364 | 7 |
| Danzig | 3,111 | 5 (Dantzic, Dantzig, etc.) |
| Klaipeda | 2,711 | 1 (from Memel) |
| Rotterdam | 2,706 | 3 |
| Drammen | 2,635 | 7 (Dram, etc.) |
| Fredrikstad | 2,566 | 15 (F'stad, Fred'stad, etc.) |
| Gävle | 2,478 | 1 (Gefle) |
| Montreal | 2,267 | 2 |

### Destination Ports - Successfully Normalized

| Port | Ships | Variants Consolidated |
|------|-------|----------------------|
| London | 24,427 | 3 |
| Grimsby | 16,733 | 1 |
| Liverpool | 15,671 | 2 (Liverpoole) |
| Dundee | 10,540 | 2 (DU NDEE) |
| Tyne | 10,113 | 1 (THE TYNE) |
| Bristol | 9,438 | 1 |
| Newport | 7,636 | 2 |
| Poole | 5,109 | 1 |
| Borrowstounness | 4,562 | 7 (BO'NESS, BORROWSTOUNESS, etc.) |
| Greenock | 3,953 | 2 (GRENOCK) |

**Note:** These normalizations are working correctly. The issues are with other ports listed below.

---

## Problem Category 1: Journal Artifacts (NOT PORTS)

### Impact: 2,139 records with non-port destinations

These are text fragments from bankruptcy notices, building news, and other journal sections that were incorrectly parsed as destination ports.

| "Port" | Records | Actual Meaning |
|--------|---------|----------------|
| FULLY SECURED | 254 | Bankruptcy notice text |
| BUILDING NEWS | 216 | Journal section header |
| CREDITORS FULLY SECURED | 151 | Bankruptcy notice text |
| SOUND LIST | 149 | Scandinavian shipping news section |
| REGISTERED | 134 | Legal registration notice |
| PETITION PRESENTED | 101 | Bankruptcy proceeding text |
| WMW | 81 | Unknown abbreviation |
| IMPORTERS OF | 80 | Column header text |
| FULLY SECURED CREDITORS | 79 | Bankruptcy notice text |
| TENDERS OPEN | 79 | Tender announcement text |
| CORRESPONDENCE | 73 | Journal section header |
| RESULTS OF TENDERS | 72 | Tender results text |
| PETITIONS PRESENTED | 52 | Bankruptcy proceeding text |
| NOTICES TO CREDITORS | 51 | Legal notice text |

### Example Context

```
Ship: Burt & Co.
Origin: Sweden
Destination: FULLY SECURED
Cargo: 8 W. E. Bott & Co.
```

**Analysis:** "FULLY SECURED" is from a bankruptcy notice. The cargo field contains the merchant name. This is a parsing error where journal text was captured as destination.

### Recommendation

**Action:** Add these to error detection in normalization script:
- Normalize all to empty string
- Flag records for manual review of source OCR
- May indicate broader parsing issues in these date ranges

---

## Problem Category 2: Dock Variants Needing Consolidation

### Impact: 1,500+ records with inconsistent dock naming

Many ports have specific dock names that need standardization.

#### Liverpool Docks (537 records)

| Current Name | Records | Should Normalize To |
|--------------|---------|---------------------|
| LIVERPOOL (COBURG DOCK) | 197 | Liverpool (Coburg Dock) |
| LIVERPOOL (NELSON DOCK) | 130 | Liverpool (Nelson Dock) |
| LIVERPOOL (QUEEN'S DOCK) | 122 | Liverpool (Queen's Dock) |
| LIVERPOOL (BRUNSWICK DOCK) | 87 | Liverpool (Brunswick Dock) |
| LIVERPOOL (TILBURY DOCK) | 70 | Liverpool (Tilbury Dock) |
| LIVERPOOL (TILBURY DOCKS) | 69 | Liverpool (Tilbury Docks) |
| LIVERPOOL (WELLINGTON DOCK) | 52 | Liverpool (Wellington Dock) |
| LIVERPOOL (TOWER DOCK) | 36 | Liverpool (Tower Dock) |
| LIVERPOOL (PRINCE'S DOCK) | 34 | Liverpool (Prince's Dock) |
| LIVERPOOL (DOCK) | 31 | Liverpool |
| LIVERPOOL (UNION DOCK) | 26 | Liverpool (Union Dock) |

#### Grimsby Docks (701 records)

| Current Name | Records | Should Normalize To |
|--------------|---------|---------------------|
| GRIMSBY (QUEEN'S DOCK) | 616 | Grimsby (Queen's Dock) |
| GRIMSBY (PRINCE'S DOCK) | 48 | Grimsby (Prince's Dock) |
| GRIMSBY (PRINCES DOCK) | 37 | Grimsby (Prince's Dock) |

**Note:** "PRINCES DOCK" vs "PRINCE'S DOCK" - inconsistent apostrophe usage.

#### London Docks (179 records)

| Current Name | Records | Should Normalize To |
|--------------|---------|---------------------|
| LONDON (SURREY DOCKS) | 96 | London (Surrey Commercial Docks) |
| LONDON (QUEEN'S DOCK) | 56 | London (Queen's Dock) |
| LONDON (UNION DOCK) | 27 | London (Union Dock) |

#### Other Ports

| Current Name | Records | Should Normalize To |
|--------------|---------|---------------------|
| GOOLE (QUEEN'S DOCK) | 111 | Goole (Queen's Dock) |
| GREENOCK (TILBURY DOCKS) | 21 | Greenock (Tilbury Docks) |

### Recommendation

**Action:** Update normalization script to:
1. **Case normalize** all dock names (LIVERPOOL → Liverpool)
2. **Standardize apostrophes** (PRINCES → Prince's, QUEENS → Queen's)
3. **Consolidate variants** (TILBURY DOCK vs TILBURY DOCKS)
4. **Preserve dock specificity** (keep dock names for historical accuracy)

---

## Problem Category 3: Stand-Alone Dock Names Missing Parent Port

### Impact: 378 records with dock names but no city

These docks are named without their parent port, making geographic analysis difficult.

| Dock Name | Records | Likely Parent Port |
|-----------|---------|-------------------|
| NELSON DOCK | 153 | Liverpool |
| ALEXANDRA DOCK | 141 | Liverpool or Hull |
| VICTORIA DOCK | 84 | London or Hull |

### Example Context

```
Ship: Helene
Origin: Sundswall
Destination: NELSON DOCK
Raw line: Helene-Sundswall-453 lds. sawn fir-G. Tebbutt
```

**Analysis:** Nelson Dock was a major dock in Liverpool. The destination should be normalized to "Liverpool (Nelson Dock)".

### Research Notes

**Liverpool docks:**
- Nelson Dock - major timber dock
- Alexandra Dock - opened 1881
- Victoria Dock - existed 1840s-1920s

**London docks:**
- Victoria Dock - part of Royal Docks, opened 1855
- Alexandra Dock - not a major London dock

**Hull docks:**
- Victoria Dock - opened 1850
- Alexandra Dock - opened 1885

### Recommendation

**Action:** Research each dock name and add parent port:
- **NELSON DOCK** → Liverpool (Nelson Dock)
- **ALEXANDRA DOCK** → Context-dependent (check years: post-1881 likely Liverpool, pre-1881 likely Hull)
- **VICTORIA DOCK** → Context-dependent (check origin patterns)

**Method:** Cross-reference with publication dates and origin ports to determine most likely parent.

---

## Problem Category 4: REDWOOD - Suspicious Port Name

### Impact: 297 records

"REDWOOD" appears 297 times as a destination but there is no British port named Redwood.

### Sample Records

```
Ship: C. G. Hansen. B.
Origin: America
Destination: REDWOOD
Cargo: 582 Price & Pierce.

Ship: MISSING_FROM_OCR
Origin: Cronstadt
Destination: REDWOOD
Cargo: 213 Sundry Importers.
```

### Analysis

1. **No cargo description**: All REDWOOD records have merchant/importer names in cargo field, not actual cargo
2. **No British port**: No major British port named "Redwood" in historical records
3. **Possible explanations:**
   - OCR error for "Redcar" (Yorkshire port)?
   - Cargo type (redwood timber) parsed as destination?
   - Journal section about redwood imports?

### Recommendation

**Action:**
1. **Review source OCR** for sample of REDWOOD records
2. **Check date ranges** - are these concentrated in specific years/months?
3. **Likely outcome:** Normalize to empty string (parsing error)

---

## Problem Category 5: Non-British Destinations

### Impact: 358 records with NEW YORK or QUEBEC as destination

The TTJ primarily covered imports TO Britain, not exports FROM Britain. These destinations are suspicious.

| Destination | Records | Analysis |
|-------------|---------|----------|
| NEW YORK | 201 | Unusual - verify if exports or parsing errors |
| QUEBEC | 157 | Unusual - verify if exports or parsing errors |

### Sample Records

**Clearly parsing errors:**
```
Ship: Buyers do not object to
Origin: (empty)
Destination: NEW YORK
Year: 1877
Raw line: Buyers do not object to cost,—indeed, a few will admit that they think prices...
```

**Possibly legitimate:**
```
Ship: Pennsylvania (s)
Origin: Philadelphia
Destination: NEW YORK
Year: 1877
Raw line: Order. Pennsylvania (s) @ Philadelphia,—7,000 staves, 2,000
```

### Recommendation

**Action:**
1. **Review all 358 records** manually
2. **Separate legitimate exports** from parsing errors
3. **For parsing errors:** Normalize to empty string
4. **For legitimate exports:** Consider adding "export_flag" column

---

## Problem Category 6: Short Origin Port Names (Possible Fragments)

### Impact: ~700 records with very short origin names

| Port | Records | Assessment |
|------|---------|-----------|
| Saw | 290 | Suspicious - fragment of "Sandviken" or parsing error? |
| York | 273 | Could be legitimate (York, England) but unusual as origin |
| Co. | 148 | Clearly a fragment ("& Co." from merchant name) |
| Mem | 96 | Suspicious - fragment of "Memel"? |
| Kem | 53 | Possibly "Kemi" (Finnish port) misspelled |

**Legitimate short ports:**
- **Riga** (8,071) - ✅ Legitimate Latvian port
- **Abo** (537) - ✅ Legitimate Finnish port (Swedish name for Turku)
- **Kemi** (288) - ✅ Legitimate Finnish port
- **Moss** (276) - ✅ Legitimate Norwegian port
- **Umea** (132) - ✅ Legitimate Swedish port

### Recommendation

**Action:** Review each short port individually:
- **Co.** → Normalize to empty (fragment)
- **Saw** → Research - might be abbreviation
- **York** → Check context - if "New York" was split, consolidate
- **Mem** → Check if variant of Memel (should be → Klaipeda)

---

## Summary Statistics

### Ports Successfully Normalized

✅ **Working well:**
- Major Scandinavian/Baltic ports (Kronstadt, Fredrikstad, Danzig, Klaipeda)
- Major British ports (London, Liverpool, Dundee, Grimsby)
- Common OCR errors caught (Cronstadt→Kronstadt, Dantzic→Danzig)

### Ports Needing Work

⚠️ **High priority fixes (3,000+ records):**
- Journal artifacts → empty string (2,139 records)
- Dock variants → standardized names (1,500+ records)
- REDWOOD → investigate and likely → empty (297 records)
- Stand-alone docks → add parent port (378 records)

⚠️ **Medium priority reviews:**
- NEW YORK / QUEBEC destinations (358 records)
- Short origin fragments (700 records)

---

## Recommended Action Plan

### Phase 1: High-Impact Fixes (Quick Wins)

1. **Add journal artifacts to error detection** (2,139 records fixed)
   - Update `is_obvious_error()` function
   - Add patterns: FULLY SECURED, BUILDING NEWS, REGISTERED, etc.

2. **Standardize dock naming conventions** (1,500+ records improved)
   - Case normalization (LIVERPOOL → Liverpool)
   - Apostrophe standardization (QUEENS → Queen's)
   - Consolidate variants (TILBURY DOCK → Tilbury Docks)

3. **Fix stand-alone docks** (378 records fixed)
   - NELSON DOCK → Liverpool (Nelson Dock)
   - Research ALEXANDRA DOCK and VICTORIA DOCK contexts

### Phase 2: Investigation and Manual Review

4. **Investigate REDWOOD** (297 records)
   - Review source OCR samples
   - Determine root cause
   - Likely normalize to empty string

5. **Review export destinations** (358 records)
   - Separate legitimate exports from parsing errors
   - Consider adding export flag to schema

6. **Review short origin ports** (700 records)
   - Verify each short port individually
   - Fix fragments (Co. → empty)
   - Consolidate variants (Mem → Memel → Klaipeda)

### Phase 3: Verification and Documentation

7. **Spot-check high-frequency unchanged ports**
   - Verify top 100 unchanged origins are legitimate
   - Verify top 100 unchanged destinations are legitimate

8. **Update documentation**
   - Document all new normalization rules
   - Create mapping file for dock standardizations

---

## Implementation Priority

### Critical (Do First)
- ✅ Journal artifacts detection
- ✅ Dock case normalization
- ✅ Stand-alone dock parent ports

### Important (Do Soon)
- ⚠️ REDWOOD investigation
- ⚠️ Export destination review

### Nice to Have (Do Eventually)
- 📝 Short port fragment cleanup
- 📝 Comprehensive variant expansion

---

## Expected Impact

**After Phase 1 fixes:**
- **~4,000 records** will have improved destinations
- **~90% accuracy** for destination normalization (up from ~87%)
- **Geographic analysis** will be more accurate with proper dock→city mapping

**After Phase 2 reviews:**
- **~95% accuracy** achievable
- **Clear separation** of imports vs exports
- **Better data quality** for research

---

## Files for Implementation

### Scripts to Update
- `tools/apply_normalization_to_v3.py` - Add new error patterns and dock rules
- `tools/normalize_with_authority_review.py` - Enhance variant detection

### Reference Files to Create
- `reference_data/dock_parent_ports.json` - Mapping of docks to parent cities
- `reference_data/journal_artifacts.txt` - List of non-port text patterns
- `final_output/authority_normalized/additional_fixes.csv` - Manual review decisions

### Output Files
- `parsed_output/ttj_shipments_normalized_v4.csv` - Version 4 with fixes applied
- `parsed_output/normalization_report_v3_v4_comparison.md` - Before/after analysis

---

## See Also

- `docs/port_normalization_v3.md` - Current normalization methodology
- `docs/1874_1875_multiship_fix.md` - LLM parsing fixes
- `final_output/authority_normalized/README_AUTHORITY_NORMALIZATION.md` - Original normalization approach
