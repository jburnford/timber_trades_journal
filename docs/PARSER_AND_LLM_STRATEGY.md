# Parser Improvements and LLM Fallback Strategy

Goal: Maximize recall on odd-year issues where we have images, with reliable structured output. Keep regex/parser as the primary path; add an LLM-based extractor as a targeted fallback for hard cases.

## What We Changed (Parser v3)
- Added robust dash handling so dash-delimited records match regardless of separator:
  - Supports em dash `—`, en dash `–`, and hyphen `-` with flexible spacing.
- Result: Significant lift on late-1890s issues where OCR uses Unicode dashes.

### Quick Lift Check (sample)
- 1899-09-09: 0 → 154 parsed records (7 OCR files)
- 1897-06-26: 31 → 62 parsed records (3 OCR files)
- 1899-08-12: 42 → 69 parsed records (8 OCR files)
- 1891-07-25: 29 → 35 parsed records (2 OCR files)
- 1891-08-08: 17 → 18 parsed records (1 OCR file)

## Next Parser Targets
- Header flexibility: accept headers without trailing period (e.g., `LONDON` as well as `LONDON.`).
- Continuations: tolerate mid-sentence carry-overs and wrapped lines; merge lines where a record splits at column breaks.
- Date-prefixed variants: ensure `Sept. 1`/`Sep. 1`/`September 1` all drive context.
- Multi-page context: ensure context persists across files, but reset when a new issue begins.
- Noise hardening: broaden ignore list around ad blocks; ignore small caps “SPECIALITY”, “TRADE MARK”, etc., with OCR typos.

## Evaluation Harness (recommendation)
- Build an issue-level evaluation over the odd-year summer priority set:
  - Metric: delta between OCR candidate lines and parsed record counts (lower is better), plus manual spot-precision on ~50 records.
  - Batch: run top 30 priority issues before/after parser tweaks; track lift and error types.

## LLM Fallback Design
- Trigger conditions (examples):
  - Zero ships parsed but >50 OCR candidate lines.
  - Parsed < 40% of odd-year monthly median AND OCR has >30 candidate lines.
- Chunking:
  - Group by issue and destination section (e.g., `LONDON.`, `LIVERPOOL.`) to keep context.
  - 1–3 OCR pages per request; include preceding header/date lines.
- Prompting:
  - Provide 2–3 few-shot examples mapping raw OCR lines to JSON.
  - Ask for strict JSON array with fields: `ship_name`, `origin_port`, `destination_port`, `cargo`, `merchant`, `arrival_day`, `arrival_month`, `publication_date`.
  - Instructions: ignore ads/headers; skip totals; normalize common tokens (bdls., fthms., lds.) minimally, don’t hallucinate numerics.
- Post-processing:
  - Validate against canonical port list; fuzzy-match merchants; drop obviously malformed rows.
  - Deduplicate across pages; merge continuations by ship/date.
- Cost/throughput:
  - Target only hard issues (<= 50 issues initially); estimate < $5 given short chunks.
  - Keep logs of prompts+responses for reproducibility.

## Decision Criteria
- Keep regex-first if:
  - Recall ≥ 85% on priority set and precision reasonable (manual spot-check OK).
- Use LLM fallback if:
  - Any issue remains at 0 with many OCR candidates, or
  - Regex ceiling appears due to format diversity (e.g., inconsistent punctuation, multi-column wrap) where adding more rules causes regressions.

## Immediate Next Steps
- Re-run parser v3 over top priority issues; confirm lift; catalog any remaining misses with examples.
- Implement the header-without-period tweak and continuation joiner.
- Prepare an LLM prompt + schema with 5 representative examples; dry-run on 2 top issues and compare.

