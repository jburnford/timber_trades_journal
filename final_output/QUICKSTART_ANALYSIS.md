# TTJ Dataset - Quick Start Guide for Analysis

**For:** Stéphane (UQTR) and collaborators
**Dataset:** 35,870 ship arrivals, 58,602 cargo items (1874-1899)
**Last Updated:** October 17, 2025

---

## Dataset Versions

### Original Data (Recommended for Most Uses)

**Location:** `final_output/`
- `ttj_shipments.csv` - 35,870 ship arrival records
- `ttj_cargo_details.csv` - 58,602 cargo line items

**Use when:** You want the raw parsed data exactly as it appeared in the journals.

### Normalized Data (Recommended for Aggregation)

**Location:** `final_output/normalized/`
- `ttj_shipments_normalized.csv` - Port names and merchants standardized
- `ttj_cargo_details_normalized.csv` - Commodity names standardized

**Use when:** You want cleaner aggregations (e.g., counting ships by port, analyzing commodity flows).

**Key improvements:**
- 290 port variants merged (Frederickstadt → Fredrikstad, etc.)
- Capitalization standardized (LONDON → London)
- OCR errors corrected (boars → boards)
- Placeholders removed (Order → empty)

---

## File Structure

### ttj_shipments.csv (One row per ship)

```csv
record_id,source_file,line_number,ship_name,origin_port,destination_port,merchant,
arrival_day,arrival_month,arrival_year,publication_day,publication_month,publication_year,
is_steamship,format_type,confidence
```

**Key fields:**
- `record_id`: Unique ID (1-35,870) - use to join with cargo_details
- `origin_port`: Port of departure (100% coverage)
- `destination_port`: British port of arrival (99.4% coverage)
- `merchant`: Receiving merchant (82.6% coverage)
- `arrival_*`: Date from journal content (68.9% coverage)
- `publication_*`: Date from filename (100% coverage) - use as fallback!
- `is_steamship`: True/False (True = steam, False = sail)

### ttj_cargo_details.csv (Multiple rows per ship)

```csv
cargo_id,record_id,source_file,line_number,quantity,unit,commodity,merchant,raw_cargo_segment
```

**Key fields:**
- `cargo_id`: Unique cargo item ID (1-58,602)
- `record_id`: Links to ttj_shipments.csv
- `quantity`: Numeric quantity (~60% coverage)
- `unit`: pcs., bdls., fms., etc. (~40% coverage)
- `commodity`: Type of wood/product (100% coverage)
- `merchant`: Merchant for this specific cargo item (~85% coverage)

**Note:** Merchant in cargo_details may differ from shipments (multi-merchant cargoes).

---

## Quick Analysis Recipes

### 1. Top Trade Routes (Python/Pandas)

```python
import pandas as pd

# Load data
ships = pd.read_csv('ttj_shipments_normalized.csv')

# Count routes
routes = ships.groupby(['origin_port', 'destination_port']).size()
top_routes = routes.sort_values(ascending=False).head(20)

print(top_routes)
```

### 2. Commodity Analysis

```python
# Load cargo data
cargo = pd.read_csv('ttj_cargo_details_normalized.csv')

# Top commodities
top_commodities = cargo['commodity'].value_counts().head(30)

# Commodities by origin (join with ships)
ships_cargo = cargo.merge(ships[['record_id', 'origin_port']], on='record_id')
commodity_by_origin = ships_cargo.groupby(['origin_port', 'commodity']).size()
```

### 3. Temporal Patterns

```python
# Use publication dates (100% coverage)
ships['date'] = pd.to_datetime(
    ships['publication_year'].astype(str) + '-' +
    ships['publication_month'] + '-' +
    ships['publication_day'].astype(str)
)

# Monthly arrivals
monthly = ships.groupby(pd.Grouper(key='date', freq='M')).size()

# Yearly trends by origin
yearly = ships.groupby([ships['date'].dt.year, 'origin_port']).size()
```

### 4. Merchant Networks

```python
# Remove empty merchants
merchants = cargo[cargo['merchant'].notna() & (cargo['merchant'] != '')]

# Top merchants
top_merchants = merchants['merchant'].value_counts().head(50)

# Merchant specialization (commodities they handled)
merchant_commodities = merchants.groupby(['merchant', 'commodity']).size()
```

### 5. Steam vs Sail Analysis

```python
# Compare steamships vs sail
steam_vs_sail = ships.groupby(['is_steamship', ships['date'].dt.year]).size()

# By route
route_tech = ships.groupby(['origin_port', 'destination_port', 'is_steamship']).size()
```

---

## Important Data Notes

### 1. Dates: Arrival vs Publication

**Problem:** Only 68.9% of ships have explicit arrival dates in the journal text.

**Solution:** Use `publication_*` fields as fallback.

```python
# Create best available date
ships['best_date'] = pd.to_datetime(
    ships['arrival_year'].fillna(ships['publication_year']).astype(int).astype(str) + '-' +
    ships['arrival_month'].fillna(ships['publication_month']) + '-' +
    ships['arrival_day'].fillna(ships['publication_day']).astype(int).astype(str)
)
```

**Note:** Publication dates are typically 1-7 days after arrival. A May 1 journal issue reports late April arrivals.

### 2. Multiple Merchants per Ship

**Problem:** Some ships have multiple merchants (one per cargo item).

**Example:**
```
Ship: Andreas from Fredrikstad
  Cargo 1: 1,300 staves → Nickols & Colven
  Cargo 2: 41,500 staves → H. & R. Fowler
  Cargo 3: 9,173 staves → Oppenheimer & Co.
```

**Solution:** Use `ttj_cargo_details.csv` for merchant-level analysis, not `ttj_shipments.csv`.

### 3. Quantities and Units

**Problem:** Units are inconsistent (pcs., doz., stds., fms., bdls., etc.).

**Not normalized:** We did NOT convert quantities to standard units (e.g., cubic meters) due to complexity.

**Recommendation:**
- Focus on commodity types and ship counts rather than volume aggregation
- If you need volumes, create conversion factors manually for key units

### 4. Missing Destination Ports

**Coverage:** 99.4% (35,637/35,870)

**Missing:** 233 records (0.6%) from files starting mid-document

**Solution:** These are at the beginning of files - you can infer port from surrounding records if needed.

---

## Data Quality Checks

### Run These Checks Before Analysis

```python
# Check for missing values
print("Missing destination ports:", ships['destination_port'].isna().sum())
print("Missing arrival dates:", ships['arrival_day'].isna().sum())
print("Missing merchants:", ships['merchant'].isna().sum())

# Check date ranges
print("Publication date range:", ships['publication_year'].min(), "-", ships['publication_year'].max())

# Verify joins
print("Ships:", len(ships))
print("Cargo items:", len(cargo))
print("Ships with cargo:", cargo['record_id'].nunique())
```

Expected output:
```
Missing destination ports: 233
Missing arrival dates: 11173
Missing merchants: 6251
Publication date range: 1874 - 1899
Ships: 35870
Cargo items: 58602
Ships with cargo: 33970
```

---

## Common Analysis Pitfalls

### ❌ DON'T: Join cargo to ships without considering duplicates

```python
# WRONG - creates duplicate ships (one per cargo item)
bad_join = cargo.merge(ships, on='record_id')
ship_count = len(bad_join)  # This is cargo_count, not ship_count!
```

### ✅ DO: Aggregate cargo first, then join

```python
# CORRECT - aggregate cargo by ship first
cargo_summary = cargo.groupby('record_id').agg({
    'commodity': lambda x: ', '.join(x),
    'quantity': 'sum'
}).reset_index()

good_join = ships.merge(cargo_summary, on='record_id', how='left')
ship_count = len(good_join)  # Correct: 35,870 ships
```

### ❌ DON'T: Use arrival dates without fallback

```python
# WRONG - loses 31% of records
dated_ships = ships[ships['arrival_year'].notna()]  # Only 68.9%
```

### ✅ DO: Use publication dates as fallback

```python
# CORRECT - 100% coverage
ships['year'] = ships['arrival_year'].fillna(ships['publication_year'])
```

---

## Reference Data

### Top Origin Ports (from normalized data)

| Port | Count | Region |
|------|-------|--------|
| Riga | 1,970 | Baltic (Latvia) |
| Gothenburg | 1,546 | Sweden |
| Quebec | 1,380 | Canada |
| Cronstadt | 1,210 | Russia |
| New York | 1,087 | USA |
| Christiania | 966 | Norway (Oslo) |
| Sundswall | 920 | Sweden |
| Bordeaux | 821 | France |

### Top Commodities

| Commodity | Count |
|-----------|-------|
| deals | 10,974 |
| props | 3,387 |
| staves | 2,802 |
| battens | 2,560 |
| pit/pitwood | 4,635 combined |
| firewood | 2,122 |
| boards | 1,798 |
| timber | 1,580 |

### Key Units

| Unit | Meaning |
|------|---------|
| pcs. | pieces |
| bdls. | bundles |
| doz. | dozen |
| fms. | fathoms (6 feet) |
| lds. | loads |
| stds. | standards |
| tons | tons (weight) |

---

## Getting Help

### Documentation

1. **README_DATASET.md** - Full dataset documentation (original data)
2. **README_NORMALIZED.md** - Normalization methodology and quality metrics
3. **QUICKSTART_ANALYSIS.md** - This file

### Common Questions

**Q: Which dataset should I use?**
A: Start with normalized for cleaner aggregations. Use original if you need exact historical spellings.

**Q: Why are some merchants missing?**
A: 17.4% of records have no merchant (journal used "Order" as placeholder). This is normal for the period.

**Q: Can I trust the dates?**
A: Publication dates are 100% reliable. Arrival dates (68.9%) are from journal content. Use publication as fallback.

**Q: How do I handle quantities?**
A: Units aren't standardized. Focus on commodity types and ship counts unless you need volumes (requires manual conversion).

**Q: Some ports look wrong (e.g., "---", "Order")?**
A: These are OCR errors or data artifacts. Use normalized data to reduce these.

---

## Next Steps

1. **Load the data:** Start with `ttj_shipments_normalized.csv` and `ttj_cargo_details_normalized.csv`
2. **Explore top ports:** What are the major trade routes?
3. **Temporal analysis:** How did trade patterns change 1874-1899?
4. **Commodity flows:** Which ports exported which products?
5. **Merchant networks:** Who handled which commodities from which origins?
6. **Technology adoption:** How did steamship usage evolve?

---

## Contact

For questions about the data:
- Dataset issues: Check README_DATASET.md
- Normalization: Check README_NORMALIZED.md
- Technical details: See `/tools/*.py` source code

**Good luck with your analysis!**

---

**Generated:** October 17, 2025
**Dataset Version:** 1.0
**Coverage:** 1874-1899 (25 years)
**Records:** 35,870 ships, 58,602 cargo items
