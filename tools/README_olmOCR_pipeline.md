olmOCR-first pipeline for TTJ pages

Overview
- Optimize page images, run through olmOCR, then parse and normalize locally using the provided tools and your dictionaries.

1) Prepare images or PDFs
- If you already have per-page images (PNG/JPG), skip to step 2.
- If you have PDFs, render at high DPI:
  - `bash tools/ocr_render_pdf.sh path/to/page.pdf work/pages 500`

2) Optimize images for OCR (contrast/deskew/sharpen)
- Requires ImageMagick (`magick` or `convert`). Examples:
  - `bash tools/ocr_preprocess.sh work/pages/page-1.png work/prep/page-1.png --deskew --clahe 50x50+128+3`
  - Tweak `--brightness-contrast` via `--contrast 10x15` and `--sharpen` as needed.
- Tips:
  - Keep grayscale; use CLAHE for faint text; light sharpen avoids halos.
  - If column bleed occurs, consider manual column crops for testing.

3) Bundle subdirectories of images into PDFs (optional, for olmOCR upload batch)
- If your images are in subfolders per page/batch, you can create PDFs quickly:
  - `bash tools/bundle_images_to_pdf.sh work/prep --pattern '*.png'`
- Uses `img2pdf` if available; else ImageMagick.

4) Run pages through olmOCR
- Upload the optimized images or PDFs to olmOCR.
- Export one text file per page/column if possible (one arrival per line is ideal but not required).

5) Parse to JSON (with your dictionaries)
- Provide product/port dictionaries (extend or alias terms) as JSON.
  - See: `tools/config/custom_products.example.json`, `tools/config/custom_ports.example.json`.
- Parse:
  - `python3 tools/ttj_parse.py cleaned_lines.txt --products tools/config/custom_products.json --ports tools/config/custom_ports.json > parsed.json`

6) Triage for LLM/human correction (minimize tokens)
- `python3 tools/ttj_triage.py parsed.json -o triage.json -t triage.txt`
- Prepare small batches:
  - `python3 tools/ttj_llm_queue_prep.py triage.json --size 10 --prefix batches/batch`
- Use prompt `tools/prompts/line_correct_minimal.txt` to correct lines; keep output one line per input line.

7) Re-parse and post-process
- `python3 tools/ttj_parse.py corrected_batch.txt --products ... --ports ... > corrected_parsed.json`
- `python3 tools/ttj_postprocess.py corrected_parsed.json -o final.json`

Notes & Best Practices
- For problematic pages, do column splits before OCR; add a small gutter margin to avoid cross-column noise.
- Keep quantities in OCR text if easier, the parser strips common quantity tokens.
- The parser is conservative: it will set `warnings` when unsure; use triage to target just those lines.

