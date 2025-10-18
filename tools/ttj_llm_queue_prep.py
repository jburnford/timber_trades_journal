#!/usr/bin/env python3
import sys, json
from typing import List, Dict

"""
Group triage text or JSON into small batches for LLM correction to minimize tokens.

Usage:
  python3 tools/ttj_llm_queue_prep.py triage.json --size 10 --prefix batch
  -> creates batch_001.txt, batch_002.txt, ... each containing up to N lines

Input can be either:
  - a JSON array (from ttj_triage.py), or
  - a plain text file where blocks are separated by blank lines (as written by ttj_triage.py --text)
"""

def from_json(path: str) -> List[str]:
    with open(path, 'r', encoding='utf-8') as f:
        arr: List[Dict] = json.load(f)
    # Compose a minimal one-line prompt per record
    lines = []
    for r in arr:
        ap = r.get('arrival_place_raw') or ''
        dp = r.get('departure_port_raw') or ''
        pr = r.get('product_list_raw') or ''
        nt = f" ({r['notes']})" if r.get('notes') else ''
        # Use em dashes, keep merchants if present
        m = r.get('merchants_raw')
        tail = pr + (f"; {m}" if m else '')
        line = f"{ap} — {dp} — {tail}{nt}".strip()
        lines.append(line)
    return lines

def from_text(path: str) -> List[str]:
    # Expect blocks as produced by ttj_triage.py --text; recompose to one line
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()
    blocks = [b.strip() for b in txt.split('\n\n') if b.strip()]
    lines = []
    for b in blocks:
        ap = dp = pr = nt = m = ''
        for ln in b.splitlines():
            if ln.lower().startswith('arrival_place_raw:'):
                ap = ln.split(':',1)[1].strip()
            elif ln.lower().startswith('departure_port_raw:'):
                dp = ln.split(':',1)[1].strip()
            elif ln.lower().startswith('product_list_raw:'):
                pr = ln.split(':',1)[1].strip()
            elif ln.lower().startswith('notes:'):
                nt = ln.split(':',1)[1].strip()
            elif ln.lower().startswith('merchants_raw:'):
                m = ln.split(':',1)[1].strip()
        tail = pr + (f"; {m}" if m else '')
        note = f" ({nt})" if nt and nt.lower() != 'none' else ''
        line = f"{ap} — {dp} — {tail}{note}".strip()
        lines.append(line)
    return lines

def write_batches(lines: List[str], size: int, prefix: str):
    batch = 1
    for i in range(0, len(lines), size):
        chunk = lines[i:i+size]
        path = f"{prefix}_{batch:03d}.txt"
        with open(path, 'w', encoding='utf-8') as w:
            for ln in chunk:
                w.write(ln + "\n")
        batch += 1

def main():
    import argparse, os
    ap = argparse.ArgumentParser(description='Create small LLM correction batches from triage outputs')
    ap.add_argument('input', help='triage JSON array or triage text file')
    ap.add_argument('--size', type=int, default=10, help='lines per batch file')
    ap.add_argument('--prefix', default='batch', help='output file prefix')
    args = ap.parse_args()

    path = args.input
    if path.lower().endswith('.json'):
        lines = from_json(path)
    else:
        lines = from_text(path)

    if not lines:
        print('No lines found to batch.', file=sys.stderr)
        return 0

    write_batches(lines, args.size, args.prefix)
    print(f'Wrote {((len(lines)-1)//args.size)+1} batch file(s).', file=sys.stderr)
    return 0

if __name__ == '__main__':
    sys.exit(main())

