#!/usr/bin/env python3
import argparse
import os

import cv2

# Reuse robust deskew and OCR preprocessing from the companion module
from deskew_preprocess_cv import (
    load_image,
    auto_orient,
    deskew as best_deskew,
    find_content_bbox,
    preprocess_for_ocr,
)


def resize_max_width(img, max_width: int):
    if max_width is None or max_width <= 0:
        return img
    h, w = img.shape[:2]
    if w <= max_width:
        return img
    scale = max_width / float(w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)


def main():
    ap = argparse.ArgumentParser(description="Deskew TTJ page and emit a single *_full.png (no column splitting)")
    ap.add_argument("input", help="Input PDF or image")
    ap.add_argument("--outdir", default="work/cvdeskew", help="Output directory")
    ap.add_argument("--dpi", type=int, default=400, help="DPI for PDF rendering (when input is PDF)")
    ap.add_argument("--deskew-method", choices=["auto", "hough", "lsd", "sweep"], default="auto", help="Deskew method (best-of when auto)")
    ap.add_argument("--max-angle", type=float, default=12.0, help="Maximum absolute skew to consider (degrees)")
    # Output size and variants
    ap.add_argument("--max-width", type=int, default=2000, help="Resize output to at most this width (px);")
    ap.add_argument("--emit-ocr-gray", action='store_true', help="Also write enhanced grayscale for OCR")
    ap.add_argument("--emit-ocr-bin", action='store_true', help="Also write binarized OCR image")
    # OCR optimization knobs (used only if OCR variants requested)
    ap.add_argument("--scale", type=float, default=1.0, help="Optional scale factor for OCR enhancement")
    ap.add_argument("--clip-limit", type=float, default=2.0, help="CLAHE clip limit")
    ap.add_argument("--tile", type=int, default=8, help="CLAHE tile size")
    ap.add_argument("--denoise-h", type=int, default=5, help="fastNlMeansDenoising h (0 disables)")
    ap.add_argument("--sharpen", type=float, default=0.5, help="Unsharp amount (0 disables)")
    ap.add_argument("--binarize", choices=["adaptive", "otsu"], default="adaptive", help="Binarization method for OCR image")
    ap.add_argument("--debug", action='store_true', help="Write debug overlay (saved as JPEG) with content box and angle")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    img, origin = load_image(args.input, dpi=args.dpi, tmpdir=args.outdir)
    if img is None:
        raise SystemExit("Failed to load image")
    img = auto_orient(img)

    # Deskew using the best-of strategy
    # Keep rotation small (no 90° orientation flips) to match expectations
    img_dk, ang = best_deskew(img, method=args.deskew_method, max_angle=args.max_angle, try_rotations=False)

    # Optional: trim to content to avoid black borders (used for OCR variants)
    h, w = img_dk.shape[:2]
    bx, by, bw, bh = find_content_bbox(img_dk)
    roi = img_dk[by:by + bh, bx:bx + bw]

    # OCR-oriented enhancement (optional, always written for convenience)
    gray_enh = None
    bin_img = None
    if args.emit_ocr_gray or args.emit_ocr_bin:
        gray_enh, bin_img = preprocess_for_ocr(
            roi,
            scale=args.scale,
            clip_limit=args.clip_limit,
            tile=args.tile,
            denoise_h=args.denoise_h,
            sharpen=args.sharpen,
            bin_method=args.binarize,
        )

    base = os.path.splitext(os.path.basename(args.input))[0]
    # Resize full image to target width for smaller size
    out_full = resize_max_width(img_dk, args.max_width)
    p_full = os.path.join(args.outdir, f"{base}_full.png")
    cv2.imwrite(p_full, out_full, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    # Optional OCR variants
    if gray_enh is not None and args.emit_ocr_gray:
        out_gray = resize_max_width(gray_enh, args.max_width)
        p_gray = os.path.join(args.outdir, f"{base}_full.ocr.gray.png")
        cv2.imwrite(p_gray, out_gray, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if bin_img is not None and args.emit_ocr_bin:
        out_bin = resize_max_width(bin_img, args.max_width)
        p_bin = os.path.join(args.outdir, f"{base}_full.ocr.bin.png")
        cv2.imwrite(p_bin, out_bin, [cv2.IMWRITE_PNG_COMPRESSION, 9])

    if args.debug:
        overlay = cv2.cvtColor(resize_max_width(img_dk, args.max_width), cv2.COLOR_GRAY2BGR)
        # Rescale bbox for overlay if resized
        scale = overlay.shape[1] / float(w)
        bx_s = int(round(bx * scale)); by_s = int(round(by * scale)); bw_s = int(round(bw * scale)); bh_s = int(round(bh * scale))
        cv2.rectangle(overlay, (bx_s, by_s), (bx_s + bw_s, by_s + bh_s), (0, 255, 0), 2)
        cv2.putText(overlay, f"skew={ang:.2f} deg", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        p_dbg = os.path.join(args.outdir, f"{base}_full.debug.jpg")
        cv2.imwrite(p_dbg, overlay, [cv2.IMWRITE_JPEG_QUALITY, 85])

    print(f"Deskewed (angle={ang:.2f}°). Wrote: {p_full}")


if __name__ == "__main__":
    main()
