# Cargo Parser Noise Analysis & Improvement Plan

**Date**: 2025-11-13
**Current Output**: 196,089 cargo records (ttj_cargo_details.csv)
**Analysis**: Comprehensive review of parser noise and quality issues

## Executive Summary

The cargo parser has significant noise issues that can be addressed through better filtering and validation. Analysis reveals **5 major categories of noise** that are creating false commodity entries:

### Critical Issues Found

| Issue Type | Estimated Count | Impact | Fixable? |
|------------|----------------|--------|----------|
| Ship@port annotations | ~500-1,000 | HIGH | ✅ YES - Filter exists but not working |
| Merchant initial+name | ~400-600 | MEDIUM | ✅ YES - Needs refinement |
| Merchant name fragments | ~300-500 | MEDIUM | ✅ YES - Extend filter list |
| Empty commodities | 16,297 | HIGH | ⚠️ PARTIAL - Root cause unclear |
| Complex merged patterns | ~200-400 | LOW | ✅ YES - Better segmentation |

**Total estimated noise**: ~18,000-19,000 records (9-10% of data)

---

## Issue #1: Ship@Port Annotations Getting Through

### Problem
Despite having filter code (line 399-400 in cargo_parser.py), ship@port patterns are appearing as commodities:

```
williamson hertha @ memel
tyr @ dram
thor @ halmstad
nephews louise @ konigsberg
maclaren maud @ riga
aurora @ christiania
```

### Root Cause
The `_is_valid_commodity()` filter exists but has bugs:
1. **Filter is defined** (line 399-400): Checks for '@' symbol
2. **But it's not working** - these patterns are still in output

### Investigation Needed
```python
# Line 399-400 in cargo_parser.py
if '@' in lower:
    return False
```

This SHOULD filter all @ patterns, but they're getting through. Possibilities:
- Filter is being called AFTER items are added to results
- Component creation bypasses filter
- Encoding issues with @ symbol

### Fix Strategy
1. **Add defensive filtering** at multiple points:
   - Pre-filter in `_split_commodity_components()`
   - Post-filter in `parse_cargo_string()` before returning
   - Strengthen @ pattern detection with regex: `r'@\s*\w+'`

2. **Enhanced ship@port pattern**:
```python
# Add to invalid_commodity_patterns
re.compile(r'\w+\s*@\s*\w+', re.IGNORECASE),  # Any word @ word
re.compile(r'\([a-z]\)\s*@', re.IGNORECASE),   # (s) @ port patterns
```

3. **Add comprehensive ship name list** (already partially exists):
- Extend existing `ship_name_patterns` set with detected patterns
- Add: hertha, tyr, thor, alida, gertrud, aurora, aphrodite, etc.

### Expected Impact
- **Eliminate**: ~500-1,000 false commodity records
- **Improvement**: ~0.5% data quality gain

---

## Issue #2: Merchant Initial+Name Patterns

### Problem
Single letter + surname patterns appearing as commodities:

**Invalid (merchants):**
```
j kennedy      (47 instances) → J. Kennedy
h smith        (24 instances) → H. Smith
a dobell       (22 instances) → A. Dobell
a thomson      (16 instances) → A. Thomson
j wilkie       (8 instances)  → J. Wilkie
```

**Valid (tons/cwt of commodity):**
```
t logwood      (37 instances) → tons of logwood ✓
t boxwood      (39 instances) → tons of boxwood ✓
t ebony        (16 instances) → tons of ebony ✓
t redwood      (7 instances)  → tons of redwood ✓
c deals        (91 instances) → cwt/cords of deals ✓
```

### Current Implementation
Code already has logic for this (lines 422-442):
```python
common_unit_abbrevs = {'t', 'c', 's', 'm', 'ft', 'yd', 'lb', 'oz', 'qt', 'pt', 'pk', 'bu'}
merchant_initial_pattern = re.compile(r'^[a-z](\s+[a-z]){0,2}\s+[a-z]{3,}$', re.IGNORECASE)

if merchant_initial_pattern.match(lower):
    words = lower.split()
    if len(words) >= 2:
        last_word = words[-1]
        if last_word in self.merchant_fragments:
            return False
```

### Why It's Not Working
1. **Incomplete merchant_fragments list** - Missing many surnames:
   - Has: tagart, boysen, dahl, hughes, etc. (67 names)
   - Missing: kennedy, smith, dobell, thomson, wilkie, kerr, coltart, etc.

2. **Commodity detection not comprehensive** - Need to identify valid commodity words that can follow 't':
   - Has: Checks if in merchant_fragments
   - Missing: Whitelist of woods/materials that pair with unit abbrevs

### Fix Strategy

**Option 1: Expand merchant_fragments (Conservative)**
- Add detected merchant surnames to filter list
- Add: kennedy, smith, dobell, thomson, wilkie, kerr, coltart, horsley, alcott, etc.
- Risk: Low - only filters what we know are merchants
- Implementation: 30 minutes

**Option 2: Create commodity_materials whitelist (Aggressive)**
- Create list of known commodities that can follow unit abbreviations
- Woods: logwood, boxwood, ebony, redwood, rosewood, mahogany, oak, pine, etc.
- Logic: If `t [word]` where word is in commodity_materials → KEEP, else → FILTER
- Risk: Medium - might filter valid new materials
- Implementation: 1 hour

**Recommended: Hybrid Approach**
```python
# 1. Add comprehensive merchant surname list
self.merchant_fragments.update({
    'kennedy', 'smith', 'dobell', 'thomson', 'wilkie', 'kerr', 'coltart',
    'horsley', 'alcott', 'pantin', 'nielsen', 'sandell', 'haagensen',
    'bellhouse', 'holt', 'gardner', 'pearson', 'oliver', 'mitchell',
    'chaplin', 'herrmann', 'chaloner', 'duckett', 'becker', 'leary'
})

# 2. Add commodity materials whitelist for unit abbreviations
self.unit_commodity_materials = {
    'logwood', 'boxwood', 'ebony', 'redwood', 'rosewood', 'mahogany',
    'oak', 'pine', 'fir', 'cedar', 'walnut', 'birch', 'elm', 'ash',
    'deals', 'battens', 'boards', 'timber', 'firewood', 'staves'
}

# 3. Enhanced validation logic
if merchant_initial_pattern.match(lower):
    words = lower.split()
    if words[0] in common_unit_abbrevs and words[-1] in self.unit_commodity_materials:
        return True  # Valid unit+commodity like "t logwood"
    if words[-1] in self.merchant_fragments:
        return False  # Merchant like "j kennedy"
    # Default: be conservative - keep it
    return True
```

### Expected Impact
- **Eliminate**: ~400-500 merchant patterns (j kennedy, h smith, etc.)
- **Preserve**: ~150-200 valid unit+commodity patterns (t logwood, c deals, etc.)
- **Net improvement**: ~0.2% data quality gain

---

## Issue #3: Empty Commodities

### Problem
16,297 records (8.3% of total) have blank commodity field:

```csv
cargo_id,record_id,...,quantity,unit,commodity,merchant,raw_cargo_segment
123,45,...,,,,[empty],"some cargo string"
```

### Root Causes

**Possible causes:**
1. **Over-aggressive filtering** - Valid commodities filtered out
2. **Merchant-only segments** - Segments with only merchant info
3. **Parsing failures** - Regex doesn't match, returns empty
4. **Malformed input** - OCR artifacts that can't be parsed

### Investigation Strategy

```bash
# Find patterns in cargo strings that yield empty commodities
awk -F',' '$7 == "" {print $NF}' ttj_cargo_details.csv | sort | uniq -c | sort -rn | head -50
```

### Potential Fixes

**If over-filtering:**
- Review `_clean_component()` logic (lines 446-504)
- Check if commodity_whitelist needs expansion
- Review units_to_strip logic (line 495-496)

**If merchant-only segments:**
- These are actually CORRECT - segments like "Order." or "J. Smith & Co." alone
- Should NOT create cargo records at all
- Fix: Filter at record creation level, not component level

**If parsing failures:**
- Enhance unified_pattern regex (line 82-92)
- Add fallback patterns for common structures
- Consider logging failed parses for analysis

### Expected Impact
- Depends on root cause investigation
- Could reduce empty records by 50-80% (~8,000-13,000)
- **Improvement**: 4-7% data quality gain

---

## Issue #4: Merchant Name Fragments as Commodities

### Problem
Merchant surnames appearing standalone:

```
oppenheimer
simson
tagart
boysen
```

### Root Cause
These ARE in the `merchant_fragments` set (lines 114-126), but they're appearing anyway.

Investigation shows this is from early-format parsing where merchant names are split incorrectly:
```
Raw: "boards, Simson & Mason. Bayard @ Fredrikstad,"
Parsed:
  - "boards" ✓
  - "simson" ✗ (merchant fragment)
  - "mason bayard @ fredrikstad" ✗ (merchant + ship@port)
```

### Fix Strategy

**1. Better merchant extraction in _extract_segment()**
Current logic (lines 308-328) tries to extract merchant after commodity/quantity.

Problem: Period-delimited patterns like "Merchant. Ship @ Port" confuse it.

Enhanced pattern:
```python
# Detect and strip "Merchant. Ship @ Port" annotations
annotation_pattern = re.compile(
    r'[,\s]+([A-Z][A-Za-z\s&\.]+)\.\s+[A-Z][a-z]+\s*@\s*[A-Z][a-z]+',
    re.IGNORECASE
)
segment = annotation_pattern.sub('', segment)
```

**2. Filter standalone merchant fragments**
Add check in `_clean_component()`:
```python
# Line 501 - before returning
if cleaned in self.merchant_fragments:
    return None
```

Wait - this already exists! Line 403-404:
```python
if lower in self.merchant_fragments:
    return False
```

So why isn't it working? The issue must be:
- The fragments are being created before validation
- OR the validation isn't being called
- OR the fragments aren't in the merchant_fragments set yet

### Investigation Needed
Check if validation is called for EVERY component:
```python
# In _extract_component_items, line 362
component = self._clean_component(part)
if not component:
    continue
# Missing: Call to _is_valid_commodity()!
```

**AH-HA! Found the bug:**
- `_clean_component()` is called (line 362)
- But `_is_valid_commodity()` is ONLY called at line 501 **inside** `_clean_component()`
- The flow is: `_clean_component()` → (filters) → `_is_valid_commodity()` at end
- But the filter in `_is_valid_commodity()` line 403 checks `merchant_fragments`
- While the one at line 461-463 in `_clean_component()` should also check

Let me re-trace the code...

Actually looking more carefully:
- Line 403-404 in `_is_valid_commodity()` checks merchant_fragments
- Line 501 in `_clean_component()` calls `_is_valid_commodity()`
- So it SHOULD filter them

The issue must be: **merchant_fragments set is incomplete**.

### Fix Strategy (Revised)

**Simply add missing merchant names:**
```python
self.merchant_fragments.update({
    'oppenheimer', 'simson', 'mason', 'chaloner', 'cooper',
    'brownlee', 'walker', 'bateman', 'wilkie', 'winter'
})
```

But wait - checking line 114-126, most of these ARE already there!
- Line 115: 'boysen' ✓
- Line 115: 'tagart' ✓
- Line 124: 'webster' ✓

Hmm, let me check the actual data again...

From the head -50 output earlier:
- Line 4: commodity="oppenheimer"
- Line 12: commodity="simson"
- Line 17: commodity="tagart"
- Line 48: commodity="tagart"
- Line 49: commodity="boysen"

BUT checking cargo_parser.py lines 114-126:
- 'tagart' ✓ (line 115)
- 'boysen' ✓ (line 115)

So these fragments ARE in the list but STILL appearing in output!

**This means the filter is NOT being applied.**

Root cause must be in the data flow. Let me check when `_is_valid_commodity()` is actually called...

Looking at line 501 in `_clean_component()`:
```python
if not self._is_valid_commodity(cleaned):
    return None
```

This should filter anything in merchant_fragments (via line 403-404).

**Wait - I need to check what version of the code generated the current output!**

The output file might be from BEFORE these filters were added. Let me check git history...

Actually, looking at the final summary doc (cargo_parser_final_summary.md), it says:
- v5 (final): 306,202 cargo items
- But the current CSV has only 196,089 lines

This means the CSV is a DIFFERENT/OLDER version than what the summary describes!

### Conclusion
The current ttj_cargo_details.csv file may be from an older version of the parser. The filters may already be working in the current code, but the output file is stale.

### Fix Strategy (Final)
1. **Re-run the parser** with current code to see if issues persist
2. If they do, then debug the validation flow
3. If not, we just need to regenerate the output

---

## Issue #5: Complex Merged Patterns

### Problem
Complex merged patterns that combine multiple issues:

```
r goodman minerva @ fredrikstad    (merchant + ship @ port)
mason bayard @ fredrikstad          (merchant fragment + ship @ port)
nephews louise @ konigsberg         (merchant suffix + ship @ port)
(s) @ gothenburg                    (steamship notation + port)
```

### Root Cause
These are COMPOSITE parsing failures:
1. Merchant name not extracted properly
2. Resulting in "Merchant Ship @ Port" as commodity
3. @ filter should catch these, but isn't

### Fix Strategy

**Short-term: Regex filters**
```python
# Add to invalid_commodity_patterns
re.compile(r'\w+\s+\w+\s*@\s*\w+', re.IGNORECASE),  # word word @ word
re.compile(r'\([a-z]\)\s*@', re.IGNORECASE),         # (s) @ port
re.compile(r'^\(\w+\)$', re.IGNORECASE),             # Pure parenthetical
```

**Long-term: Better segmentation**
Fix `_extract_segment()` to properly handle:
- Period-delimited annotations: `Merchant. Ship @ Port`
- Comma-delimited annotations: `cargo, Merchant Ship @ Port`
- Parenthetical annotations: `cargo (s) @ Port`

Enhanced extraction:
```python
def _extract_segment(self, segment: str):
    # Strip ship@port annotations FIRST
    segment = re.sub(r'\w+\s*@\s*\w+', '', segment)
    segment = re.sub(r'\([a-z]\)\s*@\s*\w+', '', segment, flags=re.IGNORECASE)

    # Then extract merchant
    # ... existing logic ...
```

### Expected Impact
- **Eliminate**: ~200-400 complex merged patterns
- **Improvement**: ~0.1-0.2% data quality gain

---

## Issue #6: Missing Quantity/Unit Data

### Problem
Most records have empty quantity and unit fields:

```csv
cargo_id,...,quantity,unit,commodity,merchant
1,...,,,staves,Nickols and Colven
2,...,,,staves,H. and R. Fowler
```

But the raw cargo segment HAS quantity:
```
raw_cargo_segment: "1,300 staves, Nickols & Colven"
```

### Root Cause
The `unified_pattern` regex (lines 82-92) is NOT matching.

Why?
1. **Pattern expects quantity+commodity in sequence**: `\d+ <unit?> <commodity>`
2. **But real data has**: `\d+ <unit?> <commodity>, <merchant>`
3. **The merchant comma breaks the pattern lookahead**

Looking at line 90:
```python
r'(?=\s*(?:;|—|$)|,\s*(?:(?-i:[A-Z])|\d))',  # Lookahead
```

This expects:
- Semicolon, em-dash, or end of string
- OR comma followed by uppercase or digit

But "1,300 staves, Nickols" has:
- Comma followed by "Nickols" (uppercase) ✓ Should work!

So why isn't it matching?

**Need to test the regex pattern separately to diagnose.**

### Investigation Needed
```python
# Test the pattern
test = "1,300 staves, Nickols & Co."
pattern = re.compile(...unified_pattern...)
match = pattern.search(test)
# Does it match?
```

### Fix Strategy (Deferred)
This needs hands-on debugging:
1. Test regex against sample strings
2. Identify where pattern fails
3. Adjust lookahead/boundaries
4. Re-test

**Priority: HIGH** - But requires interactive debugging
**Estimated time**: 1-2 hours

---

## Recommended Implementation Plan

### Phase 1: Low-Hanging Fruit (1-2 hours)

**High impact, low risk improvements:**

1. **Extend merchant_fragments set** (+30 mins)
   - Add 25+ new merchant surnames from analysis
   - Test on sample data
   - Expected: -400-500 records

2. **Strengthen ship@port filters** (+30 mins)
   - Add regex patterns for complex @ patterns
   - Add pre-filtering in component split
   - Expected: -500-1,000 records

3. **Add steamship notation filter** (+15 mins)
   - Filter "(s)" and "(s.s.)" patterns
   - Expected: -50-100 records

4. **Test and validate** (+30 mins)
   - Re-run parser on sample (1000 records)
   - Compare before/after
   - Verify no good data lost

**Total expected impact: -1,000-1,600 records (~0.5-0.8% improvement)**

---

### Phase 2: Regex Debugging (2-3 hours)

**Medium impact, medium risk:**

1. **Debug unified_pattern regex** (+2 hours)
   - Write test harness
   - Test against sample cargo strings
   - Identify and fix matching failures
   - Expected: Populate quantity/unit fields for 50-70% of records

2. **Validate against corpus** (+1 hour)
   - Re-run on full dataset
   - Check for regressions
   - Measure improvement

**Total expected impact: Populate quantity/unit data (quality > quantity)**

---

### Phase 3: Structural Improvements (3-4 hours)

**High impact, higher risk:**

1. **Refactor segment extraction** (+2 hours)
   - Fix `_extract_segment()` to handle annotations
   - Strip Ship@Port BEFORE merchant extraction
   - Better period-delimited parsing

2. **Investigate empty commodities** (+1 hour)
   - Analyze root causes
   - Determine if filtering or parsing issue
   - Implement targeted fix

3. **Create commodity materials whitelist** (+1 hour)
   - List of valid woods, materials, products
   - Enhance unit+commodity validation
   - Reduce false positives on "t logwood" etc.

**Total expected impact: -8,000-13,000 empty records + better segmentation**

---

## Quick Wins (Do These First)

### Fix #1: Extend merchant_fragments (10 minutes)

Add to line 114-126 in cargo_parser.py:

```python
self.merchant_fragments = {
    # Existing entries...
    'tagart', 'boysen', 'erlundsen', 'dahl', 'sadler', 'duus', 'brown',
    # ... existing 67 names ...

    # ADD THESE NEW ONES:
    'kennedy', 'smith', 'dobell', 'thomson', 'wilkie', 'kerr', 'coltart',
    'horsley', 'alcott', 'pantin', 'nielsen', 'sandell', 'haagensen',
    'bellhouse', 'holt', 'gardner', 'pearson', 'oliver', 'mitchell',
    'chaplin', 'herrmann', 'chaloner', 'duckett', 'becker', 'leary',
    'martin', 'walker', 'cooper', 'brownlee', 'bateman', 'winter',
    'salvesen', 'graham', 'maclaren', 'singleton', 'reay', 'rayner',
    'moller', 'eaglish', 'torkildsen', 'eklund', 'bennetts', 'mcpherson',
    'hertha', 'nephews', 'wilkie', 'william', 'williamson'
}
```

### Fix #2: Strengthen @ filters (10 minutes)

Add to line 106-111 in cargo_parser.py:

```python
self.invalid_commodity_patterns = [
    re.compile(r'@\s+\w+', re.IGNORECASE),      # Existing
    re.compile(r'\(.+\)', re.IGNORECASE),        # Existing
    re.compile(r'^\d+$'),                        # Existing
    re.compile(r'^[&,;\-\.]+$'),                 # Existing

    # ADD THESE:
    re.compile(r'\w+\s*@\s*\w+', re.IGNORECASE),    # word @ word
    re.compile(r'\([a-z]+\)\s*@', re.IGNORECASE),   # (s) @ port
    re.compile(r'^\([a-z]+\)$', re.IGNORECASE),     # Standalone (s)
]
```

### Fix #3: Pre-filter annotations (15 minutes)

Add to `_extract_segment()` at line 302, right after stripping:

```python
def _extract_segment(self, segment: str) -> (str, Optional[str]):
    segment = segment.strip()
    if not segment:
        return '', None

    # ADD THIS: Pre-filter ship@port annotations
    segment = re.sub(r'\w+\s*@\s*\w+', '', segment)
    segment = re.sub(r'\([a-z]+\)\s*@\s*\w+', '', segment, flags=re.IGNORECASE)
    segment = segment.strip(' ,;')

    # ... rest of existing code ...
```

**Total time: 35 minutes**
**Expected impact: -1,000-1,500 noise records**

---

## Testing Strategy

### Before Making Changes

```bash
# Baseline metrics
wc -l ttj_cargo_details.csv
awk -F',' '$7 ~ /@/' ttj_cargo_details.csv | wc -l
awk -F',' '$7 ~ /^[a-z] [a-z]+$/' ttj_cargo_details.csv | wc -l
awk -F',' '$7 == ""' ttj_cargo_details.csv | wc -l
```

### After Each Fix

```bash
# Regenerate output
python tools/generate_two_csv_output.py

# Compare metrics
wc -l final_output/ttj_cargo_details.csv
awk -F',' '$7 ~ /@/' final_output/ttj_cargo_details.csv | wc -l
awk -F',' '$7 ~ /^[a-z] [a-z]+$/' final_output/ttj_cargo_details.csv | wc -l
awk -F',' '$7 == ""' final_output/ttj_cargo_details.csv | wc -l

# Spot check top commodities
cut -d',' -f7 final_output/ttj_cargo_details.csv | sort | uniq -c | sort -rn | head -30
```

### Validation Checks

```bash
# Ensure valid data NOT filtered
grep -i "logwood" final_output/ttj_cargo_details.csv | head -10
grep -i "deals" final_output/ttj_cargo_details.csv | head -10
grep -i "battens" final_output/ttj_cargo_details.csv | head -10

# Ensure noise IS filtered
grep "@" final_output/ttj_cargo_details.csv | head -10  # Should be empty
grep "^[0-9]*,[0-9]*,[^,]*,[0-9]*,,,oppenheimer" final_output/ttj_cargo_details.csv  # Should be empty
```

---

## Risk Assessment

### Low Risk Changes ✅
- Extending merchant_fragments set
- Adding regex patterns to invalid_commodity_patterns
- Pre-filtering annotations

**Why safe:**
- Only removes what we KNOW is noise
- No logic changes to core parsing
- Easy to verify/rollback

### Medium Risk Changes ⚠️
- Debugging/changing unified_pattern regex
- Modifying _extract_segment() logic

**Risks:**
- Could break quantity/unit extraction
- Might filter valid edge cases
- Harder to validate comprehensively

**Mitigation:**
- Test on sample data first
- Keep git history for rollback
- Generate before/after comparison reports

### High Risk Changes 🚫
- Major refactoring of parsing logic
- Changing data structures
- Modifying component extraction flow

**Recommendation:** NOT needed for this iteration. Current code structure is sound.

---

## Expected Results After Phase 1

### Noise Reduction
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total records | 196,089 | ~194,500 | -1,589 (-0.8%) |
| Ship@port patterns | ~500 | ~10 | -490 (-98%) |
| Merchant initials | ~400 | ~50 | -350 (-88%) |
| Empty commodities | 16,297 | 16,297 | 0 (needs Phase 3) |
| Valid data filtered | 0 | <10 | Acceptable |

### Quality Improvement
- **Cleaner commodity field**: Less noise in analytics
- **Better merchant attribution**: Fragments removed
- **Maintained precision**: No valid data lost

### Remaining Issues
- Empty commodities (need investigation)
- Quantity/unit extraction (need regex debugging)
- Some edge case patterns

**Recommendation: Proceed with Phase 1 quick wins.**

---

## Decision Point

**Do you want me to:**

1. ✅ **Implement Phase 1 quick wins** (35 minutes)
   - Extend merchant_fragments
   - Strengthen @ filters
   - Add pre-filtering
   - Re-generate output
   - Compare results

2. 🔍 **First investigate why existing filters aren't working**
   - Check if output CSV is stale
   - Verify current parser code
   - Test on sample data
   - Then decide on fixes

3. 📊 **Just provide the analysis** (current status)
   - No code changes yet
   - Let you review first
   - Decide what to prioritize

**My recommendation: Option 2 first** - We should verify that the current ttj_cargo_details.csv matches the current parser code. If it's stale, we might just need to regenerate. If filters are actually failing, then we implement Phase 1.
