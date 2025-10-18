#!/usr/bin/env bash
set -euo pipefail

# Convert a set of image-or-PDF inputs into single-page, grayscale PDFs in one output directory.
# - Renders PDF pages to PNG at specified DPI, optionally preprocesses (if ImageMagick is available),
#   then wraps a single PNG back into a PDF using img2pdf (preferred) or ImageMagick as fallback.
# - Output filenames preserve the input basename with .pdf extension.
#
# Usage:
#   tools/batch_optimize_to_pdf.sh OUT_DIR INPUT1 [INPUT2 ...] [--dpi 400] [--skip-existing]
#   tools/batch_optimize_to_pdf.sh OUT_DIR @filelist.txt [--dpi 400] [--skip-existing]
#
# Notes:
# - If an input PDF has multiple pages, the first page is used; a warning is printed.
# - If ImageMagick (magick/convert) is not installed, preprocessing is skipped (still renders grayscale).

if [ $# -lt 2 ]; then
  echo "Usage: $0 OUT_DIR INPUT... [--dpi 400]" >&2
  exit 1
fi

OUT_DIR="$1"; shift
DPI=400
SKIP_EXISTING=false

# Collect inputs (allow @filelist)
INPUTS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dpi) shift; DPI="${1:-400}" ;;
    --skip-existing) SKIP_EXISTING=true ;;
    @*)
      listfile="${1#@}"
      if [ -f "$listfile" ]; then
        while IFS= read -r line; do [ -n "$line" ] && INPUTS+=("$line"); done < "$listfile"
      else
        echo "List file not found: $listfile" >&2; exit 2
      fi
      ;;
    *) INPUTS+=("$1") ;;
  esac
  shift || true
done

command -v pdftoppm >/dev/null 2>&1 || {
  echo "pdftoppm is required." >&2; exit 2;
}

if command -v img2pdf >/dev/null 2>&1; then
  PDF_BACKEND=img2pdf
elif command -v magick >/dev/null 2>&1; then
  PDF_BACKEND=magick
elif command -v convert >/dev/null 2>&1; then
  PDF_BACKEND=convert
else
  echo "Need img2pdf or ImageMagick installed to write PDFs." >&2
  exit 2
fi

PREPROC_SCRIPT="$(dirname "$0")/ocr_preprocess.sh"
HAS_IM=false
if command -v magick >/dev/null 2>&1 || command -v convert >/dev/null 2>&1; then
  HAS_IM=true
fi

mkdir -p "$OUT_DIR"
WORKDIR="${TMPDIR:-/tmp}/ttj_opt.$$"
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT

warn() { echo "$*" >&2; }

process_pdf() {
  local in="$1"; local base="$2"; local png="$WORKDIR/${base}-1.png"
  pdftoppm -gray -r "$DPI" -png "$in" "$WORKDIR/${base}" >/dev/null
  if compgen -G "$WORKDIR/${base}-*.png" > /dev/null; then
    local count=$(ls "$WORKDIR/${base}"-*.png | wc -l | tr -d ' ')
    if [ "$count" -gt 1 ]; then warn "[multi-page] $in -> using first page"; fi
  else
    warn "No pages rendered from $in"; return 1
  fi
  if [ -f "$png" ]; then
    echo "$png"
  else
    # Fallback to the first rendered file
    echo "$(ls "$WORKDIR/${base}"-*.png | sort -V | head -n1)"
  fi
}

process_image() {
  local in="$1"; local base="$2"; local out="$WORKDIR/${base}.png"
  # Ensure grayscale via pdftoppm pipeline is overkill; use ImageMagick if available, else copy.
  if $HAS_IM; then
    if command -v magick >/dev/null 2>&1; then magick "$in" -colorspace Gray "$out"; else convert "$in" -colorspace Gray "$out"; fi
  else
    cp "$in" "$out"
  fi
  echo "$out"
}

preprocess_png() {
  local inpng="$1"; local outpng="$2"
  if $HAS_IM && [ -x "$PREPROC_SCRIPT" ]; then
    "$PREPROC_SCRIPT" "$inpng" "$outpng" --deskew --clahe 50x50+128+3 >/dev/null || cp "$inpng" "$outpng"
  else
    cp "$inpng" "$outpng"
  fi
}

png_to_pdf() {
  local inpng="$1"; local outpdf="$2"
  case "$PDF_BACKEND" in
    img2pdf)
      img2pdf "$inpng" -o "$outpdf" ;;
    magick)
      magick "$inpng" "$outpdf" ;;
    convert)
      convert "$inpng" "$outpdf" ;;
  esac
}

for IN in "${INPUTS[@]}"; do
  if [ ! -f "$IN" ]; then warn "Skip missing: $IN"; continue; fi
  ext="${IN##*.}"; ext="${ext,,}"
  base=$(basename "$IN")
  base="${base%.*}"
  echo "Processing: $IN"
  png_src=""
  case "$ext" in
    pdf) png_src=$(process_pdf "$IN" "$base") || { warn "Failed to render $IN"; continue; } ;;
    png|jpg|jpeg|tif|tiff) png_src=$(process_image "$IN" "$base") ;;
    *) warn "Unsupported extension: $IN"; continue ;;
  esac
  png_pre="$WORKDIR/${base}.prep.png"
  preprocess_png "$png_src" "$png_pre"
  OUT_PDF="$OUT_DIR/${base}.pdf"
  if $SKIP_EXISTING && [ -f "$OUT_PDF" ]; then
    echo "[skip] $OUT_PDF exists"
    continue
  fi
  png_to_pdf "$png_pre" "$OUT_PDF"
  echo "-> $OUT_PDF"
done

echo "Done. Output directory: $OUT_DIR"
