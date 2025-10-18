# Port Normalization Review Instructions

## Your Task

Review `ports_for_review.csv` and fill in the **action** and **map_to_port** columns.

## Actions

### ACCEPT
- Port is legitimate (found via web search)
- Not in canonical list because it's from a year not transcribed (1874-1882, 1884-1888, 1890-1896, 1898-1899)
- Example: "Oresund" (1,409 ships) → ACCEPT (Øresund Sound is real location)

### MAP
- Port is OCR variant of a canonical port
- Use the best_match_canonical if confidence is good (>0.85)
- Or specify your own mapping if you find the correct port
- Example: "Dram" → MAP → "Drammen"

### ERROR
- Port is OCR garbage, journal artifact, or wharf name
- Very low frequency (<10 ships) and no web search results
- Example: "PITWOOD" → ERROR (this is a commodity, not a port)

## Workflow

1. **Start with high-frequency ports (≥100 ships)**
   - These affect the most records
   - Usually legitimate ports, just need verification

2. **Web search strategy:**
   - Copy the `web_search_query` column value
   - Paste into browser
   - Look for: Wikipedia, historical records, port authority sites

3. **For each port, decide:**
   - **ACCEPT**: Found evidence it's a real timber port
   - **MAP**: It's a variant of a known port
   - **ERROR**: No evidence, likely OCR error

4. **Fill in columns:**
   - `action`: ACCEPT / MAP / ERROR
   - `map_to_port`: Only if action=MAP, specify the canonical port name
   - `notes`: Optional (e.g., "Øresund Sound between Denmark/Sweden")

## Examples

```
original_port     | action | map_to_port | notes
----------------- | ------ | ----------- | -----
Oresund           | ACCEPT |             | Øresund Sound (Denmark/Sweden strait)
Memel             | MAP    | Klaipeda    | German name for Klaipeda (Lithuania)
Dram              | MAP    | Drammen     | Abbreviation
LONDON            | MAP    | London      | Capitalization issue
PITWOOD           | ERROR  |             | Commodity, not a port
```

## Priority Order

1. High-frequency (≥100 ships) - ~15-20 ports
2. Medium-frequency (20-99) - ~100 ports
3. Low-frequency (<20) - ~100+ ports (consider batch ERROR if no match)

## Notes

- Origin ports: 481 canonical from 1883, 1889, 1897
- Destination ports: 139 canonical from 1888 only
- Legitimate ports from other years ARE expected
- When in doubt, web search is your friend!

## After Review

Save the CSV and run: `python3 apply_normalization.py`
This will apply your decisions to the full dataset.
