# TTJ Parsing Feedback: Commodities, Merchants, and Quick Port Wins

This document summarizes targeted improvements based on a review of the repository’s markdown documentation, parsing code, and recent outputs. The focus is on commodity parsing and merchant parsing, with a few easy port normalization wins.

## Scope Reviewed
- Docs: `README.md`, `DATA_PROCESSING_PIPELINE.md`, `METHODOLOGY_NOTES.md`, `PIPELINE_IMPROVEMENTS_SUMMARY.md`, `PLAN_TO_95_PERCENT.md`, `ANALYTICAL_DATASETS_GUIDE.md`.
- Code: `tools/ttj_parser_v3.py`, `tools/cargo_parser.py`, `tools/generate_two_csv_output.py`, `tools/normalize_data.py`, `tools/normalize_with_authority_review.py`, `tools/apply_normalization.py`, and `reference_data/*`.
- Results: `final_output/deduped/*.csv`, `final_output/authority_normalized/*`, with special attention to `commodity_fixes_recommended.csv`.

## High‑Impact Findings
- Units misclassified as commodities: Words like “loads”, “tons”, “pieces”, “cords”, “fathoms”, “standards”, “squares”, “bundles” (and abbr. `bdls`, `pcs`, `bgs`, `doz`, `lds`, `fms`) sometimes end up in the commodity field. Evidence: `final_output/authority_normalized/commodity_fixes_recommended.csv` shows 1,800+ “unit → ERROR” rows.
- Segmentation issues: Items separated by em‑dashes (—) are not currently split, causing cross‑contamination of merchants and duplicated commodities inside a single parsed segment.
- Merchant attribution: Merchant is extracted per segment; in mixed segments, item‑level merchants are not consistently captured and fall back to the shipment‑level or to placeholders like “Order”.
- Commodity normalization already runs (commodity‑normalized payload exists), but upstream parsing can be tightened to reduce downstream cleanup work.
- Ports: Strong overall; a few quick wins remain (case‑insensitive exacts, province suffixes, and ensuring the St. lookahead fix is applied where needed).

## Commodity Parsing: Recommended Changes
1. Split on em‑dashes as well as semicolons
   - In `tools/cargo_parser.py` `parse_cargo_string`, split segments via: `segments = re.split(r'[;—]+', cargo)`.

2. Treat unit words (not just dotted abbreviations) as units
   - Load known units from `reference_data/units.json` and extend the unit pattern to accept both dotted and undotted forms:
     - Examples to support as units: `loads?`, `tons?`, `pieces?`, `bundles?`, `cords?`, `fathoms?`, `standards?`, `squares?`, `bags?`, `bales?`, plus dotted abbr like `pcs.?`, `bdls.?`, `bgs.?`, `doz.?`, `lds.?`, `fms.?`.
   - Regex sketch (single pass): `(?P<qty>\d[\d,]*)\s+(?P<unit>(?:bdls?\.?|pcs?\.?|bgs?\.?|doz\.?|lds\.?|fms\.?|tons?|loads?|pieces?|bundles?|cords?|fathoms?|standards?|squares?))\b\s+(?P<comm>[a-z][a-z\s&\-]{2,})`.

3. Use one unified per‑item regex that also captures merchant
   - Prefer a single `finditer` pattern per segment capturing: quantity, optional unit (abbr or word), commodity, optional trailing merchant, stopping at `;`/`—`/end.
   - This fixes leakage from “segment‑level merchant” and handles mixed segments like `“… 9,173 staves, Oppenheimer & Co. — 22,313 pcs. redwood … Order”`.

4. Guardrails against false commodities and fragments
   - Drop matches where `commodity` is too short (<3) unless whitelisted (`oak`, `fir`).
   - Denylist the fragment tokens seen in `commodity_fixes_recommended.csv` (e.g., `w`, `p`, `sq`, `ft`, `pp`, etc.).
   - As a second line of defense, if the captured “commodity” is exactly a known unit word, discard the item.

5. Mixed‑commodity phrasing
   - Keep canonical combined commodities when ambiguous (“logs mahogany and cedar”) rather than trying to split the quantity; your `reference_data/commodities.json` already models such forms.

6. Spelled‑out small numbers (nice‑to‑have)
   - Optionally map very common cases (e.g., “two logs …”, “one log …”) to numeric quantities to reduce misses; low priority.

## Merchant Parsing: Recommended Changes
1. Item‑level merchants
   - With the unified per‑item regex, capture merchant per item (comma‑separated, stop at segment end). Fall back to shipment‑level merchant only if item‑level is missing.

2. Merchant normalization rules
   - In `tools/normalize_data.py normalize_merchant`:
     - Strip house styles/polite forms: `Messrs`, `Mr.`, `Mrs.`, suffixes like `Ltd`, `Limited`, `Co.`, convert `&` → `and`.
     - Compact whitespace, strip trailing punctuation, and Title‑Case cautiously (preserve initials and apostrophes).
     - Treat placeholders/synonyms as empty: `Order`, `To order`, `In bond`, `Nil`, `Ditto`.

3. (Optional) Merchant authority pass
   - Generate `final_output/authority_normalized/merchants_for_review.csv` listing top‑frequency variants and suggested merges (after case/punctuation folding: `&`→`and`, `Co.`→`Company`, etc.).
   - Auto‑normalize exact/obvious variants; flag 0.85–0.92 fuzzy range for review (mirrors port workflow but simpler thresholds).

## Where to Change
- `tools/cargo_parser.py`
  - Split on `;` and `—`.
  - Replace the two‑pattern parsing with a single `finditer` regex that supports item‑level merchant capture and word/abbrev units.
  - Load known units from `reference_data/units.json` and build a case‑insensitive unit alternation.
  - Apply fragment and unit‑as‑commodity filters.

- `tools/generate_two_csv_output.py`
  - No structural change; it already prefers item‑level merchant when present.

- `tools/normalize_data.py`
  - Extend `normalize_merchant` rules as above.
  - (Optional) Add a merchant review export akin to the port review flow.

## Quick Port Wins
- Case‑insensitive exacts first:
  - Ensure both origin and destination paths in `normalize_with_authority_review.PortNormalizer.normalize_port` do a fast case‑insensitive exact match before variant/fuzzy.

- Province suffix stripping (origins):
  - Pre‑strip `, N.B.`, `, N.S.`, `, P.E.I.` prior to variant/fuzzy matching.

- “St.” abbreviation fix proliferation:
  - You applied a lookahead fix in `ttj_parser_v3.py` for `early_at_pattern`; if residual “St” truncations arise from other formats (standard/condensed), replicate the lookahead approach there too.

## Validation After Changes
- Commodities
  - Re‑generate `commodity_fixes_recommended.csv` and confirm steep drop in “unit → ERROR” rows and fragment rows.
  - Spot‑check segments with em‑dashes for proper item separation and merchant capture.

- Quantities
  - Re‑run `tools/analyze_quantity_accuracy.py` on the 1883 validation sample; ensure no regression (some gains likely due to better segmentation and unit recognition).

- Ports
  - Verify reduction of any residual “St” truncations and apply suffix stripping impact on Canadian origins.

## Offer to Implement
I can implement the cargo parser improvements (em‑dash splitting, unified regex with unit vocabulary, fragment filters) and extend merchant normalization rules, then re‑run a targeted subset to compare before/after metrics. If you want, I can also scaffold a minimal merchant review file (`merchants_for_review.csv`) mirroring your port review process. Let me know and I’ll proceed.

