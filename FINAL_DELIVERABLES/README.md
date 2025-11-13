# TTJ Forest of Numbers - Final Deliverables

**Generated:** November 12, 2025  
**Status:** Production-ready datasets and analysis

This directory contains **copies** of all production-ready files for analysis and publication. Original files remain in their working directories to preserve code functionality.

---

## 📊 Core Databases

### ttj_shipments.csv
**150,592 shipment records (1874-1899) with geographic coordinates**

- Origin port coordinates: 84.7% coverage (125,908 ships)
- Destination port coordinates: 93.1% coverage (140,223 ships)
- Complete routes: 77.8% (117,133 ships with both origin and destination)
- Deduplicated, normalized, UK/Ireland destinations only
- Ready for GIS mapping and spatial analysis

**Columns:** record_id, ship_name, origin_port, destination_port, origin_latitude, origin_longitude, destination_latitude, destination_longitude, arrival_year, merchant, and more

### ttj_cargo_details_cleaned.csv
**306,202 cargo records with ship and port information**

- Ship names included
- Origin and destination ports included
- Coordinates included (80.7% complete routes)
- Commodities normalized (pit props consolidated: 19,714 records)
- Parsing errors removed (1,338 cleaned)
- Ready for commodity flow analysis

**Columns:** cargo_id, ship_name, origin_port, origin_latitude, origin_longitude, destination_port, destination_latitude, destination_longitude, commodity, quantity, unit, merchant

---

## 📈 Annual Statistics (By Year)

### export_ports_per_year.csv
**3,857 port-year combinations (1874-1899)**

Export ports with annual shipment counts and coordinates. Shows temporal patterns in timber exports to Britain.

**Columns:** year, port_name, latitude, longitude, ship_count

**Example use:** Map changing export patterns over time, identify port growth/decline

**Note:** Case-insensitive consolidation applied (e.g., "Riga" + "RIGA" in same year → consolidated)

### import_ports_per_year.csv
**1,169 port-year combinations (1874-1899)**

British import ports with annual shipment counts and coordinates. All UK/Ireland destinations.

**Columns:** year, port_name, latitude, longitude, ship_count

**Example use:** Map British port specialization, regional timber demand

**Note:** Case-insensitive consolidation applied (e.g., 1885: "LONDON" 2,021 + "London" 33 → 2,054)

### export_import_pairs_per_year.csv
**24,486 route-year combinations (1874-1899)**

Origin-destination pairs with annual counts and coordinates for both endpoints. Shows trade route evolution.

**Columns:** year, origin_port, origin_latitude, origin_longitude, destination_port, destination_latitude, destination_longitude, ship_count

**Example use:** Flow maps, trade route analysis, network visualization

**Note:** Case-insensitive consolidation applied to both origin and destination ports

---

## 📊 Aggregate Statistics (Entire Period)

### export_ports_total.csv
**357 export ports (1874-1899 combined)**

Total shipment counts per export port across entire period with coordinates.

**Columns:** port_name, latitude, longitude, ship_count

**Top exports:** Riga (7,828), Gothenburg (6,505), New York (4,816)

**Note:** Case-insensitive consolidation applied (e.g., "LONDON" + "London" → "LONDON")

### import_ports_total.csv
**134 British import ports (1874-1899 combined)**

Total shipment counts per import port across entire period with coordinates.

**Columns:** port_name, latitude, longitude, ship_count

**Top imports:** LONDON (19,050), LIVERPOOL (18,546), GRIMSBY (17,465)

**Note:** Case-insensitive consolidation applied to fix OCR case variants

### export_import_pairs_total.csv
**6,811 unique trade routes (1874-1899 combined)**

Total shipment counts per origin-destination pair across entire period with coordinates for both endpoints.

**Columns:** origin_port, origin_latitude, origin_longitude, destination_port, destination_latitude, destination_longitude, ship_count

**Top routes:** New York → LIVERPOOL (1,713), Bordeaux → BRISTOL (1,663), Gothenburg → GRIMSBY (1,210)

**Note:** Case-insensitive consolidation applied to both origin and destination ports

---

## 🏛️ London Case Study

### london_commodities.csv
**39,831 cargo records for London imports**

Complete London commodity data with origins and coordinates.

**Key finding:** London shifted from importing raw timber (deals, lathwood) to finished products (doors, mouldings, flooring) between 1874-1899, reflecting industrialization of timber processing moving to source countries.

### london_commodity_trends.csv
**Annual trends for top 10 commodities imported to London**

Time series showing commodity changes by year.

**Key trends:**
- Doors: +2,073% growth (11 → 239 records)
- Mouldings: +688% growth (25 → 197 records)
- Floorings: +864% growth (11 → 106 records)
- Deals: -32% decline (1,543 → 1,052 records)

### london_commodity_origins.csv
**Commodity-origin pairs for London**

Shows which commodities came from which ports.

**Key patterns:**
- Staves: 19% from New York (American oak)
- Doors: Concentrated from Gothenburg (Swedish manufacturing)
- Deals: Diversified sources (Quebec, Cronstadt, Riga, Gothenburg)

### london_commodity_growth.csv
**Growth analysis (1874-1880 vs 1893-1899)**

Compares early vs late period to quantify structural shifts.

**Major finding:** Finished products increased from 1.2% to 7.9% of imports, while raw materials declined from 66.5% to 63.1%, indicating deindustrialization of London timber processing.

---

## 🗺️ Reference Data

### Ports_Master.geojson
**558 ports with coordinates**

Complete port database with coordinates, alternative names, and metadata.

- Original ports: 480
- Added: 78 new ports (71 origin, 7 destination)
- Format: GeoJSON for direct GIS import
- Includes: Norwegian fjord ports, Baltic ports, North American timber ports

### manual_port_matches.json
**109 port normalization rules**

Handles spelling variants and historical names:
- Canadian variants: "St. John, N.B." → "St. John"
- European variants: "Trondhjem" → "Trondheim (Drontheim)"
- Props consolidation: "props", "pit props", "pit-props" → "pit props"

---

## 📋 Quick Start Guide

### For Mapping in GIS Software

1. **Load ports:** Import `Ports_Master.geojson`
2. **Load shipments:** Import `ttj_shipments.csv`
3. **Join:** Link shipments to ports via origin_port/destination_port names
4. **Visualize:** Create flow maps using origin/destination coordinates

### For Commodity Analysis

1. **Load:** `ttj_cargo_details_cleaned.csv`
2. **Filter:** By commodity, origin_port, destination_port, or year
3. **Aggregate:** Group by commodity + origin to see supply patterns
4. **Visualize:** Create supply chain maps using coordinates

### For Temporal Analysis

1. **Load:** `export_import_pairs_per_year.csv`
2. **Filter:** By year range
3. **Animate:** Create time-series maps showing route evolution
4. **Analyze:** Compare early (1874-1880) vs late (1893-1899) periods

---

## 🔍 Key Research Findings

### Geographic Patterns
- **Top Export Ports:** Riga (7,828 ships), Gothenburg (6,505), New York (4,816)
- **Top Import Ports:** LONDON (19,050 ships), LIVERPOOL (18,546), GRIMSBY (17,465)
- **Busiest Route:** New York → LIVERPOOL (1,713 ships)
- **Case consolidation:** OCR case variants merged (e.g., "LONDON" + "London" → 19,050 total)

### Commodity Patterns
- **Top Commodities:** Deals (36,784), Battens (20,763), Pit props (19,714)
- **Pit props:** Critical for coal mining (3rd largest import)
- **Geographic specialization:** Staves from America, doors from Sweden, deals diversified

### Temporal Trends
- **Industrialization shift:** Raw timber imports declining, finished products rising
- **London case:** 6.5x increase in finished product imports (1.2% → 7.9%)
- **Processing moved:** From British ports to source countries (cheaper labor, mechanization)

---

## 📊 Data Quality Metrics

### Coverage
- **Shipments:** 150,592 total (deduplicated from 152,984 parser output)
- **Origin coordinates:** 84.7% (125,908 ships)
- **Destination coordinates:** 93.1% (140,223 ships)
- **Complete routes:** 77.8% (117,133 ships)

### Cargo
- **Total records:** 306,202
- **Valid commodities:** 304,864 (99.6%)
- **With coordinates:** 247,156 (80.7%)
- **Quality improvements:** 21,052 records normalized/cleaned (6.9%)

### Time Period
- **Years covered:** 1874-1899 (26 years)
- **Missing years:** None (continuous coverage)
- **Records per year:** Average ~5,792

---

## 💾 File Sizes

- ttj_shipments.csv: ~29 MB
- ttj_cargo_details_cleaned.csv: ~42 MB
- Annual statistics: ~2 MB total
- London analysis: ~5 MB total
- Ports_Master.geojson: ~180 KB

**Total deliverables:** ~78 MB

---

## 📝 Citation

When using this data, please cite:

> Timber Trades Journal Forest of Numbers Project (1874-1899). Geocoded shipment and cargo database. Dataset compiled from historical Timber Trades Journal using OCR and geocoding. November 2025.

---

## ❓ Questions & Support

**Which file should I use?**
- Mapping shipments: `ttj_shipments.csv`
- Commodity analysis: `ttj_cargo_details_cleaned.csv`
- Annual trends: `export_import_pairs_per_year.csv`
- London case study: `london_commodities.csv`

**File format issues?**
- All CSV files use UTF-8 encoding
- Coordinate system: WGS84 (standard lat/lon)
- Date format: Year as integer (arrival_year column)

**Need original working files?**
- See `DATABASE_VERSIONS.md` in project root
- Original locations preserved for code rerunning

---

**Last Updated:** November 12, 2025  
**Version:** 1.0  
**Contact:** See project documentation
