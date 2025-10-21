# Methodology Report: Building a Historical Timber Trade Dataset with LLM OCR and Python

## Executive Summary
- Problem: Manual transcription of the Timber Trades Journal (TTJ) was slow, costly, and produced only four partial years, with the additional challenge that volume units could not be consistently normalized to cubic metres.
- Approach: An LLM‑assisted OCR pipeline (Gemini 2.5 Vision) with Python post‑processing to parse multi‑page issues, de‑duplicate hallucinations, split ship vs. cargo tables, and perform human‑in‑the‑loop normalization.
- Result: Near‑complete coverage across 1874–1899 at scale. Categorical fields (ports, commodities, units) are reliable; numerical quantities are not sufficiently accurate for precise measurement (in line with the historical unit heterogeneity that also limited human workflows).
- Value: High for research on the geography of British timber supply and the evolution of commodity types. Unsuitable for precise volumetric estimation or price analysis without targeted manual validation.

## Context and Goals
- Historical source: Weekly TTJ issues list arrivals by destination port with ship, origin, cargo, merchants, and (sometimes) dates.
- Prior workflow: Teams of research assistants transcribed selected years by hand. It was slow, expensive, prone to inconsistency, and hit a hard limit on unit normalization.
- Project goals now:
  - Scale extraction to all available years.
  - Achieve robust categorical accuracy (ports, commodities, units, merchants where possible).
  - Embrace limits on numerical precision and unit comparability while still enabling geographic and compositional analyses over time.

## Pipeline Overview
- OCR and Parsing
  - Gemini Vision OCR over preprocessed page images (deskew, contrast, split columns as needed).
  - Context‑aware parsing (`ttj_parser_v3.py`):
    - Recognizes multi‑page continuity and port headers; tracks date headers.
    - Extracts ship records across variant line formats (early @, standard dash, condensed).
  - Two‑table export: `ttj_shipments.csv` (ship‑level) and `ttj_cargo_details.csv` (item‑level) linked by `record_id`.
- Cleaning and Normalization
  - De‑duplication of LLM repetition/hallucination patterns (signature‑based matching on ship/route/date).
  - Authority normalization for ports with human‑in‑the‑loop review: ACCEPT / MAP / ERROR decisions and high‑threshold fuzzy matching.
  - Commodity normalization: consolidate frequent variants (e.g., deal/deals, battens, boards; “logs X” patterns).
- Analytical products
  - Long‑form detailed dataset (one row per cargo item), route/year aggregates, commodity/year trends, and a route‑commodity matrix.

## Data Quality and Validation
- Categorical accuracy (1883 London validation, N≈1,769 matches):
  - Ports: ~94% exact; ≈100% within fuzzy thresholds.
  - Commodities: ~93% exact; ≈100% within fuzzy thresholds.
  - Units: ~97% exact or semantically equivalent.
- Quantities:
  - ~38% exact; ~44% within 10%; a heavy tail of larger errors.
  - Even with perfect OCR, heterogeneous historical units (bdls., pcs., stds., tons, loads, cubic ft/fm, etc.) prevent reliable conversion to a common volumetric measure without detailed, context‑specific assumptions.
- Dates:
  - Arrival dates extracted where available; otherwise publication date is used, acceptable for weekly temporal resolution but not for exact arrival‑day analyses.

## What This Enables (and What It Doesn’t)
- Enables
  - Geography of supply: robust origin→destination routes by year and decade.
  - Commodity composition: shifts in types (deals/battens/boards vs. logs/timber; props/pitwood trends) over time.
  - Network‑style questions: port centrality, route specialization, emergence of new exporters.
- Not Suitable For (without targeted validation)
  - Precise volumetric estimation or price/quantity analytics.
  - Fine‑grained temporal analysis at the day level (where arrival dates are missing).
  - Research where numeric quantities must be accurate to tight tolerances across time and space.

## Critical Assessment of the LLM + Python Approach
- Strengths
  - Scale and Coverage: Processes entire multi‑decade corpus in hours, not months/years, making broad geographic questions tractable.
  - Categorical Reliability: Ports and commodity categories are sufficiently accurate for historical patterning and network analysis.
  - Reproducibility and Transparency: Code‑based pipeline, checkpoints, and documented decisions (review CSVs) foster replicability and auditability.
  - Human‑in‑the‑Loop Where It Matters: Ambiguous normalization (especially ports) is explicitly reviewed and recorded.
- Weaknesses and Risks
  - Numeric Instability: OCR plus layout variation, combined with historically diverse units, leads to unreliable quantities; post‑hoc normalization cannot overcome semantic heterogeneity.
  - Format Drift Sensitivity: TTJ’s layout evolved; regex patterns require maintenance and edge‑case handling (e.g., “St. John” truncation, dock/city context, em‑dash segmentation).
  - Hallucination/Duplication: LLM loop errors necessitate dedicated de‑duplication logic; misses can distort tallies without careful QA.
  - Post‑Processing Burden: The gains in speed shift effort to normalization, review files, and QA scripts—still far less costly than full manual transcription, but not “zero‑touch”.
- Comparison to Manual Transcription
  - Manual wins on: precision for selective numeric transcription where the unit context is carefully interpreted; bespoke knowledge for rare entities.
  - LLM+Python wins on: scale, speed, cost, and consistency in categorical extraction; ability to iterate and re‑run as methods improve.
  - Bottom line: For the intended research (geography and commodity composition), LLM+Python provides higher value: you can analyze the whole period rather than a small, potentially biased sample.

## Methodological Choices That Matter
- Multi‑Page, Context‑Aware Parsing: Essential for continuity across page breaks and for correct destination port assignment.
- Two‑Table Relational Design: Avoids duplication and simplifies commodity‑level analysis.
- Tiered Normalization Strategy: Combines automation with human review for historically ambiguous entities; focuses human effort where it has maximal impact.
- Checkpoints and Reruns: Design for re‑runnability enables incremental improvements (e.g., adding new port decisions) without full re‑processing costs.

## Limitations and Mitigations
- Long‑Tail Entities: Thousands of rare origin ports require domain research; mitigation is to prioritize by frequency and accept a coverage threshold (e.g., 92–95%).
- Diacritics/Encoding: Double‑encoded UTF‑8 corrected post‑hoc; residuals should be monitored in geocoding tasks.
- Merchant Names: Mixed forms and abbreviations; recommend extending merchant normalization and optional review (like ports) for network studies of firms.
- Table Structure: For future numeric work, consider specialized table structure detection and numeric OCR tuned to columns.

## Recommendations for Use
- Strongly Recommended
  - Route analysis by year/decade; port importance and route specialization.
  - Commodity composition over time (category counts, presence/absence, shares).
  - Network and geography visualizations (flows, hubs, specialization).
- Use with Caution
  - Any analysis requiring quantities as continuous measures. If necessary, constrain to commodities with consistent units in a narrow time window and validate on a sample.

## Opportunities for Incremental Improvement
- Commodity and Merchant Parsing
  - Treat em‑dash as a separator; use a unified per‑item regex that captures unit words and per‑item merchants; filter fragments/units masquerading as commodities.
  - Normalize merchants with an authority‑style review for high‑frequency variants.
- Ports
  - Apply case‑insensitive exacts before fuzzy, strip Canadian province suffixes pre‑match, and propagate the “St.” fix to all relevant patterns.
- QA and Uncertainty
  - Routine spot checks per batch; report categorical accuracy and quantity error summaries by year.
  - Document data confidence and recommended research questions alongside each dataset.

## Conclusion
The LLM‑ and Python‑based methodology transforms what was a narrow, partial corpus into a comprehensive, analysis‑ready dataset for studying the geography and composition of the British timber trade. While numeric volumes remain unreliable (reflecting both OCR limits and irreducible historical unit heterogeneity), categorical fidelity is high. For questions about who traded what, where, and when—ports, routes, and commodities—this approach delivers substantially more value than manual transcription, primarily by enabling whole‑period, reproducible analysis with transparent, reviewable normalization.

