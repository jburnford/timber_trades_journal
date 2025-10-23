# Cargo Parser Improvement Plan

## Overview
Based on feedback from `PARSING_FEEDBACK.md`, this plan addresses:
1. **Em-dash segmentation** - Items separated by `—` not currently split
2. **Unit word recognition** - Words like "loads", "tons" treated as commodities
3. **Item-level merchant capture** - Better per-item merchant attribution
4. **Fragment filtering** - Remove single-letter/number junk
5. **Unified parsing approach** - One regex pattern instead of multiple passes

## Current State Analysis

### What Works Well
- Semicolon splitting (line 74)
- Basic quantity-commodity extraction
- Merchant extraction per segment (lines 114-127)
- Duplicate avoidance logic (lines 95-104)

### What Needs Improvement

**1. Segmentation (Line 74)**
```python
# Current: Only splits on semicolons
segments = re.split(r';', cargo)

# Needed: Split on both semicolons AND em-dashes
segments = re.split(r'[;—]+', cargo)
```

**2. Unit Recognition (Lines 29-44)**
Current patterns only recognize abbreviated units with periods (`pcs.`, `bdls.`)

Missing: Word-form units like `loads`, `tons`, `pieces`, `bundles`, etc.

**3. Multiple Pattern Approach (Lines 82-104)**
Three separate patterns cause:
- Overlap checking complexity
- Missed item-level merchants
- Unit/commodity confusion

**4. Fragment Filtering**
No protection against:
- Single letters: `w`, `p`, `sq`, `ft`
- Measurement units as commodities: `loads`, `tons`, `square`

## Implementation Plan

### Phase 1: Create Unit Vocabulary File

Create `reference_data/units.json`:
```json
{
  "abbreviated": ["pcs", "bdls", "bgs", "doz", "lds", "fms", "std", "stds", "sq", "ft"],
  "word_forms": [
    "load", "loads",
    "ton", "tons",
    "piece", "pieces",
    "bundle", "bundles",
    "cord", "cords",
    "fathom", "fathoms",
    "standard", "standards",
    "square", "squares",
    "bag", "bags",
    "bale", "bales",
    "dozen", "dozens",
    "package", "packages"
  ],
  "fragments_to_exclude": ["w", "p", "sq", "ft", "pp", "i", "o", "s", "r", "&", "co", "bt", "rd", "er", "j", "m", "d", "f", "b", "a"],
  "commodity_whitelist": ["oak", "fir", "ash", "elm"]
}
```

### Phase 2: Rewrite Cargo Parser with Unified Regex

**New Approach** (single `finditer` per segment):

```python
def parse_cargo_string(self, cargo: str) -> List[CargoItem]:
    """Parse cargo string with em-dash support and unified regex."""

    if not cargo or len(cargo) < 3:
        return []

    items = []
    cargo = cargo.lstrip('—-').strip()

    # Split on BOTH semicolons and em-dashes
    segments = re.split(r'[;—]+', cargo)

    for segment in segments:
        segment = segment.strip()
        if not segment or len(segment) < 5:
            continue

        # UNIFIED PATTERN: Captures qty, optional unit (abbrev OR word), commodity, optional merchant
        # Pattern: \d+ <unit?> <commodity> , <merchant?>
        unified_pattern = re.compile(
            r'(?P<qty>\d[\d,]*)\s+'                              # Quantity
            r'(?:(?P<unit>' + self.unit_pattern + r')\s+)?'      # Optional unit (abbrev or word)
            r'(?P<commodity>[a-z][a-z\s&\-]{2,40}?)'            # Commodity (3-40 chars)
            r'(?:,\s*(?P<merchant>[A-Z][A-Za-z\s\.\&\'\-]+?))?'  # Optional merchant
            r'(?=\s*(?:,|;|—|$))',                              # Stop at delimiter
            re.IGNORECASE
        )

        for match in unified_pattern.finditer(segment):
            qty = match.group('qty').replace(',', '')
            unit = match.group('unit')
            commodity = match.group('commodity').strip().lower()
            merchant = match.group('merchant')

            # FILTERS
            # 1. Skip if commodity is too short (unless whitelisted)
            if len(commodity) < 3 and commodity not in self.commodity_whitelist:
                continue

            # 2. Skip if commodity is a fragment
            if commodity in self.fragments:
                continue

            # 3. Skip if "commodity" is actually a unit word
            if commodity in self.unit_words:
                continue

            # 4. Normalize unit
            if unit:
                unit = unit.lower().rstrip('.')
                if unit in self.unit_words:
                    unit = unit  # Keep word form
                # Map abbreviations to standard forms
                unit = self.normalize_unit(unit)

            # 5. Normalize merchant
            if merchant:
                merchant = self.normalize_merchant(merchant)

            items.append(CargoItem(
                quantity=qty,
                unit=unit,
                commodity=commodity,
                merchant=merchant,
                raw_text=segment[:100]
            ))

    return items
```

**Key Improvements**:
- ✅ Single regex pass (no overlap checking needed)
- ✅ Em-dash splitting
- ✅ Unit words recognized (loads, tons, etc.)
- ✅ Item-level merchant capture
- ✅ Fragment filtering
- ✅ Unit-as-commodity prevention

### Phase 3: Enhanced Merchant Normalization

Extend `normalize_merchant` in `tools/normalize_data.py`:

```python
def normalize_merchant(self, merchant: str) -> Optional[str]:
    """Normalize merchant names."""

    if not merchant:
        return None

    # 1. Placeholders → None
    placeholders = ['order', 'to order', 'in bond', 'nil', 'ditto', '']
    if merchant.lower().strip() in placeholders:
        return None

    # 2. Strip polite forms
    merchant = re.sub(r'\b(Messrs?|Mrs?|Ms)\.?\s+', '', merchant, flags=re.I)

    # 3. Strip business suffixes
    merchant = re.sub(r'\s+(Ltd|Limited|Co\.?|Company|Sons?|Brothers?)\s*$', '', merchant, flags=re.I)

    # 4. Normalize ampersand
    merchant = merchant.replace('&', 'and')

    # 5. Compact whitespace
    merchant = re.sub(r'\s+', ' ', merchant).strip()

    # 6. Strip trailing punctuation
    merchant = merchant.rstrip('.,;:')

    # 7. Title case (preserve initials)
    # e.g., "SMITH AND CO" → "Smith and Co"
    # e.g., "J. BROWN" → "J. Brown"
    words = merchant.split()
    normalized = []
    for word in words:
        if len(word) <= 2 and word.isupper():
            normalized.append(word)  # Keep initials
        elif word.lower() in ['and', 'of', 'the']:
            normalized.append(word.lower())
        else:
            normalized.append(word.capitalize())

    merchant = ' '.join(normalized)

    return merchant if merchant else None
```

### Phase 4: Unit Pattern Building

```python
def __init__(self):
    """Initialize with unit vocabulary."""

    # Load units from file
    with open('reference_data/units.json', 'r') as f:
        units_data = json.load(f)

    self.abbreviated_units = set(units_data['abbreviated'])
    self.unit_words = set(units_data['word_forms'])
    self.fragments = set(units_data['fragments_to_exclude'])
    self.commodity_whitelist = set(units_data['commodity_whitelist'])

    # Build unit pattern
    # Match either abbreviated (with optional period) or word forms
    abbrev_pattern = '|'.join(re.escape(u) for u in self.abbreviated_units)
    word_pattern = '|'.join(re.escape(u) for u in self.unit_words)

    # Pattern: (pcs|bdls|...).? OR (loads|tons|...)
    self.unit_pattern = f'(?:{abbrev_pattern})\\.?|(?:{word_pattern})'
```

## Implementation Steps

### Step 1: Create Units File (5 minutes)
- [x] Create `reference_data/units.json`
- [x] Add comprehensive unit vocabulary
- [x] Add fragment exclusion list

### Step 2: Update Cargo Parser (30-45 minutes)
- [ ] Load units vocabulary in `__init__`
- [ ] Build unified unit pattern
- [ ] Rewrite `parse_cargo_string` with:
  - Em-dash splitting
  - Single unified regex
  - Fragment filtering
  - Unit-as-commodity prevention
- [ ] Update test cases

### Step 3: Merchant Normalization (15-20 minutes)
- [ ] Enhance `normalize_merchant` in `tools/normalize_data.py`
- [ ] Add placeholder detection
- [ ] Add business suffix stripping
- [ ] Add case normalization

### Step 4: Testing (30 minutes)
- [ ] Run `cargo_parser.py` main test
- [ ] Test on known problem cases:
  - `"9,173 staves, Oppenheimer & Co. — 22,313 pcs. redwood … Order"`
  - `"1,800 loads timber"`
  - `"102 tons deals"`
  - Fragments: `"w"`, `"sq"`, etc.

### Step 5: Re-run Pipeline (varies)
- [ ] Re-parse subset (e.g., 1883 year)
- [ ] Regenerate `commodity_fixes_recommended.csv`
- [ ] Compare before/after:
  - Unit→ERROR count (expect big drop)
  - Fragment count (expect elimination)
  - Merchant attribution quality

### Step 6: Full Re-parse (if subset successful)
- [ ] Re-run full parsing pipeline
- [ ] Regenerate all analytical datasets
- [ ] Update normalization statistics

## Expected Impact

### Commodity Quality
**Before** (current):
- 1,843 records with units as commodities
- 182 fragment records
- Total fixes needed: 2,025 (1.92%)

**After** (expected):
- Units as commodities: < 100 (5x reduction)
- Fragments: 0 (complete elimination)
- Total fixes needed: < 500 (4x improvement)

### Merchant Attribution
**Before**:
- Segment-level merchant only
- Mixed segments lose item attribution
- Many "Order" placeholders

**After**:
- Item-level merchant capture
- Better handling of mixed segments
- Placeholder normalization to NULL

### Parsing Accuracy
**Before**:
- Em-dash segments not split
- Multiple pattern overlap issues

**After**:
- Proper em-dash handling
- Single unified pattern (cleaner, faster)

## Risk Assessment

### Low Risk
- ✅ Unit vocabulary addition (extends existing)
- ✅ Fragment filtering (only removes junk)
- ✅ Merchant normalization (improves quality)

### Medium Risk
- ⚠️ Unified regex (replaces 3 patterns)
  - Mitigation: Comprehensive testing on known cases
  - Rollback: Keep old version in git

### Test Coverage Needed
1. **Quantity extraction**: Ensure no regression
2. **Commodity extraction**: Verify no good data lost
3. **Merchant attribution**: Spot-check mixed segments
4. **Edge cases**:
   - Empty segments
   - Malformed input
   - Very long commodity names

## Timeline

**Quick Implementation** (2-3 hours):
- Create units file: 5 min
- Update cargo parser: 45 min
- Update merchant normalization: 20 min
- Test on sample: 30 min
- Review results: 30 min

**Full Validation** (additional 1-2 hours):
- Re-parse test year (1883): 30 min
- Generate comparison metrics: 30 min
- Review and adjust: 30 min

**Full Pipeline** (if successful):
- Re-parse all years: 2-3 hours (background)
- Regenerate datasets: 20 min
- Update documentation: 30 min

## Open Questions

1. **Merchant review workflow?**
   - Generate `merchants_for_review.csv` similar to ports?
   - Auto-normalize obvious cases ("& Co." → "and Company")?
   - **Recommendation**: Start with automatic normalization only, defer review workflow

2. **Unit standardization?**
   - Keep "loads" vs. standardize to "load"?
   - Keep abbreviations vs. expand to words?
   - **Recommendation**: Keep as-is in unit field, normalize in separate column if needed

3. **Re-parse threshold?**
   - Test on 1883 first, or jump to full re-parse?
   - **Recommendation**: Test on 1883 (1,866 OCR files), validate, then decide

4. **Backward compatibility?**
   - Keep old cargo parser as backup?
   - Version analytical datasets?
   - **Recommendation**: Git tag current state, version datasets (v1 → v2)

## Decision Point

**Proceed with implementation?**
- If YES: Start with Step 1 (create units file)
- If REVIEW FIRST: Discuss any concerns or adjustments
- If DEFER: Note reasons and revisit later

---

**Ready to implement?** Let me know and I'll begin with creating the units vocabulary file and updating the cargo parser.
