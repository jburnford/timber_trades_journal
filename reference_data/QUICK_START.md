# Quick Start Guide: Port Geocoding Improvements

## TL;DR - What to Do

### 1. Use This File for New Ports
```
reference_data/new_ports_truly_unique.csv
```
**71 unique ports** ready to add to your GeoJSON. Already verified for duplicates.

### 2. Run Port Normalization
```bash
cd "/home/jic823/TTJ Forest of Numbers"
python3 tools/normalize_port_names.py
```
This fixes **26,527 ships** with alternative port spellings.

### 3. Expected Results
- **Current coverage:** 77.6%
- **After improvements:** ~83-85%
- **Total ships improved:** ~40,100

---

## File Locations

### ✅ Use These
| File | Purpose | Ships Fixed |
|------|---------|-------------|
| `reference_data/new_ports_truly_unique.csv` | 71 new ports to add | 13,573 |
| `reference_data/manual_port_matches.json` | Spelling normalization | 26,527 |
| `tools/normalize_port_names.py` | Apply normalization | - |

### 📚 Reference Only
- `reference_data/GEOCODING_IMPROVEMENT_README.md` - Full documentation
- `reference_data/geocoding_fixes_needed.md` - Tracking document
- Other `new_ports_*.csv` files - Working versions (don't use)

---

## Top 10 New Ports

1. **Klaipeda** (Lithuania) - 2,701 ships
2. **Bayonne** (France) - 1,082 ships
3. **Ventspils** (Latvia) - 716 ships
4. **Brevig** (Norway) - 700 ships
5. **Liepāja** (Latvia) - 687 ships
6. **Mobile** (USA) - 566 ships
7. **Lorient** (France) - 529 ships
8. **Norfolk** (USA) - 325 ships
9. **Newport News** (USA) - 299 ships
10. **Moss** (Norway) - 275 ships

---

## Known Fixed Issues

- ✅ Chatham (N.B.) - Removed from new ports, maps to existing "Chatham, N. B."
- ✅ Porsgrunn - Removed from new ports, maps to existing "Porsgrund" (4.29 km away)
- ✅ Trangsund - Fixed to Russian Vysotsk (not Swedish Stockholm)
- ✅ Egersund - Coordinates corrected to 58.4497, 6.0087
- ✅ Brevig - Coordinates corrected to 59.05544, 9.69593
- ✅ Moss - Coordinates corrected to 59.459167, 10.700833
- ✅ 27 internal duplicates - Removed
- ✅ 60 GeoJSON duplicates - Removed via coordinate matching

---

## Questions?

See `reference_data/GEOCODING_IMPROVEMENT_README.md` for full details.
