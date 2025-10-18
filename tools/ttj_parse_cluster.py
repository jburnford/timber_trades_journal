#!/usr/bin/env python3
import sys
import re
import json
from typing import List, Dict, Optional, Tuple

# Minimal reuse of normalization logic (mirrors tools/ttj_parse.py)
PRODUCT_TYPES = [
    "boards", "battens", "deals", "deal ends", "timber", "oak timber", "fir timber",
    "scantlings", "sleepers", "sleeper blocks", "staves", "pipe staves", "headings",
    "props", "pit props", "mining timber", "spars", "masts", "lathwood", "laths",
    "flooring boards", "mouldings", "architraves", "skirtings", "joinery", "wainscot logs",
    "wood pulp", "mahogany", "cedar", "satinwood", "logwood", "fustic", "lignum vitae",
    "ebony", "barwood", "boxwood", "canes", "palings", "teak", "hardwood", "letterwood",
    "planks", "redwood", "firewood", "other"
]

LIKELY_PORTS = set()
PORT_VARIANTS: Dict[str, str] = {}

MONTHS = (
    "January","February","March","April","May","June","July","August","September","October","November","December"
)

DATE_HDR = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+\d{1,2}(?:st|nd|rd|th)\.")

def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace('\u00a0',' ')).strip()

def normalize_punct(s: str) -> str:
    # Unify dashes and ensure a period before dash after port
    t = s
    # Normalize various dash chars to em dash
    t = t.replace('\u2014', '—').replace('\u2013', '—').replace('--', '—')
    # Ensure there is a space around em dash
    t = re.sub(r"\s*—\s*", " — ", t)
    # Make sure port dot + dash is ". —"
    t = re.sub(r"(\s*@\s*[^.\n—]+)\.(\s*—\s*)", lambda m: m.group(1)+". — ", t)
    return t

def ports_normalize(raw: str) -> Optional[str]:
    if not raw:
        return None
    raw_clean = normalize_whitespace(raw)
    for k, v in PORT_VARIANTS.items():
        if raw_clean.lower() == k.lower():
            return v
    for p in LIKELY_PORTS:
        if raw_clean.lower() == p.lower():
            return p
    return None

def detect_product_types(product_text: str, product_aliases: Dict[str,str]) -> List[str]:
    ptxt = (product_text or "").lower()
    for a,b in (product_aliases or {}).items():
        ptxt = re.sub(rf"(?i)(?<![a-z]){re.escape(a)}(?![a-z])", b, ptxt)
    # Aliases baked-in
    ptxt = ptxt.replace("deaks","deals")
    types: List[str] = []
    if "redwood" in ptxt and ("deal ends" in ptxt or re.search(r"\bends\b", ptxt)) and "deal" in ptxt:
        for t in ["deals","deal ends","redwood"]:
            if t not in types:
                types.append(t)
    for v in sorted(PRODUCT_TYPES, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(v) + r"(?![a-z])", ptxt):
            if v not in types:
                types.append(v)
    if re.search(r"\bends\b", ptxt) and re.search(r"\bdeal(s)?\b", ptxt) and "deal ends" not in types:
        types.append("deal ends")
    return types

def load_configs(ports_path: Optional[str], products_path: Optional[str]) -> Dict[str,Dict]:
    prod_aliases: Dict[str,str] = {}
    if ports_path:
        try:
            with open(ports_path, 'r', encoding='utf-8') as f:
                pdata = json.load(f)
            for p in pdata.get('likely_ports',[]) or []:
                LIKELY_PORTS.add(p)
            for k,v in (pdata.get('variants',{}) or {}).items():
                PORT_VARIANTS[k]=v
        except Exception as e:
            print(f"Warning: failed to load ports config: {e}", file=sys.stderr)
    if products_path:
        try:
            with open(products_path, 'r', encoding='utf-8') as f:
                pdata = json.load(f)
            # For accuracy, do NOT auto-extend PRODUCT_TYPES with uncontrolled tokens here.
            # Rely on aliases only (add_types is ignored in this cluster parser).
            prod_aliases = pdata.get('aliases',{}) or {}
        except Exception as e:
            print(f"Warning: failed to load products config: {e}", file=sys.stderr)
    # Default, conservative aliases to fix common OCR artifacts
    default_aliases = {"fireswood": "firewood", "1-sleepers": "sleepers"}
    merged = {**default_aliases, **(prod_aliases or {})}
    return {"product_aliases": merged}

def find_dates(text: str) -> List[Tuple[int,str]]:
    dates = []
    for m in DATE_HDR.finditer(text):
        dates.append((m.start(), normalize_whitespace(m.group(0).rstrip('.'))))
    return dates

# Entry must start at line start OR right after a period+space to avoid swallowing previous sentences
ENTRY_RX = re.compile(
    r"(?:^|[.]\s+)"  # boundary at start or after a period
    r"(?P<ship>[A-Z][^@.\n—]{0,80}?)\s*"  # ship name chunk
    r"(?:\((?P<steam>s)\))?\s*@\s*"      # optional (s) and @
    r"(?P<port>[^.\n—]+)\.\s*—\s*"        # port up to a period, then em dash
    r"(?P<body>.*?)"                         # body (lazy)
    r"(?=(?:[.]\s+(?:[A-Z][^@.\n—]{0,80}?\s*(?:\((?:s)\))?\s*@\s*|" + "|".join(MONTHS) + r"\s+\d{1,2}(?:st|nd|rd|th)\.))|$)",
    re.U | re.S
)

def nearest_date_label(pos: int, date_positions: List[Tuple[int,str]]) -> Optional[str]:
    label = None
    for p, d in date_positions:
        if p <= pos:
            label = d
        else:
            break
    return label

def split_merchants(body: str) -> Tuple[str, Optional[str]]:
    txt = normalize_whitespace(body)
    # Heuristic: if last comma-separated segment looks like merchant or 'Order'
    parts = [p.strip() for p in txt.split(',') if p.strip()]
    if not parts:
        return txt, None
    last = parts[-1]
    merchant_name_like = bool(re.fullmatch(r"[A-Z][A-Za-z.'’&-]+(?:\s+[A-Z][A-Za-z.'’&-]+){0,4}", last))
    if last.lower() == 'order' or merchant_name_like or re.search(r"\b(&|co\.?|son|sons|bros?\.?|brothers|ltd\.?|limited)\b", last, re.I):
        prod = ', '.join(parts[:-1]) if len(parts) > 1 else ''
        return prod, last
    return txt, None

# Remove quantities and obvious numeric tokens to stabilize product typing
QUANTITY_TOKEN = re.compile(r"(?i)\b(\d+[\d,\.]*|n\.?s\.?|pcs?\.?|loads?\.?|bdft|ft\.?|in\.?|cwt\.?|tons?\.?|bales?\.?|pkgs?\.?|cases?\.?|boxes?\.?|stds?\.?|yds?\.?|doz\.?|bags?\.?|sacks?\.?)\b")

def strip_quantities(text: str) -> str:
    t = QUANTITY_TOKEN.sub(" ", text)
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",\s*,", ", ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" ;,:")

def parse_text(raw_text: str, product_aliases: Dict[str,str]) -> List[Dict]:
    text = normalize_whitespace(normalize_punct(raw_text))
    # Drop obvious headers
    text = re.sub(r"^Imports of Timber, &c\.\s*", "", text, flags=re.I)
    text = re.sub(r"^London\s*", "", text, flags=re.I)
    # Remove (From ... ) parenthetical header
    text = re.sub(r"\(From [^)]+\)\s*", "", text, flags=re.I)

    date_positions = find_dates(text)
    entries: List[Dict] = []

    for m in ENTRY_RX.finditer(text):
        ship = normalize_whitespace(m.group('ship'))
        is_steamer = bool(m.group('steam'))
        port = normalize_whitespace(m.group('port'))
        body = normalize_whitespace(m.group('body'))
        start = m.start()
        date_label = nearest_date_label(start, date_positions)
        products_raw, merchants = split_merchants(body)
        # build normalized products
        products_for_typing = strip_quantities(products_raw)
        product_types = detect_product_types(products_for_typing, product_aliases)
        port_std = ports_normalize(port)
        warnings: List[str] = []
        if not port_std:
            warnings.append('unknown_port')
        if not product_types:
            warnings.append('ambiguous_products')
        # entry_raw should be the matched segment without leading boundary period
        entry_raw = normalize_whitespace(m.group(0).lstrip('. ').strip())
        entries.append({
            "date_label": date_label,
            "entry_raw": entry_raw,
            "ship_name_raw": ship,
            "is_steamer": is_steamer,
            "departure_port_raw": port,
            "commodities_text_raw": products_raw,
            "merchants_raw": merchants,
            "departure_port_std": port_std,
            "product_type_list": product_types,
            "warnings": warnings,
        })
    return entries

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Parse cluster OCR text (with @ Port — products.) into raw+normalized JSON")
    ap.add_argument('input', nargs='?', help='Input file (raw text or JSON with key "text"). Defaults to stdin')
    ap.add_argument('--ports', help='Custom ports JSON: {likely_ports, variants}')
    ap.add_argument('--products', help='Custom products JSON: {add_types, aliases}')
    args = ap.parse_args()

    configs = load_configs(args.ports, args.products)
    text = ''
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()
    raw = raw.strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and 'text' in obj:
            text = str(obj['text'])
        else:
            text = raw
    except Exception:
        text = raw

    data = parse_text(text, configs.get('product_aliases', {}))
    json.dump(data, sys.stdout, ensure_ascii=False)

if __name__ == '__main__':
    main()
