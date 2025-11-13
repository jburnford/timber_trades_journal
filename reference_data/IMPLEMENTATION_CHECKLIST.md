# Port Geocoding Implementation Checklist

**Quick reference for implementing all port improvements**

---

## Pre-Implementation

- [ ] Backup `Ports_Master.geojson`
- [ ] Backup `final_output/ttj_shipments.csv`
- [ ] Verify all files present (see checklist in Implementation Guide)

---

## Implementation Steps

### 1. Add New Ports to GeoJSON

- [ ] Add 71 origin ports from `new_ports_truly_unique.csv`
- [ ] Add 7 destination ports from `british_new_ports_to_add.csv`
- [ ] Save as `Ports_Master_Updated.geojson`
- [ ] Verify total ports: 466 + 78 = 544 ports

### 2. Create Normalization Script

- [ ] Create `tools/normalize_all_ports.py` (see Implementation Guide)
- [ ] Load origin rules from `manual_port_matches.json` (58 rules)
- [ ] Load destination rules from `british_port_manual_mappings_final.json` (101 rules)
- [ ] Load fuzzy rules from `british_ports_case_fuzzy_matches.json` (22 rules)

### 3. Run Normalization

- [ ] Run `python3 tools/normalize_all_ports.py`
- [ ] Verify output: `parsed_output/ttj_shipments_normalized.csv`
- [ ] Check normalization counts:
  - Origin: ~26,527 ships (17.7%)
  - Destination: ~30,148 ships (20%)

### 4. Re-run Geocoding

- [ ] Use normalized CSV as input
- [ ] Use updated GeoJSON
- [ ] Generate `final_output/ttj_shipments_geocoded.csv`

### 5. Measure Results

Expected coverage:
- [ ] Origin ports: 83-85% (was 77.6%)
- [ ] Destination ports: 94.3% (was 0%)

### 6. Finalize

- [ ] Review results for quality
- [ ] Replace original files with updated versions
- [ ] Commit changes to git with descriptive message

---

## Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Origin coverage | 77.6% | ~84% | +6.4% |
| Destination coverage | 0% | 94.3% | +94.3% |
| Total ports in GeoJSON | 466 | 544 | +78 |
| Normalization rules | 0 | 159 | +159 |

---

## Quick Commands

```bash
# Navigate to project
cd "/home/jic823/TTJ Forest of Numbers"

# Backup
cp Ports_Master.geojson Ports_Master_backup.geojson
cp final_output/ttj_shipments.csv final_output/ttj_shipments_backup.csv

# Add ports (use script in Implementation Guide)
python3 reference_data/add_new_ports.py

# Normalize
python3 tools/normalize_all_ports.py

# Geocode (your existing process)
# ... your geocoding script ...

# Measure
python3 reference_data/measure_coverage.py
```

---

## Files Modified

- `Ports_Master.geojson` → +78 new ports
- `final_output/ttj_shipments.csv` → normalized and geocoded
- `tools/normalize_all_ports.py` → new script

## Files to Commit

- `reference_data/new_ports_truly_unique.csv`
- `reference_data/british_new_ports_to_add.csv`
- `reference_data/manual_port_matches.json`
- `reference_data/british_port_manual_mappings_final.json`
- `reference_data/british_ports_case_fuzzy_matches.json`
- `reference_data/*.md` (all documentation)
- `tools/normalize_all_ports.py`
- `Ports_Master.geojson` (updated)
- `final_output/ttj_shipments.csv` (updated)

---

**Last Updated:** 2025-11-12
**Status:** Ready for implementation
