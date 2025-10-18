#!/usr/bin/env bash
set -euo pipefail
# Split a PDF or image page into left/right column crops (with optional overlap)
# and optional vertical tiling, to improve OCR coverage for camera-captured pages.
#
# Usage:
#   tools/ocr_split_columns.sh INPUT OUTDIR [--dpi 400] [--overlap 20] [--tiles 1] [--v-overlap 10]
# - INPUT: PDF or single-page image (png/jpg/tif)
# - OUTDIR: output directory; files named <base>_{full|left|right}[.tileK].png
# - --dpi: rendering DPI for PDFs (default 400)
# - --overlap: horizontal overlap in pixels between left/right (default 20)
# - --tiles: split vertically into N tiles per column (default 1 = no tiling)
# - --v-overlap: vertical overlap percentage between tiles (default 10)

if [ $# -lt 2 ]; then
  echo "Usage: $0 INPUT OUTDIR [--dpi 400] [--overlap 20] [--tiles 1] [--v-overlap 10]" >&2
  exit 1
fi

IN="$1"; OUTDIR="$2"; shift 2
DPI=400
H_OVERLAP=20
TILES=1
V_OVERLAP=10

while [ $# -gt 0 ]; do
  case "$1" in
    --dpi) shift; DPI="${1:-400}" ;;
    --overlap) shift; H_OVERLAP="${1:-20}" ;;
    --tiles) shift; TILES="${1:-1}" ;;
    --v-overlap) shift; V_OVERLAP="${1:-10}" ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift || true
done

mkdir -p "$OUTDIR"

base=$(basename "$IN")
stem="${base%.*}"
ext="${base##*.}"; ext="${ext,,}"

render_full_png() {
  local src="$1"; local outstem="$2"; local png
  if [ "$ext" = "pdf" ]; then
    pdftoppm -gray -r "$DPI" -png "$src" "$outstem" >/dev/null
    png="${outstem}-1.png"
  else
    # copy or convert to PNG
    if command -v magick >/dev/null 2>&1; then
      magick "$src" -colorspace Gray "$outstem-1.png"
    elif command -v convert >/dev/null 2>&1; then
      convert "$src" -colorspace Gray "$outstem-1.png"
    else
      cp "$src" "$outstem-1.png"
    fi
    png="${outstem}-1.png"
  fi
  echo "$png"
}

dimension_of() {
  local img="$1"
  file "$img" | sed -n 's/.*, \([0-9]\+\) x \([0-9]\+\).*/\1 \2/p'
}

crop_with_im() {
  local img="$1"; local x="$2"; local y="$3"; local w="$4"; local h="$5"; local out="$6"
  if command -v magick >/dev/null 2>&1; then
    magick "$img" -crop ${w}x${h}+${x}+${y} +repage "$out"
  elif command -v convert >/dev/null 2>&1; then
    convert "$img" -crop ${w}x${h}+${x}+${y} +repage "$out"
  else
    echo "ImageMagick not found for cropping. Skipping $out" >&2
    return 1
  fi
}

full_png="$OUTDIR/${stem}"
full_png=$(render_full_png "$IN" "$full_png")
cp "$full_png" "$OUTDIR/${stem}_full.png"

dims=$(dimension_of "$full_png")
if [ -z "$dims" ]; then
  echo "Could not determine dimensions for $full_png" >&2
  exit 2
fi
W=$(echo "$dims" | awk '{print $1}')
H=$(echo "$dims" | awk '{print $2}')
half=$(( W / 2 ))
ov=$H_OVERLAP
left_w=$(( half + ov ))
right_x=$(( half - ov ))
right_w=$(( W - right_x ))

left_png="$OUTDIR/${stem}_left.png"
right_png="$OUTDIR/${stem}_right.png"
crop_with_im "$full_png" 0 0 "$left_w" "$H" "$left_png" || true
crop_with_im "$full_png" "$right_x" 0 "$right_w" "$H" "$right_png" || true

if [ "$TILES" -gt 1 ]; then
  # Vertical tiles with overlap percentage
  perc=$V_OVERLAP
  step=$(( H * (100 - perc) / 100 / TILES ))
  tile_h=$(( H * 100 / TILES / 100 + H * perc / 100 / TILES ))
  if [ $tile_h -le 0 ] || [ $step -le 0 ]; then
    step=$(( H / TILES ))
    tile_h=$step
  fi
  idx=1
  for colimg in "$left_png" "$right_png"; do
    [ -f "$colimg" ] || continue
    y=0
    k=1
    while [ $y -lt $H ]; do
      # ensure last tile includes the bottom
      if [ $(( y + tile_h )) -gt $H ]; then y=$(( H - tile_h )); fi
      out="$OUTDIR/${stem}_$(basename "$colimg" .png).tile${k}.png"
      crop_with_im "$colimg" 0 "$y" $(echo $(dimension_of "$colimg") | awk '{print $1}') "$tile_h" "$out" || true
      y=$(( y + step ))
      k=$(( k + 1 ))
      if [ $k -gt $TILES ]; then break; fi
    done
    idx=$(( idx + 1 ))
  done
fi

echo "Wrote: $OUTDIR/${stem}_full.png, ${stem}_left.png, ${stem}_right.png"
