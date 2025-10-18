#!/usr/bin/env python3
import sys, json
from typing import List, Dict

"""
Read a JSON array (from ttj_parse.py) and emit two files:
- stdout: JSON array containing only records that likely need attention (warnings present)
- optionally, with -t/--text, writes a plain-text queue to help LLM/humans correct minimal context.
"""

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Filter TTJ parsed JSON to items needing correction.")
    ap.add_argument("input", help="Input JSON array from ttj_parse.py")
    ap.add_argument("-o", "--output", help="Output JSON (subset)", default="-")
    ap.add_argument("-t", "--text", help="Write a plain-text correction queue to this path")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data: List[Dict] = json.load(f)

    needs = [r for r in data if r.get("warnings")]

    # Write JSON subset
    payload = json.dumps(needs, ensure_ascii=False)
    if args.output == "-":
        sys.stdout.write(payload)
    else:
        with open(args.output, "w", encoding="utf-8") as w:
            w.write(payload)

    # Optional plain-text queue (token-light) for LLM/human review
    if args.text:
        with open(args.text, "w", encoding="utf-8") as w:
            for i, r in enumerate(needs, 1):
                line = (
                    f"#{i}\n"
                    f"arrival_place_raw: {r.get('arrival_place_raw')}\n"
                    f"departure_port_raw: {r.get('departure_port_raw')}\n"
                    f"product_list_raw: {r.get('product_list_raw')}\n"
                    f"notes: {r.get('notes')}\n"
                    f"warnings: {','.join(r.get('warnings', []))}\n"
                )
                w.write(line + "\n")

if __name__ == "__main__":
    main()

