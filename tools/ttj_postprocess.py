#!/usr/bin/env python3
import sys, json, difflib, re
from typing import List, Dict, Optional

# Mirror core vocab/ports from parser (lightweight, no imports)
PRODUCT_TYPES = [
    "boards","battens","deals","deal ends","timber","oak timber","fir timber","scantlings",
    "sleepers","sleeper blocks","staves","pipe staves","headings","props","pit props","mining timber",
    "spars","masts","lathwood","laths","flooring boards","mouldings","architraves","skirtings","joinery",
    "wainscot logs","wood pulp","mahogany","cedar","satinwood","logwood","fustic","lignum vitae","ebony",
    "barwood","boxwood","canes","palings","teak","hardwood","letterwood","planks","redwood","firewood","other"
]

LIKELY_PORTS = [
    "Gothenburg","New York","Kronstadt","Quebec","Danzig","Klaipeda","Riga","Christiania",
    "Fredrikstad","Belize","Sundsvall","Drammen","St. Petersburg","Montreal","Stockholm",
    "Konigsberg","Soderhamn","Gavle","Pensacola","Kotka","Jamaica","Arkhangelsk","Miramichi",
    "Abo","Oulu","Halifax","Catania","Chicoutimi","Boston","Uddevalla","Svartvik","Porsgrund",
    "Halden","Liepāja","Mobile","Odessa","Harnosand","Hamburg","Ljusne","Bremen","Helsingfors",
    "Sandarne","Ventspils","Santa Ana","Trois-Rivières","Metis","Wyborg","Rangoon","Hudikswall",
    "Finnklippan","Larvik","Bjorneborg","Baltimore","Puerto Cortez","Le Havre","Bathurst","Kragero",
    "Amsterdam","Venice","St. John","Soroka","Stettin","Skien","Trieste","Sault au Cochon","Skonvik",
    "Bangkok","Pitea","Nyhamn","Campbellton","Moulmein","Nassau"
]

PORT_VARIANTS = {
    "Wyburg": "Wyborg","Dantzic": "Danzig","Memel": "Klaipeda","Windau": "Ventspils","Hambro": "Hamburg",
    "Cronstadt": "Kronstadt","Fredrickstad": "Fredrikstad","Fredrikshald": "Halden","Falmouth Jamaica": "Jamaica",
    "Abo": "Abo","Helsingfors": "Helsingfors","Konigsberg": "Konigsberg","Christiansand": "Kristiansand",
    "Archangel": "Arkhangelsk","Harnosand": "Harnosand","Hudikswall": "Hudikswall","Krageroe": "Kragero","Liepaja": "Liepāja"
}

# Optional arrival place lexicon (helps LLM-free fixes)
ARRIVAL_PLACES = [
    "Surrey Commercial Docks","West India Docks","East India Docks","Millwall Docks","Victoria Docks",
    "London Docks","Greenland Dock","St. Katharine Docks","St. Katherine Docks","Deptford","Rotherhithe",
    "Limehouse","Bow Creek","Poplar","Blackwall","Millwall","Surrey Docks","Commercial Docks"
]

def clean(s: Optional[str]) -> str:
    return (s or "").strip()

def normalize_port(raw: str) -> Optional[str]:
    r = clean(raw)
    if not r:
        return None
    # Direct variant mapping
    for k, v in PORT_VARIANTS.items():
        if r.lower() == k.lower():
            return v
    # Exact match first
    for p in LIKELY_PORTS:
        if r.lower() == p.lower():
            return p
    # Fuzzy, but only if very close
    match = difflib.get_close_matches(r, LIKELY_PORTS + list(PORT_VARIANTS.keys()), n=1, cutoff=0.88)
    if match:
        m = match[0]
        # If matched a variant key, return its canonical value
        if m in PORT_VARIANTS:
            return PORT_VARIANTS[m]
        return m
    return None

def detect_products(text: str) -> List[str]:
    t = (text or "").lower()
    t = t.replace("deaks", "deals")
    # simple whole-word presence
    found = []
    for v in sorted(PRODUCT_TYPES, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(v) + r"(?![a-z])", t):
            if v not in found:
                found.append(v)
    # redwood deals and ends heuristic
    if "redwood" in t and "deal" in t and ("deal ends" in t or re.search(r"\bends\b", t)) and "deal ends" not in found:
        found.append("deal ends")
    return found

def normalize_arrival_place(raw: str) -> Optional[str]:
    r = clean(raw)
    if not r:
        return None
    # Prefer original text, but if it's clearly close to a known place, keep original and do nothing.
    # We do not change arrival_place_raw; this function is here if later you want to auto-fix names.
    return None

def postprocess(records: List[Dict]) -> List[Dict]:
    out = []
    for r in records:
        r = dict(r)  # shallow copy
        # Try to improve port normalization
        if not r.get("departure_port_std") and r.get("departure_port_raw"):
            cand = normalize_port(r["departure_port_raw"])
            if cand:
                r["departure_port_std"] = cand
                # If unknown_port was set, drop it
                r["warnings"] = [w for w in r.get("warnings", []) if w != "unknown_port"]
        # Try to improve product typing
        if r.get("product_list_raw"):
            types = detect_products(r["product_list_raw"])
            if types and types != r.get("product_type_list"):
                r["product_type_list"] = types
                r["warnings"] = [w for w in r.get("warnings", []) if w != "ambiguous_products"]
        out.append(r)
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Conservative TTJ post-processor (port/product normalization)")
    ap.add_argument("input", help="Input JSON array from ttj_parse.py")
    ap.add_argument("-o", "--output", help="Output JSON (post-processed)", default="-")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        records = json.load(f)

    updated = postprocess(records)
    payload = json.dumps(updated, ensure_ascii=False)
    if args.output == "-":
        sys.stdout.write(payload)
    else:
        with open(args.output, "w", encoding="utf-8") as w:
            w.write(payload)

if __name__ == "__main__":
    main()

