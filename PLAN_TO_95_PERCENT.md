# Strategic Plan to Reach 95% Origin Port Coverage

**Current Coverage**: 90.38%
**Target Coverage**: 95.00%
**Gap**: 3,203 ships across 2,220 unmapped ports

---

## Analysis Summary

### Port Categories by Difficulty

| Category | Ports | Ships | % of Gap | Difficulty | Est. Time |
|----------|-------|-------|----------|------------|-----------|
| **Parser Errors** | 22 | 256 | 8.0% | Easy (code) | 2-3 hours |
| **Province Suffixes** | 93 | 220 | 6.9% | Easy (script) | 30 min |
| **Capitalization** | 38 | 66 | 2.1% | Easy (match) | 30 min |
| **Likely Variants** | 78 | 128 | 4.0% | Medium (fuzzy) | 1-2 hours |
| **Legitimate Minor** | 122 | 837 | 26.1% | Hard (research) | 6-10 hours |
| **Ambiguous Low-Freq** | 1,867 | 2,431 | 75.9% | Very Hard | 50+ hours |

**Key Insight**: The "easy fixes" (670 ships) only get us 21% of the way to 95%. We need to tackle legitimate minor ports OR accept a lower threshold.

---

## Recommended Strategy: Tiered Approach

### Phase 1: Quick Wins (670 ships = 21% of gap)
**Effort**: 4-6 hours | **Coverage gain**: +0.97 percentage points

#### 1A. Fix Parser Errors (256 ships)
**Problem**: "St", "ST", "W", and other fragments
- **Root cause**: Parser truncating at wrong delimiters in non-@ formats
- **Solution**: Investigate condensed/dash patterns, apply same lookahead fix
- **Effort**: 2-3 hours coding + testing

#### 1B. Strip Province Suffixes (220 ships)
**Examples**: "Shediac, N.B." → "Shediac"
- **Solution**: Simple regex replace in normalization
- **Effort**: 30 minutes

#### 1C. Fix Capitalization (66 ships)
**Examples**: "ARCHANGEL" → "Archangel", "MEMEL" → "Memel"
- **Solution**: Case-insensitive matching to canonical
- **Bad data items**: "WORKING MACHINERY", "GRATEFUL AND COMFORTING" (mark as ERROR)
- **Effort**: 30 minutes

#### 1D. Map Obvious Variants (128 ships)
**Examples**: Parrsborough→Parrsboro, Essviken→Essvik
- **Solution**: Fuzzy match with high threshold (>90% similarity)
- **Effort**: 1-2 hours to verify and map

**Phase 1 Result**: 90.38% → 91.35% coverage

---

### Phase 2: Moderate Effort - Top Legitimate Ports (1,000-1,500 ships)
**Effort**: 6-10 hours | **Coverage gain**: +1.4 to +2.2 percentage points

Focus on ports with **5+ ships** from "Legitimate Minor" category (122 ports, 837 ships) PLUS selected ambiguous ports.

#### Strategy: Web Research + Batch Mapping
1. **Extract top 200 ports** (5+ ships each)
2. **Web research** using: Wikipedia port lists, GeoNames, Maritime gazetteers
3. **Batch classify**:
   - ACCEPT (if verified as real port)
   - MAP (if variant of known port)
   - ERROR (if obviously bad data)

#### High-Value Targets (54+ ships):
- **W. C. Africa** (54) - Map to "West Coast Africa" or canonical variant
- Plus 20-30 ports with 8-10 ships each

#### Tools to Use:
- GeoNames API (free for research)
- Wikipedia "List of ports by country"
- Historic port gazetteers (19th century focus)

**Phase 2 Result**: 91.35% → 92.75% to 93.55%

---

### Phase 3: Decision Point - Is 95% Achievable?

After Phases 1-2, we'll have mapped **~1,670 to 2,170 ships** (52-68% of gap).

**Remaining gap**: ~1,500 to 1,033 ships across ~1,700 low-frequency ports

#### Option A: Push to 95% (10-20 additional hours)
- Requires researching 300-500 ports with 2-4 ships each
- Diminishing returns (lots of effort for small gains)
- Risk: Many may be OCR errors or variants we can't verify

#### Option B: Accept 92-93.5% as Excellent
- Demonstrates thorough data cleaning
- Focus effort on other aspects (analysis, visualization)
- Document limitations transparently

#### Option C: Targeted "Low-Hanging Fruit" from Ambiguous
- Review top 100 ambiguous ports (4+ ships each)
- Pick obvious ones (Cork, Galway, Hobart Town, San Domingo)
- Get another 200-300 ships with 2-3 hours effort

**My Recommendation**: Phase 1 + Phase 2 + Option C = **93-94% coverage**

---

## Detailed Action Plan

### Week 1: Quick Wins (Phase 1)

#### Task 1.1: Fix "St" Parser Bug
**Time**: 2-3 hours

1. Identify which parsing patterns still fail (likely `condensed_dash_pattern`)
2. Apply lookahead fix to all patterns
3. Test on sample "St" records
4. Re-run parsing pipeline
5. Verify 169+50 = 219 ships now capture full port names

#### Task 1.2: Province Suffix Script
**Time**: 30 minutes

Create `strip_canadian_suffixes.py`:
```python
# Map ports with suffixes to base names
suffixes = [', N.B.', ', N.S.', ', P.E.I.']
for suffix in suffixes:
    if port.endswith(suffix):
        base_port = port.replace(suffix, '')
        # Add to ports_completed.csv as MAP
```

#### Task 1.3: Capitalization Fix
**Time**: 30 minutes

Modify `apply_normalization.py` to do case-insensitive canonical matching:
```python
# Before exact match, try lowercase match
port_lower = original.lower()
for canon in canonical_origin:
    if port_lower == canon.lower():
        row['origin_port'] = canon
        break
```

Mark obvious bad data as ERROR:
- "WORKING MACHINERY"
- "GRATEFUL AND COMFORTING"
- "OUT OF PACKING"

#### Task 1.4: Fuzzy Variant Mapping
**Time**: 1-2 hours

Use existing fuzzy matcher to map high-confidence variants (>90% similarity):
- Parrsborough → Parrsboro (10 ships)
- Essviken → Essvik (9 ships)
- ~70 others

**Deliverable**: Updated `ports_completed.csv` with 78 new mappings

---

### Week 2: Moderate Effort (Phase 2)

#### Task 2.1: Top 50 Legitimate Ports Research
**Time**: 4-6 hours

Systematically research top 50 ports (5+ ships each):
1. W. C. Africa (54 ships)
2. Trehiguier through Soon (10-8 ships each)

**Research sources**:
- Wikipedia: "List of ports in [country]"
- GeoNames: Search by name
- Historic gazetteers: 19th century port references

**Output**: Add to `ports_completed.csv`:
- ACCEPT if verified
- MAP if variant
- ERROR if clearly bad

#### Task 2.2: Opportunistic Ambiguous Ports
**Time**: 2-3 hours

Review obvious legitimate ports from ambiguous category:
- Cork (4 ships) - Irish port, ACCEPT
- Galway (4 ships) - Irish port, ACCEPT
- Hobart Town (4 ships) - Tasmania, ACCEPT
- San Domingo (4 ships) - Dominican Republic, MAP to Santo Domingo
- Frontera (4 ships) - Mexican port, ACCEPT
- ~20-30 more obvious ones

**Deliverable**: Add 30-50 more ports to canonical

---

## Implementation Steps

### Step 1: Run Phase 1 Fixes (This Week)
```bash
# 1. Fix parser (manual code changes)
# 2. Add province suffix mappings
cd "/home/jic823/TTJ Forest of Numbers/final_output/authority_normalized"
# Add to ports_completed.csv

# 3. Re-run normalization
cd ../tools
python3 apply_normalization.py

# 4. Check coverage
python3 -c "import csv, json; ..." # Coverage calculation
```

### Step 2: Generate Research List (Next Session)
```bash
# Extract top 200 ports needing research
python3 generate_research_list.py
# Output: ports_for_research.csv (sorted by ship count)
```

### Step 3: Batch Research and Map (Ongoing)
- Work through 20-30 ports per session
- Add decisions to `ports_completed.csv`
- Re-run normalization periodically
- Track progress

---

## Realistic Outcome Projections

### Conservative Estimate (Phase 1 only)
- **Coverage**: 91.35%
- **Effort**: 4-6 hours
- **Ships mapped**: 670

### Moderate Estimate (Phase 1 + Partial Phase 2)
- **Coverage**: 92.5% to 93.0%
- **Effort**: 10-15 hours
- **Ships mapped**: 1,200 to 1,500

### Aggressive Estimate (All phases + targeted ambiguous)
- **Coverage**: 93.5% to 94.5%
- **Effort**: 20-30 hours
- **Ships mapped**: 2,000 to 2,500

### To Actually Hit 95%
- **Effort**: 40-60 hours (not recommended)
- Requires researching 1,700+ low-frequency ports
- Many will be unverifiable or errors

---

## Recommended Decision

**Target**: 93-94% coverage through focused effort

**Rationale**:
1. **Phase 1** (quick wins) is high ROI - must do
2. **Phase 2** (top legitimate ports) is reasonable - worth doing
3. **Pushing to 95%** hits diminishing returns - not recommended
4. **93-94% is academically excellent** and defensible

**Documentation Strategy**:
- Report coverage transparently
- Note: "90.4% → 93.5% through systematic classification"
- Explain: "Remaining 6.5% are primarily low-frequency ports (1-3 ships) that are difficult to verify from historical records"
- Strength: "94% coverage on categorical data matches validation findings"

---

## Next Session Plan

**Immediate**: Implement Phase 1 fixes
1. Fix "St" parser bug (2-3 hours)
2. Add province suffix mappings (30 min)
3. Add capitalization matching (30 min)
4. Map fuzzy variants (1-2 hours)

**Goal**: Get to 91.35% coverage with <6 hours effort

**Then Decide**: Is 91.35% sufficient, or continue to Phase 2?

---

**End of Plan**
