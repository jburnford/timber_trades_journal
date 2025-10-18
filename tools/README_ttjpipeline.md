TTJ parsing pipeline (practical, column-aware)

Goal
- Produce reliable one-line OCR for each arrival sentence, then feed into `tools/ttj_parse.py` to emit the exact JSON schema.

Recommended offline workflow
- Convert each PDF page to a high-res image (300–600 dpi):
  - `pdftoppm -r 400 page.pdf page -png`
- Deskew + improve contrast (any of: ocrmypdf, ImageMagick, or OpenCV):
  - `ocrmypdf --rotate-pages --deskew --tesseract-timeout=0 -l eng in.pdf out.pdf` (fast way if you have it)
  - or ImageMagick per-page: `magick page-1.png -colorspace Gray -contrast-stretch 0.5%x0.5% -sharpen 0x1 page-1.clean.png`
- Split columns (historical TTJ is two columns):
  - Quick manual split: visually determine the center x, and crop:
    - `magick page-1.clean.png -crop 50%x100%+0+0 page-1.left.png`
    - `magick page-1.clean.png -crop 50%x100%+50%+0 page-1.right.png`
  - Auto split (OpenCV approach): detect the widest vertical whitespace gutter and crop left/right; keep a 10–20 px overlap.
- Tesseract OCR per column with line-ish segmentation:
  - `tesseract page-1.left.png page-1.left -l eng --psm 6`
  - `tesseract page-1.right.png page-1.right -l eng --psm 6`
  - If lines merge, try `--psm 4`; if broken, try `--psm 6` again with better contrast.
- Normalize lines (recommended scripts or editor macros):
  - Replace fancy dashes with a consistent `—` (em dash) or `--` so the parser can split fields consistently.
  - Join obvious hyphenated line breaks (e.g., `deal-\nends` → `deal-ends`).
  - Keep one sentence per line when possible. It’s fine if a line holds one whole arrival.

Parsing to JSON
- Feed the cleaned text (one line per arrival sentence) into the parser:
  - `python3 tools/ttj_parse.py cleaned_lines.txt > out.json`
- The script emits a JSON array where each object has exactly the required keys.

Heuristics used by the parser
- Splits records by large dashes into up to three parts: `arrival_place — departure_port — products; merchants`.
- Removes quantities conservatively (numbers + common units) from the product fragment but preserves wording.
- Moves meaningful parentheticals to `notes` (drops trivial markers like `(s)`).
- Product typing maps controlled vocabulary; “redwood deals and ends” → types include `deals` and `deal ends` (and `redwood`).
- Port normalization applies light variant mapping (e.g., `Dantzic`→`Danzig`, `Memel`→`Klaipeda`) and checks a likely-ports list.
- Warnings: `unknown_port` when no confident normalization; `ambiguous_products` when no product type is detected.

When OCR is tricky
- Increase DPI to 500–600 for faint pages; apply CLAHE (contrast-limited adaptive histogram equalization) before OCR.
- Try `--psm 4` if `--psm 6` merges adjacent lines; ensure columns are cropped cleanly.
- If columns still cross-contaminate, add a 10–20 px vertical margin between crops.

Human-in-the-loop fallback
- If automation struggles, split work: research assistant transcribes columns to one-sentence-per-line text (without quantities), then run the parser.
- You can process the left and right columns separately and concat texts before parsing.

Notes
- The parser is conservative by design: prefers `null` over guessing dates or merchants.
- Ignore TTJ headers and totals; feed only arrival lines. The parser already drops many obvious headers/summaries.

