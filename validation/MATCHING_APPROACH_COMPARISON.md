# Matching Approach Comparison - 1883 Validation

## Problem Statement

Human transcription recorded 261 unique arrival dates throughout 1883, while automated OCR only extracted 51 unique dates. This created a date coverage mismatch that initially seemed to limit matching potential.

## Approaches Tested

### 1. Exact Date Matching (Initial)
- **Strategy**: Require exact date match between automated and human
- **Results**: 360 matches (14.2% precision, 7.2% recall)
- **Issue**: Too restrictive - misses ships that arrived on different days within the same week

### 2. 14-Day Date Window (Best)
- **Strategy**: Match if dates within ±14 days AND port+commodity match (85%/80% fuzzy thresholds)
- **Results**: **1,769 matches (69.9% precision, 35.4% recall)**
- **Advantages**:
  - Accounts for uncertainty in exact arrival dates
  - Handles discrepancies between recorded arrival vs publication dates
  - Still maintains quality through port/commodity fuzzy matching
  - Naturally spans adjacent publication weeks

### 3. Issue-Based Grouping (Tested)
- **Strategy**: Group records by publication issue (weekly TTJ edition), match within same issue only
- **Results**: 715 matches (28.3% precision, 14.3% recall)
- **Issue**: Too restrictive - ships arriving Jan 1-2 might be in different weekly issues
- **Overlap**: Only 199 matches in common with date-window approach

## Performance Comparison

| Approach | Matches | Precision | Recall | F1 Score |
|----------|---------|-----------|--------|----------|
| Exact date | 360 | 14.2% | 7.2% | 9.6 |
| 14-day window | **1,769** | **69.9%** | **35.4%** | **47.0** |
| Issue-based | 715 | 28.3% | 14.3% | 19.0 |

## Why 14-Day Window Wins

### Coverage Analysis
- **OCR Coverage**: 51/52 weekly issues present (98% complete)
- **Date Granularity**: Human recorded individual arrival dates, automated uses mix of arrival (49%) and publication (51%) dates
- **Not Missing Data**: We have all the issues, just different date granularity

### Example Matches Found by Date-Window but Missed by Issue-Based
```
Auto: 1883-01-01 (New York, oak)
Human: 1883-01-02 (New York, oak)
Result: Perfect match, just 1 day apart, but different publication weeks
```

```
Auto: 1883-02-09 (Pensacola, deals)
Human: 1883-02-05 (Pensacola, deals)
Result: Perfect match, 4 days apart - date window catches it
```

### Match Quality in 14-Day Window
- **Port exact matches**: 94%
- **Commodity exact matches**: 93%
- **Unit exact/similar**: 97%
- **Mean date difference**: 7 days (median: 7 days)
- **53.6% of matches within ±7 days**

The date window is generous enough to handle date uncertainty but tight enough (combined with fuzzy port/commodity matching) to maintain high accuracy.

## Recommendation

**Use 14-day date window approach** for 1883 validation:
- 2.5x more matches than issue-based
- 5x more matches than exact date
- High precision (70%) demonstrates quality
- Moderate recall (35%) limited by date coverage, not approach
- Best balance of flexibility and accuracy

## Files Generated
- `matched_pairs_1883_fixed.csv` - 14-day window (RECOMMENDED)
- `matched_pairs_1883_by_issue.csv` - Issue-based (reference only)

---
Analysis Date: 2025-10-19
Final Recommendation: 14-day date window with 85%/80% port/commodity fuzzy thresholds
