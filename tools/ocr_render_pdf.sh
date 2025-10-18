#!/usr/bin/env bash
set -euo pipefail
# Render PDF pages to PNG for OCR.
# Usage: tools/ocr_render_pdf.sh input.pdf outdir [dpi]

if ! command -v pdftoppm >/dev/null 2>&1; then
  echo "pdftoppm not found. Please install poppler utils." >&2
  exit 2
fi

if [ $# -lt 2 ]; then
  echo "Usage: $0 input.pdf outdir [dpi]" >&2
  exit 1
fi

IN="$1"; OUTDIR="$2"; DPI="${3:-500}"
mkdir -p "$OUTDIR"
base=$(basename "$IN" .pdf)

pdftoppm -r "$DPI" -png "$IN" "$OUTDIR/$base" >/dev/null
echo "Rendered to $OUTDIR/${base}-*.png at ${DPI} dpi"

