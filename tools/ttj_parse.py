#!/usr/bin/env python3
import sys
import re
import json
from typing import List, Dict, Optional


# Controlled product vocabulary (singular, lowercase)
PRODUCT_TYPES = [
    "boards", "battens", "deals", "deal ends", "timber", "oak timber", "fir timber",
    "scantlings", "sleepers", "sleeper blocks", "staves", "pipe staves", "headings",
    "props", "pit props", "mining timber", "spars", "masts", "lathwood", "laths",
    "flooring boards", "mouldings", "architraves", "skirtings", "joinery", "wainscot logs",
    "wood pulp", "mahogany", "cedar", "satinwood", "logwood", "fustic", "lignum vitae",
    "ebony", "barwood", "boxwood", "canes", "palings", "teak", "hardwood", "letterwood",
    "planks", "redwood", "firewood", "other"
]

# Likely ports list (case-insensitive matching)
LIKELY_PORTS = set([
    "Gothenburg","New York","Kronstadt","Quebec","Danzig","Klaipeda","Riga","Christiania",
    "Fredrikstad","Belize","Sundsvall","Drammen","St. Petersburg","Montreal","Stockholm",
    "Konigsberg","Soderhamn","Gavle","Pensacola","Kotka","Jamaica","Arkhangelsk","Miramichi",
    "Abo","Oulu","Halifax","Catania","Chicoutimi","Boston","Uddevalla","Svartvik","Porsgrund",
    "Halden","Liepāja","Mobile","Odessa","Harnosand","Hamburg","Ljusne","Bremen","Helsingfors",
    "Sandarne","Ventspils","Santa Ana","Trois-Rivières","Metis","Wyborg","Rangoon",
    "Hudikswall","Finnklippan","Larvik","Bjorneborg","Baltimore","Puerto Cortez","Le Havre",
    "Bathurst","Kragero","Amsterdam","Venice","St. John","Soroka","Stettin","Skien","Trieste",
    "Sault au Cochon","Skonvik","Bangkok","Pitea","Nyhamn","Campbellton","Moulmein","Nassau"
])

# Variants mapping applied before matching against likely ports
PORT_VARIANTS = {
    # Combined from user prompts
    "Wyburg": "Wyborg",
    "Dantzic": "Danzig",
    "Memel": "Klaipeda",
    "Windau": "Ventspils",
    "Hambro": "Hamburg",
    "Cronstadt": "Kronstadt",
    "Fredrickstad": "Fredrikstad",
    "Fredrikshald": "Halden",
    "Falmouth Jamaica": "Jamaica",
    # From first prompt’s variants
    "Abo": "Abo",
    "Helsingfors": "Helsingfors",
    "Konigsberg": "Konigsberg",
    "Christiansand": "Kristiansand",
    "Archangel": "Arkhangelsk",
    "Harnosand": "Harnosand",
    "Hudikswall": "Hudikswall",
    "Krageroe": "Kragero",
    "Liepaja": "Liepāja",
}

# Arrival place keyword hints
PLACE_HINTS = re.compile(r"\\b(Dock|Docks|Wharf|Wharves|Buoy|Buoys|Quay|Quays|Stairs|Hole|Basin|Pier|Millwall|Surrey|Commercial|Victoria|West India|East India)\\b", re.I)

# Common header/sum lines to skip
HEADER_STARTS = (
    "imports of timber", "london.", "may ", "june ", "july ", "august ", "september ", "october ",
    "november ", "december ", "january ", "february ", "march ", "april ",
)
SUMMARY_PAT = re.compile(r"^(in all|sundry imports)\b", re.I)

# Normalize dash variants to an em-dash-ish token
DASH_SPLIT = re.compile(r"\s*(?:—|–|—|\s-\s|\s—\s|\s–\s|\s--\s|\s—|-{2,}|—)\s*")

# YYYY-MM-DD at start
DATE_ISO_PAT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\b")

# Remove quantities like numbers, decimals, comma-grouped, n.s., ft, in, pcs, loads, etc., conservatively
QUANTITY_TOKEN = re.compile(r"(?i)\b(\d+[\d,\.]*|n\.?s\.?|pcs?\.?|loads?\.?|bdft|ft\.?|in\.?|cwt\.?|tons?\.?|bales?\.?|pkgs?\.?|cases?\.?|boxes?\.?)\b")

# Detect parenthetical notes, but drop trivial markers like (s)
PARENS_PAT = re.compile(r"\(([^)]*)\)")


def looks_like_header(line: str) -> bool:
    s = line.strip().lower().rstrip('.:;')
    if not s:
        return True
    if SUMMARY_PAT.match(s):
        return True
    for h in HEADER_STARTS:
        if s.startswith(h):
            return True
    # Very short all-caps line
    if len(s) <= 4 and s.isupper():
        return True
    return False


def normalize_whitespace(s: str) -> str:
    s = s.replace('\u00a0', ' ')
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def extract_notes_and_strip(s: str) -> (str, Optional[str]):
    notes = []
    def keep_note(text: str) -> bool:
        t = text.strip()
        # Drop trivial steamer markers like (s) or single letters
        if re.fullmatch(r"[sS]", t):
            return False
        if len(t) <= 1:
            return False
        return True

    def repl(m):
        inner = m.group(1)
        if keep_note(inner):
            notes.append(inner.strip())
            return ""
        return ""

    s2 = PARENS_PAT.sub(repl, s)
    note_text = "; ".join(notes) if notes else None
    return normalize_whitespace(s2), note_text


def ports_normalize(raw: str) -> Optional[str]:
    if not raw:
        return None
    raw_clean = normalize_whitespace(raw)
    # Apply variant map (case-insensitive)
    for k, v in PORT_VARIANTS.items():
        if raw_clean.lower() == k.lower():
            return v
    # Exact likely ports match (case-insensitive)
    for p in LIKELY_PORTS:
        if raw_clean.lower() == p.lower():
            return p
    return None


def strip_quantities(text: str) -> str:
    # Remove obvious quantity tokens while preserving commodity phrasing
    # Also remove stray commas left behind at ends
    t = QUANTITY_TOKEN.sub(" ", text)
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",\s*,", ", ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip(" ;,:")


def detect_product_types(product_text: str) -> List[str]:
    ptxt = product_text.lower()
    types: List[str] = []

    # Aliases
    ptxt = ptxt.replace("deaks", "deals")

    # Special phrase: redwood deals and ends -> deals + deal ends + redwood (keep redwood separately)
    if "redwood" in ptxt and ("deal ends" in ptxt or re.search(r"\bends\b", ptxt)) and "deal" in ptxt:
        for t in ["deals", "deal ends", "redwood"]:
            if t not in types:
                types.append(t)

    # Straight keyword matches (prefer longer phrases first)
    vocab = sorted(PRODUCT_TYPES, key=len, reverse=True)
    for v in vocab:
        # match as whole word sequence
        if re.search(r"(?<![a-z])" + re.escape(v) + r"(?![a-z])", ptxt):
            if v not in types:
                types.append(v)

    # Mild heuristics: if we saw 'ends' but not 'deal ends' and also saw 'deal'/'deals', add 'deal ends'
    if re.search(r"\bends\b", ptxt) and (re.search(r"\bdeal(s)?\b", ptxt)) and "deal ends" not in types:
        types.append("deal ends")

    return types


def parse_line(line: str) -> Optional[Dict]:
    original = line.rstrip("\n")
    s = normalize_whitespace(original)
    if not s:
        return None
    low = s.lower()
    if looks_like_header(low):
        return None

    # Extract and remove notes
    s, notes = extract_notes_and_strip(s)

    # Extract leading ISO date if present
    date_iso = None
    m = DATE_ISO_PAT.match(s)
    if m:
        date_iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        s = s[m.end():].lstrip(" -—:")

    # Split by big dashes into up to 3 parts: arrival_place — departure_port — products/merchants
    parts = DASH_SPLIT.split(s)
    parts = [normalize_whitespace(p) for p in parts if normalize_whitespace(p)]
    if len(parts) < 2:
        # Not a recognizable arrival line
        return None

    arrival_place_raw = parts[0]
    departure_port_raw = parts[1] if len(parts) >= 2 else ""
    tail = parts[2] if len(parts) >= 3 else ""

    # If first chunk looks like a city-only header and second chunk has place hints, swap
    if not PLACE_HINTS.search(arrival_place_raw) and PLACE_HINTS.search(departure_port_raw):
        arrival_place_raw, departure_port_raw = departure_port_raw, arrival_place_raw

    # Products and merchants from tail
    product_list_raw = tail
    merchants_raw = None

    # If there is a semicolon and a "for" or "to" that likely introduces merchants, split
    if ";" in tail:
        before, after = tail.split(";", 1)
        if re.search(r"\b(for|to)\b", after, re.I):
            product_list_raw = before.strip()
            merchants_raw = normalize_whitespace(after)

    product_list_raw = strip_quantities(product_list_raw)

    departure_port_std = ports_normalize(departure_port_raw)

    product_types = detect_product_types(product_list_raw)

    warnings: List[str] = []
    if departure_port_raw and not departure_port_std:
        warnings.append("unknown_port")
    if not product_types:
        warnings.append("ambiguous_products")

    obj = {
        "date_iso": date_iso if date_iso else None,
        "arrival_place_raw": arrival_place_raw if arrival_place_raw else None,
        "departure_port_raw": departure_port_raw if departure_port_raw else None,
        "departure_port_std": departure_port_std,
        "product_type_list": product_types,
        "product_list_raw": product_list_raw if product_list_raw else "",
        "merchants_raw": merchants_raw if merchants_raw else None,
        "notes": notes if notes else None,
        "warnings": warnings,
    }

    return obj


def parse_lines(lines: List[str]) -> List[Dict]:
    out: List[Dict] = []
    for line in lines:
        rec = parse_line(line)
        if rec is not None:
            out.append(rec)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Parse TTJ OCR lines into structured JSON array.")
    ap.add_argument("input", nargs="?", help="Input text file (one line per sentence). Defaults to stdin.")
    ap.add_argument("--ports", help="Optional JSON of custom port dictionaries: { 'likely_ports':[], 'variants':{} }")
    ap.add_argument("--products", help="Optional JSON of product aliases: { 'aliases': { 'deaks':'deals', ... }, 'add_types': [] }")
    args = ap.parse_args()

    # Optional: load custom dictionaries
    if args.ports:
        try:
            with open(args.ports, "r", encoding="utf-8") as f:
                pdata = json.load(f)
            # extend likely ports
            for p in pdata.get("likely_ports", []) or []:
                LIKELY_PORTS.add(p)
            # extend variants
            for k, v in (pdata.get("variants", {}) or {}).items():
                PORT_VARIANTS[k] = v
        except Exception as e:
            print(f"Warning: failed to load ports dict: {e}", file=sys.stderr)

    product_aliases = {}
    if args.products:
        try:
            with open(args.products, "r", encoding="utf-8") as f:
                pdata = json.load(f)
            # extend product types list
            for t in pdata.get("add_types", []) or []:
                if t not in PRODUCT_TYPES:
                    PRODUCT_TYPES.append(t)
            product_aliases = pdata.get("aliases", {}) or {}
        except Exception as e:
            print(f"Warning: failed to load products dict: {e}", file=sys.stderr)

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.read().splitlines()

    # If we have product aliases, patch detect_product_types via closure
    if product_aliases:
        base_detect = detect_product_types
        def detect_with_aliases(text: str):
            t = text
            for a, b in product_aliases.items():
                t = re.sub(rf"(?i)(?<![a-z]){re.escape(a)}(?![a-z])", b, t)
            return base_detect(t)
        globals()['detect_product_types'] = detect_with_aliases  # type: ignore

    data = parse_lines(lines)
    json.dump(data, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
