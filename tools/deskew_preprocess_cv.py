#!/usr/bin/env python3
import argparse
import os
import subprocess
from typing import Optional, Tuple

import cv2
import numpy as np


def render_pdf_to_png(pdf_path: str, outdir: str, dpi: int = 400) -> str:
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    outstem = os.path.join(outdir, base)
    cmd = ["pdftoppm", "-gray", "-r", str(dpi), "-png", pdf_path, outstem]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    png = f"{outstem}-1.png"
    if not os.path.isfile(png):
        for i in range(1, 5):
            cand = f"{outstem}-{i}.png"
            if os.path.isfile(cand):
                png = cand
                break
    return png


def load_image(path: str, dpi: int = 400, tmpdir: Optional[str] = None) -> Tuple[np.ndarray, str]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        if tmpdir is None:
            tmpdir = "/tmp"
        png = render_pdf_to_png(path, tmpdir, dpi)
        img = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
        return img, png
    else:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        return img, path


def auto_orient(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    if w > h * 1.2:
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img


def _deskew_hough(img: np.ndarray, max_angle: float = 15.0) -> float:
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 1800, threshold=200)
    angle = 0.0
    if lines is not None:
        angles = []
        for rho_theta in lines[:3000]:
            rho, theta = rho_theta[0]
            deg = (theta * 180 / np.pi)
            if deg > 90:
                deg -= 180
            if -max_angle <= deg <= max_angle:
                angles.append(deg)
        if angles:
            angle = float(np.median(angles))
    return angle


def _projection_variance_score(bin_img: np.ndarray) -> float:
    # Assumes white text on black (255 on 0) or binary 0/255
    if bin_img.dtype != np.uint8:
        bin_img = bin_img.astype(np.uint8)
    # Count white pixels per row; variance is higher when lines are horizontal and tight
    row_sums = np.sum(bin_img > 0, axis=1).astype(np.float32)
    # Normalize to be robust to size
    if row_sums.size == 0:
        return 0.0
    row_sums -= row_sums.mean()
    var = float(np.mean(row_sums * row_sums))
    return var


def _deskew_sweep(img: np.ndarray, max_angle: float = 7.0, coarse: float = 1.0, fine: float = 0.1) -> float:
    # Downscale for speed
    target_w = 1200
    h, w = img.shape[:2]
    scale = min(1.0, target_w / float(max(w, 1)))
    small = img if abs(scale - 1.0) < 1e-3 else cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    # Binarize for stable scoring
    bin_small = cv2.adaptiveThreshold(small, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 35, 10)
    bin_small = 255 - bin_small  # text as white

    def score_for(angle_deg: float) -> float:
        hh, ww = bin_small.shape[:2]
        M = cv2.getRotationMatrix2D((ww // 2, hh // 2), angle_deg, 1.0)
        rot = cv2.warpAffine(bin_small, M, (ww, hh), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
        return _projection_variance_score(rot)

    # Coarse search
    best_angle = 0.0
    best_score = -1.0
    a = -max_angle
    while a <= max_angle + 1e-6:
        s = score_for(a)
        if s > best_score:
            best_score = s
            best_angle = a
        a += coarse

    # Fine search around best
    start = best_angle - coarse
    end = best_angle + coarse
    a = start
    while a <= end + 1e-9:
        s = score_for(a)
        if s > best_score:
            best_score = s
            best_angle = a
        a += fine
    return best_angle


def rotate_image(img: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 1e-3:
        return img
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    # Use white border to make rotation visually obvious (white corners)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    v = values[order]
    w = weights[order]
    c = np.cumsum(w)
    cutoff = 0.5 * np.sum(w)
    idx = int(np.searchsorted(c, cutoff))
    return float(v[min(idx, len(v) - 1)])


def _deskew_lsd(img: np.ndarray, max_angle: float = 15.0) -> float:
    # Prepare image for line segment detection
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)
    try:
        lsd = cv2.createLineSegmentDetector()  # type: ignore[attr-defined]
    except Exception:
        return 0.0
    lines, widths, prec, nfa = lsd.detect(edges)
    if lines is None or len(lines) == 0:
        return 0.0
    angles = []
    weights = []
    for seg in lines:
        x1, y1, x2, y2 = seg[0]
        dx = float(x2 - x1)
        dy = float(y2 - y1)
        length = (dx * dx + dy * dy) ** 0.5
        if length < 30:  # ignore tiny segments
            continue
        ang = np.degrees(np.arctan2(dy, dx))
        # Normalize angle to [-90, 90]
        if ang > 90:
            ang -= 180
        if ang < -90:
            ang += 180
        # Focus on near-horizontal lines within +/- max_angle
        if -max_angle <= ang <= max_angle:
            angles.append(ang)
            weights.append(length)
    if not angles:
        return 0.0
    a = np.array(angles, dtype=np.float32)
    w = np.array(weights, dtype=np.float32)
    # Robust central tendency: weighted median of angles
    return _weighted_median(a, w)


def _alignment_score(img: np.ndarray, angle_deg: float) -> float:
    # Score alignment by rotating a small binary image and computing projection variance
    target_w = 1200
    h, w = img.shape[:2]
    scale = min(1.0, target_w / float(max(w, 1)))
    small = img if abs(scale - 1.0) < 1e-3 else cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    bin_small = cv2.adaptiveThreshold(small, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 35, 10)
    bin_small = 255 - bin_small
    hh, ww = bin_small.shape[:2]
    M = cv2.getRotationMatrix2D((ww // 2, hh // 2), angle_deg, 1.0)
    rot = cv2.warpAffine(bin_small, M, (ww, hh), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    return _projection_variance_score(rot)


def _deskew_best_of(img: np.ndarray, method: str = "auto", max_angle: float = 7.0) -> Tuple[np.ndarray, float]:
    angle = 0.0
    if method == "hough":
        angle = _deskew_hough(img, max_angle=max_angle)
        return rotate_image(img, angle), angle
    if method == "lsd":
        angle = _deskew_lsd(img, max_angle=max_angle)
        return rotate_image(img, angle), angle
    if method == "sweep":
        angle = _deskew_sweep(img, max_angle=max_angle, coarse=1.0, fine=0.1)
        return rotate_image(img, angle), angle

    # method == auto or best-of: try all and pick the best by alignment score
    cand = []
    a_h = _deskew_hough(img, max_angle=max_angle)
    cand.append((a_h, "hough"))
    a_l = _deskew_lsd(img, max_angle=max_angle)
    cand.append((a_l, "lsd"))
    # Allow sweep to explore; can be slower but robust
    a_s = _deskew_sweep(img, max_angle=max_angle, coarse=1.0, fine=0.1)
    cand.append((a_s, "sweep"))

    # Score each candidate and choose the best
    best_angle = 0.0
    best_score = -1.0
    best_src = "none"
    for a, src in cand:
        s = _alignment_score(img, a)
        if s > best_score:
            best_score = s
            best_angle = a
            best_src = src

    # Fine refine around best angle
    refine_start = best_angle - 0.6
    refine_end = best_angle + 0.6
    a = refine_start
    while a <= refine_end + 1e-9:
        s = _alignment_score(img, a)
        if s > best_score:
            best_score = s
            best_angle = a
        a += 0.05

    rotated = rotate_image(img, best_angle)
    return rotated, best_angle


def deskew(img: np.ndarray, method: str = "auto", max_angle: float = 7.0, try_rotations: bool = True) -> Tuple[np.ndarray, float]:
    """Deskew with optional 0/±90 orientation search; returns rotated image and total angle."""
    if not try_rotations:
        return _deskew_best_of(img, method=method, max_angle=max_angle)

    # Evaluate base and ±90 orientations; choose best by alignment score after deskew
    orientations = [0.0, 90.0, -90.0]
    best_img = img
    best_total_angle = 0.0
    best_score = -1.0
    for ori in orientations:
        candidate = rotate_image(img, ori) if abs(ori) > 1e-6 else img
        dk_img, dk_ang = _deskew_best_of(candidate, method=method, max_angle=max_angle)
        total_ang = ori + dk_ang
        # Score
        s = _alignment_score(dk_img, 0.0)
        if s > best_score:
            best_score = s
            best_img = dk_img
            best_total_angle = total_ang
    return best_img, best_total_angle


def find_content_bbox(img: np.ndarray) -> Tuple[int, int, int, int]:
    """Find a tight content box to avoid black borders/margins. Returns (x, y, w, h)."""
    h, w = img.shape[:2]
    thr = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 35, 5)
    bin_inv = 255 - thr
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(bin_inv, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0, 0, w, h
    c = max(contours, key=cv2.contourArea)
    x, y, bw, bh = cv2.boundingRect(c)
    pad = max(5, int(min(w, h) * 0.01))
    x = max(0, x - pad)
    y = max(0, y - pad)
    bw = min(w - x, bw + 2 * pad)
    bh = min(h - y, bh + 2 * pad)
    if bw < w * 0.5 or bh < h * 0.5:
        return 0, 0, w, h
    return x, y, bw, bh


def clahe_contrast(img: np.ndarray, clip_limit: float = 2.0, tile: int = 8) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
    return clahe.apply(img)


def unsharp_mask(img: np.ndarray, sigma: float = 1.0, amount: float = 1.0) -> np.ndarray:
    blurred = cv2.GaussianBlur(img, (0, 0), sigma)
    sharp = cv2.addWeighted(img, 1 + amount, blurred, -amount, 0)
    return np.clip(sharp, 0, 255).astype(np.uint8)


def denoise(img: np.ndarray, h: int = 5) -> np.ndarray:
    # Fast, edge-preserving denoise; h~3..10 is typical
    return cv2.fastNlMeansDenoising(img, h=h, templateWindowSize=7, searchWindowSize=21)


def binarize(img: np.ndarray, method: str = "adaptive") -> np.ndarray:
    if method == "otsu":
        _thr, out = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return out
    # default adaptive mean threshold works well for uneven illumination
    return cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                 cv2.THRESH_BINARY, 35, 10)


def morph_cleanup(bin_img: np.ndarray) -> np.ndarray:
    # Remove small speckles and strengthen text strokes slightly
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, kernel_open, iterations=1)
    kernel_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    embold = cv2.dilate(cleaned, kernel_dil, iterations=1)
    return embold


def scale_image(img: np.ndarray, scale: float) -> np.ndarray:
    if abs(scale - 1.0) < 1e-3:
        return img
    h, w = img.shape[:2]
    nh, nw = int(round(h * scale)), int(round(w * scale))
    return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_CUBIC if scale > 1.0 else cv2.INTER_AREA)


def preprocess_for_ocr(img: np.ndarray, scale: float = 1.0, clip_limit: float = 2.0,
                       tile: int = 8, denoise_h: int = 5, sharpen: float = 0.5,
                       bin_method: str = "adaptive") -> Tuple[np.ndarray, np.ndarray]:
    # Contrast and denoise
    work = clahe_contrast(img, clip_limit=clip_limit, tile=tile)
    if denoise_h > 0:
        work = denoise(work, h=denoise_h)
    if sharpen > 0:
        work = unsharp_mask(work, sigma=1.0, amount=sharpen)
    work = scale_image(work, scale)
    # Binary for OCR
    bin_img = binarize(work, method=bin_method)
    bin_img = morph_cleanup(bin_img)
    return work, bin_img


def main():
    ap = argparse.ArgumentParser(description="Deskew and OCR-optimize page images (OpenCV; no column splitting)")
    ap.add_argument("input", help="Input PDF or image")
    ap.add_argument("--outdir", default="work/prep", help="Output directory for processed images")
    ap.add_argument("--dpi", type=int, default=400, help="DPI for PDF rendering")
    ap.add_argument("--scale", type=float, default=1.0, help="Optional scale factor after enhancement (e.g., 1.25)")
    ap.add_argument("--clip-limit", type=float, default=2.0, help="CLAHE clip limit (contrast)")
    ap.add_argument("--tile", type=int, default=8, help="CLAHE tile size (pixels)")
    ap.add_argument("--denoise-h", type=int, default=5, help="fastNlMeansDenoising h (0 disables)")
    ap.add_argument("--sharpen", type=float, default=0.5, help="Unsharp mask amount (0 disables)")
    ap.add_argument("--binarize", choices=["adaptive", "otsu"], default="adaptive", help="Binarization method")
    ap.add_argument("--deskew-method", choices=["auto", "hough", "lsd", "sweep"], default="auto", help="Deskew method (auto tries best-of and refines)")
    ap.add_argument("--max-angle", type=float, default=7.0, help="Maximum absolute skew angle to consider (degrees)")
    ap.add_argument("--debug", action="store_true", help="Emit debug overlay with deskew angle and content box")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    img, origin = load_image(args.input, dpi=args.dpi, tmpdir=args.outdir)
    if img is None:
        raise SystemExit("Failed to load image")
    img = auto_orient(img)
    img_dk, ang = deskew(img, method=args.deskew_method, max_angle=args.max_angle)

    # Trim to content box to reduce margins and improve OCR quality
    h, w = img_dk.shape[:2]
    bx, by, bw, bh = find_content_bbox(img_dk)
    roi = img_dk[by:by + bh, bx:bx + bw]

    # Preprocess
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
    p_full = os.path.join(args.outdir, f"{base}.deskew.png")
    p_gray = os.path.join(args.outdir, f"{base}.ocr.gray.png")
    p_bin = os.path.join(args.outdir, f"{base}.ocr.bin.png")

    cv2.imwrite(p_full, img_dk)
    cv2.imwrite(p_gray, gray_enh)
    cv2.imwrite(p_bin, bin_img)

    if args.debug:
        overlay = cv2.cvtColor(img_dk, cv2.COLOR_GRAY2BGR)
        cv2.putText(overlay, f"skew={ang:.2f} deg", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        p_dbg = os.path.join(args.outdir, f"{base}.debug.png")
        cv2.imwrite(p_dbg, overlay)

    print(f"Deskewed (angle={ang:.2f}°). Wrote: {p_full}, {p_gray}, {p_bin}")


if __name__ == "__main__":
    main()
