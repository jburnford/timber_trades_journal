#!/usr/bin/env bash
set -euo pipefail
# Bundle each subdirectory of images into one PDF.
# Usage: tools/bundle_images_to_pdf.sh ROOT_DIR [--pattern '*.png'] [--out EXT]
# - Creates PDFs in each subdirectory alongside images, named <dirname>.pdf
# - Requires either `img2pdf` or ImageMagick `magick`/`convert`.

ROOT="${1:-}"
if [ -z "$ROOT" ]; then
  echo "Usage: $0 ROOT_DIR [--pattern '*.png']" >&2
  exit 1
fi
shift || true

PATTERN='*.png'
while [ $# -gt 0 ]; do
  case "$1" in
    --pattern) shift; PATTERN="${1:-*.png}";;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
  shift || true
done

if command -v img2pdf >/dev/null 2>&1; then
  BACKEND=img2pdf
elif command -v magick >/dev/null 2>&1; then
  BACKEND=magick
elif command -v convert >/dev/null 2>&1; then
  BACKEND=convert
else
  echo "Need img2pdf or ImageMagick installed." >&2
  exit 2
fi

find "$ROOT" -type d | while read -r dir; do
  shopt -s nullglob
  imgs=("$dir"/$PATTERN)
  shopt -u nullglob
  if [ ${#imgs[@]} -eq 0 ]; then continue; fi
  # Natural sort by name
  IFS=$'\n' imgs_sorted=($(printf '%s\n' "${imgs[@]}" | sort -V))
  out="$dir/$(basename "$dir").pdf"
  echo "Bundling ${#imgs_sorted[@]} images in $dir -> $out"
  case "$BACKEND" in
    img2pdf)
      img2pdf "${imgs_sorted[@]}" -o "$out" ;;
    magick)
      magick "${imgs_sorted[@]}" "$out" ;;
    convert)
      convert "${imgs_sorted[@]}" "$out" ;;
  esac
done

