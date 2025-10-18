#!/usr/bin/env bash
set -euo pipefail

# Discover all candidate inputs (images and PDFs) under specified roots and
# convert them into single-page, grayscale PDFs in one output dir using
# tools/batch_optimize_to_pdf.sh.
#
# Usage:
#   tools/run_all_to_nibi.sh OUT_DIR [--dpi 350] [--skip-existing] [--root PATH ...]
# Examples:
#   tools/run_all_to_nibi.sh work/nibi_upload --dpi 300 --root 1875 --root 1877 --root 1879 --root 1881 --root 1885 --root 1887
#   nohup bash tools/run_all_to_nibi.sh work/nibi_upload --dpi 300 --skip-existing --root 1879 --root 1881 > work/run_all.log 2>&1 &

if [ $# -lt 1 ]; then
  echo "Usage: $0 OUT_DIR [--dpi 350] [--skip-existing] [--root PATH ...]" >&2
  exit 1
fi

OUT_DIR="$1"; shift
DPI=350
SKIP=false
ROOTS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dpi) shift; DPI="${1:-350}" ;;
    --skip-existing) SKIP=true ;;
    --root) shift; ROOTS+=("${1:-.}") ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
  shift || true
done

if [ ${#ROOTS[@]} -eq 0 ]; then
  # Default to current dir
  ROOTS=(.)
fi

TMP="${TMPDIR:-/tmp}/ttj_run_all.$$.txt"
trap 'rm -f "$TMP"' EXIT

# Build list of inputs; exclude metadata/hidden files
for r in "${ROOTS[@]}"; do
  if [ ! -d "$r" ]; then continue; fi
  find "$r" -type f \
    \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.tif" -o -iname "*.tiff" -o -iname "*.pdf" \) \
    ! -name ".DS_Store" ! -name "*:Zone.Identifier" ! -name "*:com.dropbox.attrs" ! -name "*.txt" \
    ! -path "*/.*" >> "$TMP"
done

# Natural sort and dedupe
sort -u -V "$TMP" -o "$TMP"

COUNT=$(wc -l < "$TMP" | tr -d ' ')
echo "Discovered $COUNT input file(s). Output: $OUT_DIR (dpi=$DPI, skip-existing=$SKIP)"

CMD=( "$(dirname "$0")/batch_optimize_to_pdf.sh" "$OUT_DIR" "@${TMP}" --dpi "$DPI" )
if $SKIP; then CMD+=( --skip-existing ); fi

"${CMD[@]}"

echo "All done. PDFs are in: $OUT_DIR"

