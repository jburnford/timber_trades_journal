# Authority-Based Port Normalization

**Created:** October 17, 2025
**Method:** Human-transcribed canonical lists + fuzzy matching + human review
**Status:** ⏸️ **READY FOR HUMAN REVIEW**

---

## Overview

This directory contains the **authority-based port normalization** pipeline, which uses human-transcribed canonical port lists as the gold standard for normalizing the 1,755 origin ports and 282 destination ports found in the parsed TTJ dataset.

### Key Innovation

Instead of normalizing based purely on frequency or fuzzy matching, this approach:
1. **Uses canonical lists** from human transcriptions (481 origin ports from 3 years, 139 destination ports from 1 year)
2. **Applies three-tier normalization**: auto-normalize high-confidence matches, flag medium-confidence for review, mark low-confidence as errors
3. **Includes human-in-the-loop** for uncertain cases

---

## Files in This Directory

### Input/Reference Files
- `../../reference_data/canonical_origin_ports.json` - 481 ports from 1883, 1889, 1897
- `../../reference_data/canonical_destination_ports.json` - 139 British ports from 1888

### Analysis Files (Generated)
- `normalization_analysis.json` - Complete analysis of all 2,037 ports
- `ports_for_review.csv` ⭐ **YOU REVIEW THIS FILE**
- `REVIEW_INSTRUCTIONS.md` - How to review the CSV

### Output Files (After You Review)
- `ttj_shipments_authority_normalized.csv` - Normalized ship records
- `ttj_cargo_details_authority_normalized.csv` - Corresponding cargo details
- `normalization_stats.json` - Statistics on normalization applied

---

## Current Status

### ✅ Phase 1-3 Complete

**Canonical ports extracted:**
- Origin: 481 ports (from 3 years: 1883, 1889, 1897)
- Destination: 139 ports (from 1 year: 1888)

**Analysis complete:**
- 1,755 origin ports → categorized into 3 tiers
- 282 destination ports → categorized into 3 tiers

### 📊 Normalization Results

#### Origin Ports (1,755 total)
| Tier | Ports | Ships | Action |
|------|-------|-------|--------|
| **Tier 1: Auto-normalized** | 404 | 26,607 | ✅ Already handled |
| **Tier 2: For review** | 230 | 7,172 | ⏸️ **YOU REVIEW** |
| **Tier 3: Errors** | 1,121 | 2,089 | ✅ Will be removed |

#### Destination Ports (282 total)
| Tier | Ports | Ships | Action |
|------|-------|-------|--------|
| **Tier 1: Auto-normalized** | 95 | 25,066 | ✅ Already handled |
| **Tier 2: For review** | 56 | 9,990 | ⏸️ **YOU REVIEW** |
| **Tier 3: Errors** | 131 | 581 | ✅ Will be removed |

### ⏸️ Waiting for Human Review

**286 ports need your review** (230 origin + 56 destination)

**Priority:**
- 22 high-frequency ports (≥100 ships) ⭐ **START HERE**
- 76 medium-frequency ports (20-99 ships)
- 188 low-frequency ports (<20 ships)

---

## How the Three Tiers Work

### Tier 1: Auto-Normalized (High Confidence ≥0.92)

**Exact matches:**
- "Riga" → Riga (canonical)
- "Boston" → Boston (canonical)

**Known variants:**
- "Cronstadt" → Kronstadt
- "G'burg" → Gothenburg
- "F'stad" → Fredrikstad
- "Dantzic" → Danzig
- "St. John, N.B." → St. John

**Fuzzy matches ≥0.92:**
- "Fredrikstadt" → Fredrikstad (0.96 similarity)
- "Charlotte Town" → Charlottetown (0.96 similarity)
- "Richibucto" → Richibouctou (0.91 similarity)

**Action:** Applied automatically, no review needed.

### Tier 2: For Review (0.85-0.92 similarity OR high-frequency unmapped)

**Examples:**
- "Oresund" (1,409 ships) - no match → **Likely legitimate** (Øresund Sound)
- "Memel" (713 ships) - no match → **Check if = Klaipeda**
- "Dram" (228 ships) → Drammen? (0.80) → **Web search needed**
- "LONDON" (3,336 ships) - no match → **Capitalization issue**

**Action:** ⏸️ **YOU REVIEW** - fill in `ports_for_review.csv`

### Tier 3: Errors (Low confidence, obvious errors)

**Examples:**
- "St" (169 ships) - fragment
- "THE TIMBER TRADES JOURNAL" - OCR artifact
- "PITWOOD" (350 ships) - commodity, not port
- Single letters, very short strings
- Very low frequency (<10 ships) with no match

**Action:** Will be removed (set to empty string).

---

## Your Review Task

### 1. Open the Review File

```
final_output/authority_normalized/ports_for_review.csv
```

### 2. For Each Port, Decide:

**ACCEPT** - Legitimate port from a year not in canonical list
- Example: "Oresund" → web search confirms it's Øresund Sound → **ACCEPT**

**MAP** - OCR variant or alternate spelling
- Example: "Dram" → "Drammen"
- Example: "LONDON" → "London"

**ERROR** - OCR garbage or not a port
- Example: "PITWOOD" → commodity, not a port → **ERROR**

### 3. Fill in Columns:

- `action`: ACCEPT / MAP / ERROR
- `map_to_port`: (only if MAP) specify the canonical port
- `notes`: (optional) your reasoning

### 4. Web Search Help

Copy the `web_search_query` column value and search to verify if port is real.

Look for:
- Wikipedia pages for the port
- Historical shipping records
- Port authority websites

### 5. Priority Order

1. **High-frequency (≥100 ships)** - 22 ports ⭐ **DO THESE FIRST**
2. Medium-frequency (20-99 ships) - 76 ports
3. Low-frequency (<20 ships) - 188 ports

---

## After You Complete Review

### Run Application Script

```bash
cd /home/jic823/TTJ\ Forest\ of\ Numbers/tools
python3 apply_normalization.py
```

This will:
1. Read your review decisions from `ports_for_review.csv`
2. Apply normalization to full dataset
3. Generate `ttj_shipments_authority_normalized.csv`
4. Generate `ttj_cargo_details_authority_normalized.csv`
5. Create statistics report

---

## Expected Results

### Origin Ports
- **Before:** 1,755 unique ports
- **After:** ~500-550 ports (481 canonical + ~20-70 from other years)
- **Reduction:** ~70% (1,200+ OCR variants eliminated)

### Destination Ports
- **Before:** 282 unique ports
- **After:** ~150-170 ports (139 canonical + ~10-30 from other years)
- **Reduction:** ~40% (100+ variants eliminated)

### Ship Records
- **All 35,870 ships preserved**
- **No data loss** - only normalization of port names
- **~90%+ ships** will have clean, canonical port names

---

## Example Review Decisions

### High-Frequency Origin Ports

| Original Port | Ships | Best Match | Your Decision | Reasoning |
|---------------|-------|------------|---------------|-----------|
| Oresund | 1,409 | Porsgrund (0.75) | ACCEPT | Øresund Sound (Denmark/Sweden) - legitimate location |
| Memel | 713 | (none) | MAP → Klaipeda | German name for Lithuanian port |
| Gefle | 662 | (none) | MAP → Gävle | Alternate spelling of Swedish port |
| Archangel | 558 | Arkhangelsk (0.80) | MAP → Arkhangelsk | English vs Russian spelling |
| Dram | 228 | Durham (0.80) | MAP → Drammen | Abbreviation of Norwegian port |

### High-Frequency Destination Ports

| Original Port | Ships | Best Match | Your Decision | Reasoning |
|---------------|-------|------------|---------------|-----------|
| LONDON | 3,336 | (none) | MAP → London | Capitalization |
| SURREY COMMERCIAL DOCKS | 2,001 | London (Surrey...) (0.84) | MAP → Surrey Commercial Docks | Accept canonical match |
| WEST HARTLEPOOL | 1,266 | (none) | ACCEPT | Real port (merged with Hartlepool in 1967) |
| PITWOOD | 350 | (none) | ERROR | Commodity, not a port |

---

## Quality Assurance

### Checks Performed
- ✅ Exact matches (case-insensitive)
- ✅ Known variant patterns (40+ mappings)
- ✅ Fuzzy similarity ≥0.85
- ✅ Frequency-based filtering
- ✅ Error detection (fragments, artifacts)

### Human Review Adds
- 🔍 Domain knowledge (historical port names)
- 🔍 Web search verification
- 🔍 Context understanding (regions, trade routes)
- 🔍 Disambiguation (similar names, abbreviations)

---

## Tools Reference

### Scripts Created
1. `extract_canonical_ports.py` - Extract canonical lists from Excel
2. `normalize_with_authority_review.py` - Three-tier analysis
3. `generate_review_csv.py` - Create review spreadsheet
4. `apply_normalization.py` - Apply your decisions

### Run Order
```bash
# Already completed:
python3 extract_canonical_ports.py
python3 normalize_with_authority_review.py
python3 generate_review_csv.py

# Your turn:
# 1. Review ports_for_review.csv
# 2. Fill in action + map_to_port columns
# 3. Save the CSV

# Then run:
python3 apply_normalization.py
```

---

## Comparison to Previous Normalization

### Old Approach (normalize_data.py)
- Fuzzy matching against parsed data itself
- No authoritative canonical list
- 1,755 → 1,465 origin ports (only 16.5% reduction)
- Many OCR variants still present

### New Approach (Authority-Based)
- Human-transcribed canonical lists as gold standard
- Three-tier confidence system
- Human review for uncertain cases
- Expected: 1,755 → ~500 origin ports (70% reduction)
- Much cleaner final dataset

---

## Questions?

**Which ports should I ACCEPT?**
- Ports you find via web search that are real
- Not in canonical list because they're from years 1874-1882, 1884-1888, 1890-1896, 1898-1899

**How do I know if it's a variant (MAP)?**
- Similar spelling to canonical port
- Historical alternate names (Memel = Klaipeda)
- OCR errors (Dram = Drammen)
- Capitalization (LONDON = London)

**When should I mark ERROR?**
- No web search results for "{port} timber port 1880s"
- Obviously not a port (commodities, journal text)
- Very low frequency (<10 ships) AND no match

**How long will this take?**
- High-frequency (22 ports): ~30-60 minutes
- Medium-frequency (76 ports): ~2-3 hours
- Low-frequency (188 ports): ~3-4 hours (or batch ERROR if no matches)
- **Total estimate:** 5-8 hours for complete review

---

**Last Updated:** October 17, 2025
**Status:** Waiting for human review of 286 ports
**Next Step:** Review `ports_for_review.csv` and fill in decisions
