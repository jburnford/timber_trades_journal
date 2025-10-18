#!/usr/bin/env python3
import sys, json, os, re
from collections import Counter, defaultdict
from typing import List, Dict, Tuple

import pandas as pd


CONTROLLED_PRODUCTS = set([
    "boards","battens","deals","deal ends","timber","oak timber","fir timber","scantlings",
    "sleepers","sleeper blocks","staves","pipe staves","headings","props","pit props","mining timber",
    "spars","masts","lathwood","laths","flooring boards","mouldings","architraves","skirtings","joinery",
    "wainscot logs","wood pulp","mahogany","cedar","satinwood","logwood","fustic","lignum vitae","ebony",
    "barwood","boxwood","canes","palings","teak","hardwood","letterwood","planks","redwood","firewood","other"
])


def pick_sheets(xl: pd.ExcelFile) -> List[str]:
    names = xl.sheet_names
    target = []
    for n in names:
        low = n.lower().strip()
        if ("london" in low or low.startswith("lon")) and any(y in low for y in ["1883","1889","1897"]):
            target.append(n)
    if target:
        return target
    # Fallback: exact names hinted by collaborator
    fallbacks = ["London imports 1883","Lon imp. 1889","Lon imp.1897"]
    for f in fallbacks:
        if f in names and f not in target:
            target.append(f)
    return target or names


def find_column(df: pd.DataFrame, keywords: List[str]) -> List[str]:
    cols = []
    for c in df.columns:
        cl = str(c).lower()
        if any(k in cl for k in keywords):
            cols.append(c)
    return cols


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0"," ")).strip()


def tokenize_products(text: str) -> List[str]:
    # Split on common separators: comma, semicolon, slash, ' and ', ' & '
    t = text
    # Normalize plus signs, ampersands
    t = t.replace("/", ",").replace(";", ",").replace("&", " and ")
    # Replace ' et ' (French) with ' and '
    t = re.sub(r"\bet\b", " and ", t, flags=re.I)
    # Split at commas first
    parts = [p.strip() for p in t.split(",") if p.strip()]
    tokens: List[str] = []
    for p in parts:
        subs = re.split(r"\band\b", p, flags=re.I)
        for s in subs:
            s = normalize_space(s)
            if s:
                tokens.append(s)
    return tokens


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Extract ports/products from Excel workbooks and build parser dictionaries")
    ap.add_argument("xlsx", nargs="+", help="Path(s) to Excel workbook(s)")
    ap.add_argument("--outdir", default="tools/out", help="Output directory for JSONs")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    port_counter: Counter = Counter()
    product_phrase_counter: Counter = Counter()
    product_token_counter: Counter = Counter()

    for path in args.xlsx:
        if not os.path.isfile(path):
            print(f"Skip missing workbook: {path}", file=sys.stderr)
            continue
        xl = pd.ExcelFile(path)
        sheets = pick_sheets(xl)
        # Always also consider any sheet with port/product-like columns
        consider = list(dict.fromkeys(sheets + xl.sheet_names))
        print(f"Scanning {path}: sheets={consider}")

        for sn in consider:
            try:
                df = xl.parse(sn)
            except Exception:
                continue
            # Identify columns (French/English):
            port_cols = find_column(df, ["port of origin","port of entry","port", "départ", "depart", "city"]) or []
            prod_cols = find_column(df, ["produit", "product", "commodity", "species"]) or []

            # Ports
            for c in port_cols:
                for v in df[c].dropna().astype(str):
                    v = normalize_space(v)
                    if v:
                        port_counter[v] += 1

            # Products
            for c in prod_cols:
                for v in df[c].dropna().astype(str):
                    v = normalize_space(v)
                    if not v:
                        continue
                    product_phrase_counter[v] += 1
                    for tok in tokenize_products(v):
                        product_token_counter[tok] += 1

    # No-op: normalized ports are now included via generic port_cols above
    normalized_ports = []

    # Build likely_ports as sorted unique (case-insensitive unique by canonical form)
    def ci_unique(counter: Counter) -> List[str]:
        seen = set()
        out = []
        for s, _ in counter.most_common():
            k = s.lower()
            if k not in seen:
                seen.add(k)
                out.append(s)
        return out

    likely_ports = ci_unique(port_counter)
    # Add normalized ports with priority (preserve order by appending new ones)
    seen = set(x.lower() for x in likely_ports)
    for p in normalized_ports:
        pl = p.lower()
        if pl and pl not in seen:
            likely_ports.append(p)
            seen.add(pl)

    # Derive add_types: tokens that look like product names not in controlled list
    def normalize_token(t: str) -> str:
        return t.lower()

    add_types = []
    for tok, _ in product_token_counter.most_common():
        tt = normalize_token(tok)
        if tt not in CONTROLLED_PRODUCTS and tt not in add_types:
            add_types.append(tt)

    # Write detailed outputs
    ports_out = {
        "likely_ports": likely_ports,
        "frequency": dict(port_counter.most_common())
    }
    products_out = {
        "raw_phrases": dict(product_phrase_counter.most_common()),
        "unique_tokens": dict(product_token_counter.most_common())
    }

    with open(os.path.join(args.outdir, "ports_from_excel.json"), "w", encoding="utf-8") as w:
        json.dump(ports_out, w, ensure_ascii=False, indent=2)
    with open(os.path.join(args.outdir, "products_from_excel.json"), "w", encoding="utf-8") as w:
        json.dump(products_out, w, ensure_ascii=False, indent=2)

    # Configs consumable by ttj_parse.py
    with open(os.path.join("tools", "config", "custom_ports.from_excel.json"), "w", encoding="utf-8") as w:
        json.dump({"likely_ports": likely_ports, "variants": {}}, w, ensure_ascii=False, indent=2)
    with open(os.path.join("tools", "config", "custom_products.from_excel.json"), "w", encoding="utf-8") as w:
        json.dump({"add_types": add_types, "aliases": {}}, w, ensure_ascii=False, indent=2)

    # Coverage summary
    controlled_hits = sum(c for p,c in product_token_counter.items() if p.lower() in CONTROLLED_PRODUCTS)
    total_tokens = sum(product_token_counter.values()) or 1
    coverage = controlled_hits / total_tokens * 100.0
    print(f"Products tokens covered by controlled list: {coverage:.1f}% ({controlled_hits}/{total_tokens})")
    print(f"Wrote: {args.outdir}/ports_from_excel.json, {args.outdir}/products_from_excel.json")
    print(f"Configs: tools/config/custom_ports.from_excel.json, tools/config/custom_products.from_excel.json")

if __name__ == "__main__":
    main()
