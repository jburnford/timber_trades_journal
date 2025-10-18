#!/usr/bin/env bash
set -euo pipefail
# Basic OCR-friendly image preprocessing using ImageMagick if available.
# Usage:
#   tools/ocr_preprocess.sh input.png output.png \
#     [--gray] [--auto-orient] [--deskew] \
#     [--contrast 10x15] [--autolevel] [--clahe 50x50+128+3] \
#     [--sharpen 0x1] [--adaptive-sharpen 0x1] \
#     [--despeckle] [--median 1] [--reduce-noise 1] \
#     [--threshold 60%] [--adaptive-threshold 15x15+10%] \
#     [--trim 5%]
# Notes:
# - Requires `magick` (ImageMagick 7) or `convert` (ImageMagick 6). If neither is found, exits non-zero.

if command -v magick >/dev/null 2>&1; then
  IM=magick
elif command -v convert >/dev/null 2>&1; then
  IM=convert
else
  echo "ImageMagick not found (magick/convert). Please install it." >&2
  exit 2
fi

if [ $# -lt 2 ]; then
  echo "Usage: $0 input.png output.png [options]" >&2
  exit 1
fi

IN="$1"; OUT="$2"; shift 2

# Defaults tuned for TTJ scans: grayscale, mild deskew, contrast, sharpen, and slight de-noise
OPTS=( -colorspace Gray )

# Optional extras via flags
while [ $# -gt 0 ]; do
  case "$1" in
    --gray) ;; # already grayscale by default
    --auto-orient) OPTS+=( -auto-orient ) ;;
    --deskew) OPTS+=( -deskew 40% );;
    --contrast) shift; OPTS+=( -brightness-contrast "$1" );;
    --autolevel) OPTS+=( -auto-level ) ;;
    --sharpen) shift; OPTS+=( -unsharp "$1" );;
    --adaptive-sharpen) shift; OPTS+=( -adaptive-sharpen "$1" );;
    --clahe) shift; OPTS+=( -clahe "$1" );;
    --threshold) shift; OPTS+=( -threshold "$1" );;
    --adaptive-threshold) shift; OPTS+=( -adaptive-threshold "$1" );;
    --despeckle) OPTS+=( -despeckle ) ;;
    --median) shift; OPTS+=( -median "$1" );;
    --reduce-noise) shift; OPTS+=( -reduce-noise "$1" );;
    --trim) shift; OPTS+=( -fuzz "$1" -trim +repage );;
    *) echo "Unknown option: $1" >&2; exit 1;;
  esac
  shift || true
done

"$IM" "$IN" ${OPTS[@]} "$OUT"
echo "Wrote $OUT"
