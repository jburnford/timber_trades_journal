#!/usr/bin/env python3
"""
Generate human review CSV from normalization analysis.
Creates spreadsheet for reviewing uncertain port mappings.
"""

import json
import csv
from pathlib import Path


def generate_review_csv(analysis_file: Path, output_csv: Path):
    """Generate CSV file for human review of port normalizations."""

    print("=" * 80)
    print("GENERATING HUMAN REVIEW CSV")
    print("=" * 80)

    # Load analysis
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    # Prepare review records
    review_records = []

    # Process origin ports
    print("\nProcessing origin ports for review...")
    for port_info in analysis['origin']['for_review']:
        web_query = f"{port_info['original']} timber port 1880s"

        record = {
            'port_type': 'origin',
            'original_port': port_info['original'],
            'ship_count': port_info['ship_count'],
            'best_match_canonical': port_info['normalized'] or '',
            'similarity_score': f"{port_info['confidence']:.3f}" if port_info['confidence'] > 0 else '',
            'normalization_tier': port_info['tier'],
            'year_range': port_info['year_range'],
            'web_search_query': web_query,
            'action': '',  # For human to fill in
            'map_to_port': '',  # For human to fill in
            'notes': ''  # For human notes
        }
        review_records.append(record)

    # Process destination ports
    print("Processing destination ports for review...")
    for port_info in analysis['destination']['for_review']:
        web_query = f"{port_info['original']} British port timber 1880s"

        record = {
            'port_type': 'destination',
            'original_port': port_info['original'],
            'ship_count': port_info['ship_count'],
            'best_match_canonical': port_info['normalized'] or '',
            'similarity_score': f"{port_info['confidence']:.3f}" if port_info['confidence'] > 0 else '',
            'normalization_tier': port_info['tier'],
            'year_range': port_info['year_range'],
            'web_search_query': web_query,
            'action': '',
            'map_to_port': '',
            'notes': ''
        }
        review_records.append(record)

    # Sort by ship count (descending) within each type
    origin_records = [r for r in review_records if r['port_type'] == 'origin']
    dest_records = [r for r in review_records if r['port_type'] == 'destination']

    origin_records.sort(key=lambda x: x['ship_count'], reverse=True)
    dest_records.sort(key=lambda x: x['ship_count'], reverse=True)

    review_records = origin_records + dest_records

    # Write CSV
    fieldnames = [
        'port_type',
        'original_port',
        'ship_count',
        'best_match_canonical',
        'similarity_score',
        'normalization_tier',
        'year_range',
        'action',
        'map_to_port',
        'notes',
        'web_search_query'
    ]

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # Add instruction row
        writer.writerow({
            'port_type': '=== INSTRUCTIONS ===',
            'original_port': 'Fill in ACTION column',
            'ship_count': '',
            'best_match_canonical': 'Options:',
            'similarity_score': 'ACCEPT = accept as-is',
            'normalization_tier': 'MAP = map to canonical',
            'year_range': 'ERROR = mark as error',
            'action': '<-- Fill this',
            'map_to_port': '<-- If MAP, specify port here',
            'notes': 'Optional notes',
            'web_search_query': 'Copy this to browser'
        })

        writer.writerows(review_records)

    print(f"\n✓ Generated review CSV: {output_csv}")
    print(f"  Total ports for review: {len(review_records)}")
    print(f"    Origin ports: {len(origin_records)}")
    print(f"    Destination ports: {len(dest_records)}")

    # Generate summary by frequency
    print("\n" + "=" * 80)
    print("REVIEW WORKLOAD SUMMARY")
    print("=" * 80)

    high_freq = [r for r in review_records if r['ship_count'] >= 100]
    med_freq = [r for r in review_records if 20 <= r['ship_count'] < 100]
    low_freq = [r for r in review_records if r['ship_count'] < 20]

    print(f"\nHigh-frequency (≥100 ships): {len(high_freq)} ports ⭐ PRIORITY")
    print(f"Medium-frequency (20-99 ships): {len(med_freq)} ports")
    print(f"Low-frequency (<20 ships): {len(low_freq)} ports")

    print(f"\nTop 20 ports by frequency:")
    for i, record in enumerate(review_records[:20], 1):
        match_str = f" → {record['best_match_canonical']} ({record['similarity_score']})" if record['best_match_canonical'] else ""
        print(f"  {i:2}. [{record['port_type']:11}] {record['original_port']:30} {record['ship_count']:4} ships{match_str}")

    # Generate action guide
    action_guide_file = output_csv.parent / "REVIEW_INSTRUCTIONS.md"
    with open(action_guide_file, 'w', encoding='utf-8') as f:
        f.write("""# Port Normalization Review Instructions

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
""")

    print(f"\n✓ Generated instructions: {action_guide_file}")

    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print(f"1. Open: {output_csv}")
    print("2. Read: {action_guide_file}")
    print("3. Review ports (start with high-frequency)")
    print("4. Fill in 'action' and 'map_to_port' columns")
    print("5. Save the CSV")
    print("6. Run: python3 apply_normalization.py")
    print("=" * 80)


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    output_dir = base_dir / "final_output" / "authority_normalized"

    analysis_file = output_dir / "normalization_analysis.json"
    output_csv = output_dir / "ports_for_review.csv"

    if not analysis_file.exists():
        print(f"Error: Analysis file not found: {analysis_file}")
        print("Run normalize_with_authority_review.py first")
        return

    generate_review_csv(analysis_file, output_csv)


if __name__ == '__main__':
    main()
