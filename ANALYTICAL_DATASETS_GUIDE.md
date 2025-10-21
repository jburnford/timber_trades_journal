# Analytical Datasets Guide

## Overview

This document describes the 5 analytical datasets generated from the TTJ (Timber Trades Journal) shipment data. These datasets provide different views of the same underlying data, optimized for different types of analysis.

**Source Data**: 69,303 shipments with 105,235 cargo items (1874-1899)

**Location**: `final_output/analytical_datasets/`

---

## 1. detailed_shipments_long.csv

**Purpose**: Master file with complete detail in LONG format (one row per cargo item)

**Rows**: 105,235 (one per cargo item)

**Columns**:
- `record_id` - Unique shipment identifier
- `date` - Publication/arrival date (YYYY-MM-DD format)
- `year` - Year extracted for analysis
- `ship_name` - Name of vessel
- `origin_port` - Departure port (normalized)
- `destination_port` - Arrival port (normalized)
- `commodity` - Type of cargo (normalized)
- `quantity` - Amount of cargo
- `unit` - Measurement unit
- `merchant` - Merchant/consignee name
- `is_steamship` - Whether vessel is steamship (TRUE/FALSE)
- `source_file` - Original TTJ issue

**Use Cases**:
- Detailed queries about specific shipments
- Filtering by ship name, merchant, or commodity
- Full-detail exports for external analysis
- Base data for custom aggregations

**Example Query**: "Show all pine timber shipments from Quebec to Liverpool in 1885"

---

## 2. trade_routes_by_year.csv

**Purpose**: Geographic analysis of trade routes over time

**Rows**: 20,979 (unique origin-destination-year combinations)

**Columns**:
- `origin_port` - Departure port
- `destination_port` - Arrival port
- `year` - Year of trade
- `num_ships` - Number of ships on this route in this year
- `num_cargo_items` - Total cargo items shipped
- `top_commodity` - Most common commodity on this route
- `top_commodity_count` - Number of items of top commodity

**Use Cases**:
- Trade route mapping and visualization
- Network analysis (which ports connected to which)
- Route importance over time
- Geographic shifts in trade patterns

**Key Findings**:
- **Top route overall**: New York → Liverpool (891 ships)
- **Peak decade**: 1880s (38,763 ships)
- **Baltic dominance**: Riga, Gothenburg, Kronstadt major exporters
- **UK import hubs**: London, Grimsby, Liverpool top destinations

**Example Analysis**: "How did Riga's exports to UK ports change 1874-1899?"

---

## 3. commodity_flows_by_year.csv

**Purpose**: Commodity analysis over time

**Rows**: 6,050 (unique commodity-year combinations)

**Columns**:
- `commodity` - Type of cargo (normalized)
- `year` - Year
- `num_ships` - Number of ships carrying this commodity
- `num_cargo_items` - Number of cargo items of this type
- `top_origin` - Most common origin port for this commodity
- `top_destination` - Most common destination port

**Use Cases**:
- Commodity trend analysis
- Rise and fall of different timber products
- Specialization patterns (which ports exported which goods)
- Market demand shifts over time

**Key Findings**:
- **Dominant commodity**: Deals (18,505 items total)
- **Mining timber surge**: Props, pitwood, pit (12,525 items)
- **Processed products**: Staves, battens, boards (12,157 items)

**Example Analysis**: "Did pit props increase with coal mining expansion in 1880s-1890s?"

---

## 4. route_commodity_matrix.csv

**Purpose**: Combined route-commodity analysis

**Rows**: 50,106 (unique origin-destination-commodity-year combinations)

**Columns**:
- `origin_port` - Departure port
- `destination_port` - Arrival port
- `commodity` - Type of cargo
- `year` - Year
- `num_ships` - Ships carrying this commodity on this route
- `num_cargo_items` - Number of items

**Use Cases**:
- Route specialization ("What did Quebec export vs. Riga?")
- Commodity-specific trade networks
- Competition analysis (multiple origins for same commodity)
- Supply chain patterns

**Key Findings**:
- **Quebec → Liverpool**: Specialized in pine, oak, red pine (large timber)
- **Baltic ports → UK**: Dominated deals, battens, boards (processed lumber)
- **North American → UK**: More raw timber, less processed goods

**Example Analysis**: "Compare timber products from North America vs. Baltic"

---

## 5. port_activity_summary.csv

**Purpose**: Port-level analysis over time

**Rows**: 7,924 (unique port-type-year combinations)

**Columns**:
- `port_name` - Port name
- `port_type` - 'origin' or 'destination'
- `year` - Year
- `num_ships` - Number of ships
- `num_cargo_items` - Total cargo items
- `top_commodity_1` - Most common commodity
- `top_commodity_2` - Second most common
- `top_commodity_3` - Third most common

**Use Cases**:
- Port importance ranking
- Specialization by port (what each port handled)
- Port activity trends over time
- Regional trade patterns

**Key Findings**:

**Top Origin Ports** (1874-1899):
1. Riga (3,738 ships) - Baltic lumber hub
2. Gothenburg (2,979 ships) - Swedish exports
3. New York (2,298 ships) - North American hub
4. Quebec (2,027 ships) - Canadian timber
5. Bordeaux (1,973 ships) - French Atlantic

**Top Destination Ports**:
1. London (9,606 ships) - Largest importer
2. Grimsby (9,038 ships) - East coast hub
3. Liverpool (8,809 ships) - Major port
4. Bristol (5,167 ships) - West England
5. Tyne (5,013 ships) - Northeast coal region

**Example Analysis**: "Which ports grew/declined over 25-year period?"

---

## Analytical Questions & Recommended Datasets

### Geography Questions
**Q**: "What were the major trade routes?"
**Use**: `trade_routes_by_year.csv`

**Q**: "Which ports were most important as exporters/importers?"
**Use**: `port_activity_summary.csv`

**Q**: "How did Baltic trade compare to North American trade?"
**Use**: `trade_routes_by_year.csv` + `port_activity_summary.csv`

### Commodity Questions
**Q**: "What types of timber were most traded?"
**Use**: `commodity_flows_by_year.csv`

**Q**: "Did pit props increase with industrial expansion?"
**Use**: `commodity_flows_by_year.csv` (filter for props, pitwood, pit)

**Q**: "When did processed lumber overtake raw timber?"
**Use**: `commodity_flows_by_year.csv` (compare deals/battens vs. timber/logs)

### Combined Questions
**Q**: "What did Quebec export vs. what Riga exported?"
**Use**: `route_commodity_matrix.csv` (group by origin)

**Q**: "Did London import different goods than Liverpool?"
**Use**: `route_commodity_matrix.csv` (group by destination)

**Q**: "Which routes specialized in which commodities?"
**Use**: `route_commodity_matrix.csv` (origin-dest-commodity combinations)

### Temporal Questions
**Q**: "How did trade change by decade?"
**Use**: Any dataset, aggregate by year/decade

**Q**: "What was the impact of 1890s economic depression?"
**Use**: `trade_routes_by_year.csv` (compare 1880s vs 1890s volumes)

### Detailed Questions
**Q**: "Show me all shipments of a specific vessel"
**Use**: `detailed_shipments_long.csv` (filter by ship_name)

**Q**: "What did merchant X import?"
**Use**: `detailed_shipments_long.csv` (filter by merchant)

---

## Data Quality Notes

### Coverage
- **Origin ports**: 91.25% coverage (621 canonical ports)
- **Destination ports**: 99%+ coverage (highly standardized)
- **Commodities**: 96% coverage (2,322 types after normalization)
- **Years**: 1874-1899 (concentration in 1880s)

### Known Issues
1. **Missing dates**: ~3,000 shipments lack publication year
2. **Quantity data**: Units not fully normalized (loads, tons, standards, etc.)
3. **Port variants**: Some rare ports (~9%) remain unmapped
4. **Commodity noise**: ~2% deleted as measurement units or fragments

### Normalization Applied
- **Ports**: Human review + fuzzy matching (province suffixes, capitalization)
- **Commodities**: Singular→plural normalization, unit removal, fragment deletion
- **Dates**: Separated year/month/day fields

---

## File Sizes

| File | Rows | Size (approx) |
|------|------|---------------|
| detailed_shipments_long.csv | 105,235 | 15 MB |
| trade_routes_by_year.csv | 20,979 | 2 MB |
| commodity_flows_by_year.csv | 6,050 | 800 KB |
| route_commodity_matrix.csv | 50,106 | 5 MB |
| port_activity_summary.csv | 7,924 | 1 MB |

**Total**: ~24 MB (all files combined)

---

## Next Steps for Analysis

### Recommended Visualizations

1. **Trade Network Map** (using `trade_routes_by_year.csv`)
   - Plot routes on map with line thickness = number of ships
   - Animated over time to show network evolution

2. **Port Timeline** (using `port_activity_summary.csv`)
   - Line chart of top 10 ports' activity over time
   - Show rise/fall of different regions

3. **Commodity Treemap** (using `commodity_flows_by_year.csv`)
   - Hierarchical view: raw vs. processed timber
   - Size by volume, color by growth rate

4. **Route Specialization Matrix** (using `route_commodity_matrix.csv`)
   - Heatmap: routes × commodities
   - Show which routes carried which goods

### Recommended Statistical Analyses

1. **Network Analysis**
   - Centrality measures (which ports were most connected)
   - Community detection (regional trade clusters)
   - Temporal network evolution

2. **Time Series Analysis**
   - Seasonal patterns in shipping
   - Impact of economic events (1893 panic)
   - Growth rates by route/commodity

3. **Spatial Analysis**
   - Geographic distribution of trade
   - Distance-based patterns
   - Regional specialization

---

## Technical Notes

### Joining Back to Original Data

All datasets can be joined back to original detailed data via `record_id`:

```python
# Example: Get full ship details for a trade route
import pandas as pd

routes = pd.read_csv('trade_routes_by_year.csv')
detailed = pd.read_csv('detailed_shipments_long.csv')

# Filter route
quebec_liverpool = routes[
    (routes['origin_port'] == 'Quebec') &
    (routes['destination_port'] == 'Liverpool') &
    (routes['year'] == 1885)
]

# Get ship details (join on record_id via detailed view)
# Note: Need to match on origin/dest/year since trade_routes is aggregated
ships = detailed[
    (detailed['origin_port'] == 'Quebec') &
    (detailed['destination_port'] == 'Liverpool') &
    (detailed['year'] == 1885)
]
```

### Aggregation Flexibility

All datasets aggregate from the same source, so custom aggregations are possible:

```python
# Example: Aggregate by different dimensions
detailed = pd.read_csv('detailed_shipments_long.csv')

# By merchant
merchant_summary = detailed.groupby('merchant').agg({
    'record_id': 'nunique',  # Unique ships
    'commodity': 'count'      # Total cargo items
}).reset_index()

# By decade
detailed['decade'] = (detailed['year'] // 10) * 10
decade_summary = detailed.groupby(['decade', 'commodity']).size()
```

---

## Contact & Documentation

For questions about data processing, normalization, or analytical methods, see:

- `DATA_PROCESSING_PIPELINE.md` - Complete pipeline documentation
- `PIPELINE_IMPROVEMENTS_SUMMARY.md` - Recent improvements and fixes
- `PLAN_TO_95_PERCENT.md` - Port normalization strategy
- `tools/generate_analytical_datasets.py` - Script to regenerate datasets

---

**Generated**: 2025-01-XX
**Data Period**: 1874-1899 (Timber Trades Journal)
**Total Shipments**: 69,303
**Total Cargo Items**: 105,235
