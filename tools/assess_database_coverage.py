#!/usr/bin/env python3
"""
Phase 1.3: Assess current database coverage for affected dates.
Query ttj_shipments_final.csv to establish baseline ship counts before recovery.
"""
import json
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Increase CSV field size limit for large fields
csv.field_size_limit(10 * 1024 * 1024)  # 10MB

def normalize_date(year, month, day):
    """Convert year, month, day to YYYYMMDD format."""
    if not all([year, month, day]):
        return None
    try:
        return f"{int(year):04d}{int(month):02d}{int(day):02d}"
    except (ValueError, TypeError):
        return None

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    manifest_path = base_dir / "analysis" / "polaris_ocr_mapping.json"
    database_path = base_dir / "parsed_output" / "ttj_shipments_final.csv"
    output_dir = base_dir / "analysis"

    print("=" * 80)
    print("PHASE 1.3: ASSESS CURRENT DATABASE COVERAGE")
    print("=" * 80)
    print()

    # Load manifest from Phase 1.2
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    affected_dates = set(manifest['dates'].keys())
    print(f"Affected dates from manifest: {len(affected_dates)}")
    print()

    # Query database for ship counts per date
    print(f"Querying database: {database_path}")
    print("This may take a moment...")
    print()

    ships_by_date = defaultdict(list)
    total_ships = 0

    with open(database_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_ships += 1

            # Get date components
            year = row.get('arrival_year')
            month = row.get('arrival_month')
            day = row.get('arrival_day')

            # Normalize to YYYYMMDD
            norm_date = normalize_date(year, month, day)

            if norm_date and norm_date in affected_dates:
                ships_by_date[norm_date].append({
                    'ship_name': row.get('ship_name', ''),
                    'origin_port': row.get('origin_port', ''),
                    'destination_port': row.get('destination_port', ''),
                    'source_file': row.get('source_file', '')
                })

    print(f"Total ships in database: {total_ships:,}")
    print(f"Ships on affected dates: {sum(len(ships) for ships in ships_by_date.values()):,}")
    print()

    # Generate coverage report
    print("=" * 80)
    print("DATABASE COVERAGE BY AFFECTED DATE")
    print("=" * 80)
    print()

    coverage_data = {}
    dates_with_no_ships = 0
    dates_with_low_ships = 0  # < 10 ships

    for norm_date in sorted(affected_dates):
        date_info = manifest['dates'][norm_date]
        date_str = date_info['date_str']
        ship_count = len(ships_by_date.get(norm_date, []))

        gemini_count = date_info['counts']['gemini']
        polaris_count = date_info['counts']['polaris']

        # Flag suspicious dates
        status = "NORMAL"
        if ship_count == 0:
            status = "MISSING"
            dates_with_no_ships += 1
        elif ship_count < 10:
            status = "LOW"
            dates_with_low_ships += 1

        print(f"{date_str:25} | Ships: {ship_count:4} | Gemini: {gemini_count} | Polaris: {polaris_count} | [{status}]")

        coverage_data[norm_date] = {
            'date_str': date_str,
            'ship_count': ship_count,
            'gemini_files': gemini_count,
            'polaris_files': polaris_count,
            'status': status,
            'ships': ships_by_date.get(norm_date, [])
        }

    print()
    print(f"Dates with NO ships in database: {dates_with_no_ships}")
    print(f"Dates with LOW ships (< 10): {dates_with_low_ships}")
    print()

    # Save coverage report
    output_manifest = {
        'generated': datetime.now().isoformat(),
        'database_path': str(database_path),
        'total_ships_in_database': total_ships,
        'affected_dates_count': len(affected_dates),
        'ships_on_affected_dates': sum(len(ships) for ships in ships_by_date.values()),
        'dates_with_no_ships': dates_with_no_ships,
        'dates_with_low_ships': dates_with_low_ships,
        'coverage_by_date': coverage_data
    }

    output_path = output_dir / "database_coverage_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_manifest, f, indent=2, ensure_ascii=False)

    print(f"Coverage report saved to: {output_path}")
    print()

    # Analysis summary
    print("=" * 80)
    print("RECOVERY POTENTIAL ANALYSIS")
    print("=" * 80)
    print()

    total_affected_ships = sum(len(ships) for ships in ships_by_date.values())
    avg_ships_per_date = total_affected_ships / len(affected_dates) if affected_dates else 0

    print(f"Current ships on affected dates: {total_affected_ships:,}")
    print(f"Average ships per date: {avg_ships_per_date:.1f}")
    print()
    print(f"Polaris recovery files: {manifest['total_polaris_files']}")
    print(f"Dates missing from database: {dates_with_no_ships}")
    print()

    # Estimate recovery potential
    if dates_with_no_ships > 0:
        print(f"RECOVERY POTENTIAL:")
        print(f"  Missing dates suggest incomplete OCR parsing")
        print(f"  Polaris recovery should restore these dates")

    if dates_with_low_ships > 0:
        print(f"  {dates_with_low_ships} dates with low counts may have partial data")
        print(f"  Polaris + Gemini combination should improve coverage")

    print()
    print("=" * 80)
    print("PHASE 1.3 COMPLETE")
    print("=" * 80)
    print()
    print("Ready for Phase 2: Create hybrid OCR directory")

    return output_manifest

if __name__ == '__main__':
    manifest = main()
