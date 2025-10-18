#!/usr/bin/env python3
"""
Automatic Image Deskewing and OCR Optimization Pipeline
Handles rotation detection and correction for historical document images.
"""

import cv2
import numpy as np
from pathlib import Path
import argparse
from typing import Tuple, Optional
import sys


class ImageDeskewer:
    """Advanced image deskewing for OCR optimization."""

    def __init__(self, debug=False):
        self.debug = debug

    def detect_rotation_angle(self, image: np.ndarray, method='combined') -> float:
        """
        Detect rotation angle using multiple methods.

        Args:
            image: Input image (grayscale or color)
            method: 'hough', 'contours', 'projection', or 'combined'

        Returns:
            Rotation angle in degrees (negative = clockwise, positive = counter-clockwise)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if method == 'combined':
            angles = []

            # Method 1: Hough Line Transform (best for clear text lines)
            angle_hough = self._detect_angle_hough(gray)
            if angle_hough is not None:
                angles.append(angle_hough)

            # Method 2: Contour-based (good for overall page orientation)
            angle_contour = self._detect_angle_contours(gray)
            if angle_contour is not None:
                angles.append(angle_contour)

            # Method 3: Projection profile (robust for text documents)
            angle_projection = self._detect_angle_projection(gray)
            if angle_projection is not None:
                angles.append(angle_projection)

            if not angles:
                return 0.0

            # Use median of detected angles for robustness
            return float(np.median(angles))

        elif method == 'hough':
            return self._detect_angle_hough(gray) or 0.0
        elif method == 'contours':
            return self._detect_angle_contours(gray) or 0.0
        elif method == 'projection':
            return self._detect_angle_projection(gray) or 0.0
        else:
            return 0.0

    def _detect_angle_hough(self, gray: np.ndarray) -> Optional[float]:
        """Detect angle using Hough Line Transform."""
        try:
            # Apply adaptive threshold to get better edges
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 15, 10
            )

            # Detect edges
            edges = cv2.Canny(thresh, 50, 150, apertureSize=3)

            # Detect lines using Hough Transform
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180, threshold=100,
                minLineLength=100, maxLineGap=10
            )

            if lines is None or len(lines) == 0:
                return None

            # Calculate angles for all lines
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))

                # Normalize angle to [-45, 45] range
                if angle < -45:
                    angle += 90
                elif angle > 45:
                    angle -= 90

                angles.append(angle)

            if self.debug:
                print(f"  Hough: Found {len(angles)} lines")
                print(f"  Hough angles range: {min(angles):.2f}° to {max(angles):.2f}°")

            # Return median angle (robust to outliers)
            return float(np.median(angles))

        except Exception as e:
            if self.debug:
                print(f"  Hough detection failed: {e}")
            return None

    def _detect_angle_contours(self, gray: np.ndarray) -> Optional[float]:
        """Detect angle using minimum area rectangle of largest contours."""
        try:
            # Threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return None

            # Get largest contours (top 20%)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            num_contours = max(1, int(len(contours) * 0.2))
            top_contours = contours[:num_contours]

            # Calculate angles from minimum area rectangles
            angles = []
            for contour in top_contours:
                if cv2.contourArea(contour) < 100:  # Skip tiny contours
                    continue

                rect = cv2.minAreaRect(contour)
                angle = rect[2]

                # Normalize angle
                if angle < -45:
                    angle += 90
                elif angle > 45:
                    angle -= 90

                angles.append(angle)

            if not angles:
                return None

            if self.debug:
                print(f"  Contour: Analyzed {len(angles)} contours")
                print(f"  Contour angles range: {min(angles):.2f}° to {max(angles):.2f}°")

            return float(np.median(angles))

        except Exception as e:
            if self.debug:
                print(f"  Contour detection failed: {e}")
            return None

    def _detect_angle_projection(self, gray: np.ndarray) -> Optional[float]:
        """Detect angle using projection profile method."""
        try:
            # Threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Try different angles and find one with maximum variance in row sums
            # (horizontal text lines will have high variance in vertical projection)
            test_angles = np.arange(-10, 10, 0.5)  # Test -10 to +10 degrees
            variances = []

            h, w = thresh.shape
            center = (w // 2, h // 2)

            for angle in test_angles:
                # Rotate image
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC)

                # Calculate variance of horizontal projection
                projection = np.sum(rotated, axis=1)
                variance = np.var(projection)
                variances.append(variance)

            # Find angle with maximum variance
            best_idx = np.argmax(variances)
            best_angle = test_angles[best_idx]

            if self.debug:
                print(f"  Projection: Best angle {best_angle:.2f}° (variance: {variances[best_idx]:.0f})")

            return float(best_angle)

        except Exception as e:
            if self.debug:
                print(f"  Projection detection failed: {e}")
            return None

    def rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate image by given angle.

        Args:
            image: Input image
            angle: Rotation angle in degrees

        Returns:
            Rotated image
        """
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        # Get rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Calculate new image dimensions to prevent cropping
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # Adjust rotation matrix for new dimensions
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        # Rotate with white background
        rotated = cv2.warpAffine(
            image, M, (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )

        return rotated

    def enhance_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """
        Apply additional enhancements for OCR.

        Args:
            image: Input image

        Returns:
            Enhanced image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Increase contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Slight Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

        # Adaptive threshold (optional - can produce binary output)
        # thresh = cv2.adaptiveThreshold(
        #     blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        #     cv2.THRESH_BINARY, 11, 2
        # )

        return blurred

    def process_image(self, image: np.ndarray, method='combined',
                     enhance=True) -> Tuple[np.ndarray, float]:
        """
        Complete processing pipeline: detect rotation, correct, and enhance.

        Args:
            image: Input image
            method: Rotation detection method
            enhance: Whether to apply OCR enhancements

        Returns:
            Tuple of (processed_image, rotation_angle)
        """
        if self.debug:
            print("Detecting rotation angle...")

        # Detect rotation
        angle = self.detect_rotation_angle(image, method=method)

        if self.debug:
            print(f"Detected angle: {angle:.2f}°")

        # Rotate if needed (only if angle is significant)
        if abs(angle) > 0.1:
            if self.debug:
                print(f"Rotating image by {angle:.2f}°...")
            rotated = self.rotate_image(image, angle)
        else:
            rotated = image.copy()

        # Enhance for OCR
        if enhance:
            if self.debug:
                print("Enhancing image for OCR...")
            result = self.enhance_for_ocr(rotated)
        else:
            result = rotated

        return result, angle


def main():
    parser = argparse.ArgumentParser(
        description='Automatic image deskewing and OCR optimization'
    )
    parser.add_argument('input', type=str, help='Input image file or directory')
    parser.add_argument('-o', '--output', type=str, help='Output file or directory')
    parser.add_argument('-m', '--method', type=str,
                       choices=['hough', 'contours', 'projection', 'combined'],
                       default='combined', help='Rotation detection method')
    parser.add_argument('--no-enhance', action='store_true',
                       help='Skip OCR enhancement step')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Print debug information')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Process directory recursively')

    args = parser.parse_args()

    # Initialize deskewer
    deskewer = ImageDeskewer(debug=args.debug)

    # Process input
    input_path = Path(args.input)

    if input_path.is_file():
        # Single file
        if args.debug:
            print(f"\nProcessing: {input_path}")

        # Read image
        img = cv2.imread(str(input_path))
        if img is None:
            print(f"Error: Could not read image {input_path}")
            sys.exit(1)

        # Process
        result, angle = deskewer.process_image(
            img, method=args.method, enhance=not args.no_enhance
        )

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.parent / f"{input_path.stem}_deskewed{input_path.suffix}"

        # Save result
        cv2.imwrite(str(output_path), result)
        print(f"Saved: {output_path} (rotated {angle:.2f}°)")

    elif input_path.is_dir():
        # Directory
        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = input_path / "deskewed"
            output_dir.mkdir(exist_ok=True)

        # Find images
        patterns = ['*.png', '*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.PNG']
        image_files = []

        for pattern in patterns:
            if args.recursive:
                image_files.extend(input_path.rglob(pattern))
            else:
                image_files.extend(input_path.glob(pattern))

        if not image_files:
            print(f"No image files found in {input_path}")
            sys.exit(1)

        print(f"Found {len(image_files)} images to process\n")

        # Process each image
        for i, img_path in enumerate(image_files, 1):
            if args.debug:
                print(f"\n[{i}/{len(image_files)}] Processing: {img_path.name}")
            else:
                print(f"[{i}/{len(image_files)}] {img_path.name}...", end=' ', flush=True)

            # Read image
            img = cv2.imread(str(img_path))
            if img is None:
                print(f"Skipped (could not read)")
                continue

            # Process
            result, angle = deskewer.process_image(
                img, method=args.method, enhance=not args.no_enhance
            )

            # Determine output path (preserve relative structure if recursive)
            if args.recursive:
                rel_path = img_path.relative_to(input_path)
                out_path = output_dir / rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                out_path = output_dir / img_path.name

            # Save result
            cv2.imwrite(str(out_path), result)

            if not args.debug:
                print(f"rotated {angle:.2f}° → {out_path.name}")

        print(f"\nAll images saved to: {output_dir}")

    else:
        print(f"Error: {input_path} is not a file or directory")
        sys.exit(1)


if __name__ == '__main__':
    main()
