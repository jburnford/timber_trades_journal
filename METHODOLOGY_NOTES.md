# Methodology Notes & Improvements

## Overview
This document captures lessons learned, methodology improvements, and recommendations for similar historical OCR projects based on the TTJ (Timber Trades Journal) digitization project.

**Date**: October 20, 2025
**Dataset**: 1,866 pages, 1874-1899, ~100K shipment records
**Validation**: 1883 London imports (1,769 matched pairs against human transcription)

---

## Core Methodology: What Works

### 1. Multi-Page Context-Aware Parsing ✓

**Problem**: Historical documents often span multiple pages, tables continue across boundaries.

**Solution**: Group files by base document, process sequentially.

```python
# Group: 18830106p.12_p001.txt, 18830106p.12_p002.txt → One document
# Process pages in order, maintain parser context
```

**Result**: Captures table rows that span pages, maintains context for abbreviated entries.

**Recommendation**: Essential for any multi-page table extraction project.

---

### 2. Two-CSV Relational Structure ✓

**Why Two CSVs?**

1. **Shipments CSV** (90K records): One row per ship arrival
   - Enables: Route analysis, temporal patterns, ship frequency

2. **Cargo Details CSV** (140K records): One row per cargo item
   - Enables: Commodity analysis, volume tracking, merchant networks

**Linked via**: `record_id` field

**Benefits**:
- Avoids data duplication
- Supports both aggregate and granular analysis
- Standard relational database pattern
- Easy to query with SQL/pandas joins

**Recommendation**: Use relational design even for "simple" CSV exports. Avoid denormalization unless specifically needed for tool compatibility.

---

### 3. Three-Tier Port Normalization ✓

**Tier 1: Human Review** (Highest Priority)
- ACCEPT: Verified legitimate variants
- MAP: Historical spellings → modern forms
- ERROR: Remove OCR errors

**Tier 2: Automatic Fuzzy Matching**
- Exact: Keep as-is
- High confidence (≥90%): Auto-normalize
- Medium (85-89%): Auto-normalize with flag
- Low (<85%): Send to human review

**Tier 3: Unchanged**
- Flag for future review

**Why This Works**:
- Human expertise for ambiguous cases
- Automation for obvious matches
- Incremental improvement (review file grows over time)
- Traceable decisions (review CSV documents all mappings)

**Key Insight**: Start with high-frequency ports (most impact), work down to rare variants.

**Recommendation**: **DO NOT attempt fully automated normalization for historical text**. Domain expertise is essential for distinguishing legitimate variants from OCR errors.

---

## Matching Strategies: What We Learned

### Date-Based Matching Evolution

#### Attempt 1: Exact Date Matching
- **Strategy**: Require exact date match
- **Result**: 360 matches (14.2% precision)
- **Problem**: Too restrictive

#### Attempt 2: 14-Day Date Window ✓ WINNER
- **Strategy**: Match if within ±14 days AND port+commodity match (85%/80% fuzzy)
- **Result**: 1,769 matches (69.9% precision, 35.4% recall)
- **Why It Works**:
  - Accounts for uncertainty in arrival vs publication dates
  - Handles reporting lag (ship arrives Monday, reported in Saturday issue)
  - Still maintains quality through fuzzy port/commodity matching

#### Attempt 3: Issue-Based Grouping
- **Strategy**: Match only within same weekly publication
- **Result**: 715 matches (28.3% precision)
- **Problem**: Too restrictive, ships arriving Jan 1-2 in different weekly issues

**Recommendation**: For historical datasets with date ambiguity, use **date windows** (7-14 days typical) combined with high-quality categorical matching.

---

## Field-Level Accuracy Findings

### Categorical Fields: EXCELLENT (93-94% perfect)

#### Ports (94% perfect matches)
**Error Types**:
- 85% are 1-2 character typos: Fredrikstadt/Fredrikstad
- 15% are substring issues: Liscomb/Liscombe
- Mostly OCR character recognition, not structural

**Implications**:
- ✓ Reliable for route analysis
- ✓ Fuzzy matching handles variants perfectly
- ✓ Can trust for categorical analysis

#### Commodities (93% perfect matches)
**Error Types**:
- 91% are plural/singular: sleeper/sleepers, board/boards
- 8% are compound terms: "red wood" vs "redwood"
- <1% are actual errors

**Implications**:
- ✓ Reliable for commodity analysis
- ✓ Errors are semantic equivalents (boards = board)
- ✓ Fuzzy matching or simple normalization handles this

#### Units (97% exact or similar)
**Error Types**:
- Mostly abbreviation variations: "t." vs "tons"

**Implications**:
- ✓ Very reliable
- ✓ Simple mapping handles variants

---

### Numerical Fields: MODERATE (38% exact, 44% within 10%)

#### Quantities: Challenging
**Accuracy**:
- 37.6% exact matches
- 44.3% within 10%
- 55.7% differ by >50%

**Error Patterns**:
- **75% have wrong first digit** (not just OCR substitution)
- **Most common confusions**: 1↔2 (153 cases), 1↔3 (67 cases)
- **Not simple factor errors**: Only 21% are 2x/5x/10x mistakes
- **Catastrophic failures**: Some off by 100-1000x

**Root Causes** (likely):
1. Reading wrong table cells
2. Multi-line number parsing issues
3. Confusion with adjacent columns
4. Not just character-level OCR errors

**Implications**:
- ⚠ Use for **aggregate trends only**
- ⚠ Individual values not reliable
- ⚠ Manual verification for critical applications
- ✓ Good enough for: "Did trade volumes increase 1885-1890?"
- ✗ Not good enough for: "What exact tonnage arrived from Riga in July 1887?"

---

## Key Recommendations for Similar Projects

### 1. Plan for Validation Early

**What We Did**:
- Identified 1883 as validation year (had human transcription)
- Built matching algorithms with fuzzy logic
- Systematically compared field-by-field

**Results**:
- Quantified accuracy: 94% ports, 93% commodities, 38% quantities
- Identified error patterns: Categorical good, numerical problematic
- Provided confidence intervals for analysis

**Recommendation**: **Budget 10-15% of project time for validation**. Essential for:
- Understanding data quality
- Setting appropriate research questions
- Disclaimers in publications
- Methodology papers

---

### 2. Categorical Data First, Numerical Data Second

**Insight from Our Validation**:
Port and commodity extraction is **highly reliable** (93-94% perfect).
Quantity extraction is **moderately reliable** (44% within 10%).

**Project Design Implication**:
- Research questions based on **routes, commodities, temporal patterns**: ✓ High confidence
- Research questions based on **exact volumes, price calculations**: ⚠ Requires validation

**Recommendation**: Design research questions around what OCR does well. For historical documents:
- ✓ Who traded with whom (categorical)
- ✓ What commodities moved (categorical)
- ✓ Temporal trends (dates + categories)
- ⚠ Exact quantities (numerical)

---

### 3. Human-in-the-Loop for Domain-Specific Normalization

**What We Did**:
- Generated initial port list with fuzzy matching
- Flagged ambiguous cases for human review
- Human reviewed ~50 high-frequency variants
- Applied decisions to full dataset

**Why This Works**:
- Historical port names require domain knowledge (Memel vs Klaipeda)
- OCR errors mimic legitimate variants
- Rare variants might be OCR errors OR real minor ports
- Ship counts help prioritize (713 ships from "Memel" → definitely real)

**Recommendation**: **Do NOT fully automate historical entity normalization**. Use:
1. Automatic matching for obvious cases (>95% similarity)
2. Human review for medium cases (80-95% similarity)
3. Research + web search for rare cases
4. Document all decisions in review file

---

### 4. Incremental Processing with Checkpoints

**Our Pipeline**:
```
OCR (1,866 files)
  ↓ [Checkpoint: parsed_output/]
Parse (100K records)
  ↓ [Checkpoint: final_output/]
Split CSVs (shipments + cargo)
  ↓ [Checkpoint: authority_normalized/]
Normalize ports
  ↓ [Checkpoint: review files]
Flag new variants
```

**Benefits**:
- Can re-run from any checkpoint
- Easy to update (e.g., add OCR files, re-parse)
- Human review file accumulates knowledge
- Debugging easier (isolate which step failed)

**Recommendation**: **Design pipelines to be re-runnable**. Avoid monolithic scripts that do everything in one pass.

---

## Methodology Improvements for Next Time

### 1. Earlier Validation

**What We Did**: Processed all data, then validated 1883.

**Better Approach**:
- Validate on 5-10% sample BEFORE processing all data
- Iterate on parsing/normalization based on validation
- Then process full dataset

**Why**: We discovered quantity issues late. Could have investigated OCR settings or alternate tools earlier.

---

### 2. Quantity Extraction Research

**What We Know**:
- Quantities have high error rates
- Not simple OCR substitution
- Likely structural parsing issues

**Future Work**:
- Sample failing cases manually
- Examine original images
- Determine if:
  - OCR reading wrong cells?
  - Table structure confusing parser?
  - Need different OCR tool for numbers?

**Potential Solutions**:
- Specialized OCR for tabular numeric data
- Computer vision for table structure
- Post-OCR validation (sanity checks on numbers)

---

### 3. Hybrid Arrival Date Extraction

**Current**:
- 49% of records have arrival dates (extracted from text)
- 51% use publication dates (from filename)

**Issue**: This creates date granularity mismatch with human transcription (which recorded specific arrival dates).

**Future Improvement**:
- Investigate why arrival dates missing
- Check if OCR missing date columns
- Consider computer vision for table structure
- Or: Use publication dates systematically, acknowledge limitation

---

### 4. Merchant Data Cleaning

**Current**: Merchant field has:
- Company names
- Individual names
- "Order" (no merchant specified)
- Mixed formats

**Future Work**:
- Normalize merchant names (like we did for ports)
- Distinguish companies vs individuals
- Entity resolution (same merchant, different spellings)

**Use Case**: Network analysis of trading relationships

---

## Statistical Summary for Publication

### Dataset Characteristics
- **Temporal Coverage**: 1874-1899 (25 years)
- **Geographic Coverage**: Global timber trade to UK
- **Record Count**: ~100,000 ship arrivals, ~150,000 cargo items
- **Data Source**: Timber Trades Journal (weekly publication)
- **OCR Technology**: Google Gemini 2.5 Pro Vision
- **Processing Time**: 33.9 hours OCR + parsing/normalization

### Validation Results (1883 London Imports, N=1,769 matched pairs)
- **Port Accuracy**: 94.0% exact matches, 100% within fuzzy threshold
- **Commodity Accuracy**: 93.0% exact matches, 100% within fuzzy threshold
- **Unit Accuracy**: 97.2% exact or semantically equivalent
- **Quantity Accuracy**: 37.6% exact, 44.3% within 10%, 55.7% >10% error
- **Matching Precision**: 69.9% (automated records matched to human)
- **Matching Recall**: 35.4% (human records matched to automated)

### Quality Assessment
**Categorical data (ports, commodities, units)**: Excellent reliability for research use
**Numerical data (quantities)**: Moderate reliability, suitable for aggregate trends only
**Temporal data (dates)**: Good coverage, hybrid approach (49% arrival, 51% publication dates)

---

## Replication & Transparency

### Published Artifacts
1. **Complete pipeline code**: All scripts in `tools/` directory
2. **Validation dataset**: 1883 matched pairs available
3. **Review decisions**: `ports_completed.csv` documents all normalizations
4. **Processing logs**: OCR statistics, parsing outputs
5. **Methodology documentation**: This file + DATA_PROCESSING_PLAN.md

### Reproducibility
- Pipeline re-runnable from any checkpoint
- Human review decisions documented and version-controlled
- Validation methodology described for replication
- Known limitations explicitly stated

### Recommended Citation Format
"Data extracted using Gemini 2.5 Pro OCR with contextual parsing (94% port accuracy, 93% commodity accuracy, 38% quantity exact matches based on 1883 validation sample, N=1,769). Quantities suitable for aggregate analysis only; see methodology documentation for details."

---

## Future Extensions

### Potential Improvements
1. **Quantity accuracy**: Investigate structural parsing improvements
2. **Merchant normalization**: Apply port normalization approach to merchant names
3. **Additional validation**: Validate 1889 (no quantities), other years
4. **Temporal modeling**: Statistical models for trade volume trends
5. **Network analysis**: Merchant and route networks over time

### Scaling to Other Journals
This methodology applicable to any:
- Historical tabular data
- Multi-page documents
- Domain-specific entity normalization
- Mixed categorical/numerical extraction

**Key Success Factors**:
- Plan validation early
- Human-in-the-loop for domain knowledge
- Incremental, checkpointed processing
- Clear documentation of decisions
- Transparent reporting of limitations

---

**Last Updated**: October 20, 2025
**Status**: Methodology validated, full processing in progress
**Next Steps**: Apply to remaining TTJ years (1900-1920s), extend to other timber trade journals
