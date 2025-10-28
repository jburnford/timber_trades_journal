#!/usr/bin/env python3
"""
Evaluate TTJContextParser lift on a set of issues by counting parsed records
per issue and comparing with current CSV ships_parsed counts.

Usage:
  python tools/evaluate_parser_lift.py --issues-csv parser_miss_priority_list.csv \
      --ocr-dir ocr_results/gemini_full --out lift_report.csv
"""

import argparse
import csv
import glob
from pathlib import Path
from typing import Dict

from ttj_parser_v3 import TTJContextParser


def count_parsed_for_issue(ocr_dir: Path, ymd: str) -> int:
    parser = TTJContextParser()
    total = 0
    for fp in sorted(glob.glob(str(ocr_dir / f"{ymd}*.txt"))):
        total += len(parser.parse_file(Path(fp)))
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--issues-csv', required=True, help='CSV with issue_date column (YYYY-MM-DD)')
    ap.add_argument('--ocr-dir', default='ocr_results/gemini_full', help='Directory of OCR .txt files')
    ap.add_argument('--out', default='lift_report.csv', help='Output CSV path')
    args = ap.parse_args()

    # Load issue_date -> csv_ships
    issues: Dict[str, int] = {}
    with open(args.issues_csv, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            date = row['issue_date']
            # Only include rows with OCR candidates > CSV if present in CSV
            if 'csv_ships' in row and 'ocr_candidates' in row:
                issues[date] = int(row['csv_ships'] or 0)
            else:
                # fallback to ttj_issue_inventory schema
                issues[date] = int(row.get('ships_parsed') or 0)

    # Compute new parsed counts
    out_rows = []
    for date, csv_ships in issues.items():
        ymd = date.replace('-', '')
        parsed = count_parsed_for_issue(Path(args.ocr_dir), ymd)
        out_rows.append({
            'issue_date': date,
            'csv_ships': csv_ships,
            'parser_v3_count': parsed,
            'delta_v3_minus_csv': parsed - csv_ships,
        })

    # Write output
    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['issue_date','csv_ships','parser_v3_count','delta_v3_minus_csv'])
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {args.out} with {len(out_rows)} rows")


if __name__ == '__main__':
    main()

