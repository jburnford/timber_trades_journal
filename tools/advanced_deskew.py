#!/usr/bin/env python3
"""
Advanced deskewing with perspective correction for phone photos of documents.
"""

import cv2
import numpy as np
from pathlib import Path
import argparse
from typing import Tuple, Optional


class AdvancedDeskewer:
    """Advanced deskewing with perspective correction for phone camera images."""

    def __init__(self, debug=False):
        self.debug = debug

    def detect_document_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect the four corners of a document page in an image.

        Returns:
            4x2 array of corner coordinates [top-left, top-right, bottom-right, bottom-left]
            or None if detection fails
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Dilate edges to close gaps
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Find the largest contour (likely the page)
        largest_contour = max(contours, key=cv2.contourArea)

        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)

        # We want a quadrilateral (4 corners)
        if len(approx) == 4:
            corners = approx.reshape(4, 2)
            return self._order_corners(corners)

        # If not 4 corners, use minimum area rectangle
        rect = cv2.minAreaRect(largest_contour)
        box = cv2.boxPoints(rect)
        return self._order_corners(box)

    def _order_corners(self, corners: np.ndarray) -> np.ndarray:
        """
        Order corners as: [top-left, top-right, bottom-right, bottom-left]
        """
        # Sort by y-coordinate
        sorted_by_y = corners[np.argsort(corners[:, 1])]

        # Top two points
        top = sorted_by_y[:2]
        # Bottom two points
        bottom = sorted_by_y[2:]

        # Sort top points by x (left to right)
        top_left, top_right = top[np.argsort(top[:, 0])]

        # Sort bottom points by x (left to right)
        bottom_left, bottom_right = bottom[np.argsort(bottom[:, 0])]

        return np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)

    def apply_perspective_correction(self, image: np.ndarray,
                                    corners: np.ndarray) -> np.ndarray:
        """
        Apply perspective transform to get a top-down view of the document.
        """
        # Calculate the width and height of the corrected document
        width_top = np.linalg.norm(corners[1] - corners[0])
        width_bottom = np.linalg.norm(corners[2] - corners[3])
        max_width = int(max(width_top, width_bottom))

        height_left = np.linalg.norm(corners[3] - corners[0])
        height_right = np.linalg.norm(corners[2] - corners[1])
        max_height = int(max(height_left, height_right))

        # Destination points (rectangle)
        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)

        # Calculate perspective transform matrix
        M = cv2.getPerspectiveTransform(corners, dst)

        # Apply transform
        warped = cv2.warpPerspective(image, M, (max_width, max_height))

        return warped

    def auto_correct_perspective(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Automatically detect and correct perspective distortion.

        Returns:
            (corrected_image, correction_applied)
        """
        corners = self.detect_document_corners(image)

        if corners is None:
            if self.debug:
                print("  Perspective: Could not detect document corners")
            return image, False

        # Check if perspective correction is needed
        # Calculate the aspect ratio and skew
        width_top = np.linalg.norm(corners[1] - corners[0])
        width_bottom = np.linalg.norm(corners[2] - corners[3])
        width_ratio = min(width_top, width_bottom) / max(width_top, width_bottom)

        height_left = np.linalg.norm(corners[3] - corners[0])
        height_right = np.linalg.norm(corners[2] - corners[1])
        height_ratio = min(height_left, height_right) / max(height_left, height_right)

        if self.debug:
            print(f"  Perspective: Width ratio: {width_ratio:.3f}, Height ratio: {height_ratio:.3f}")

        # If ratios are close to 1.0, perspective is already good
        if width_ratio > 0.95 and height_ratio > 0.95:
            if self.debug:
                print("  Perspective: No significant distortion detected")
            return image, False

        # Apply perspective correction
        if self.debug:
            print("  Perspective: Applying correction")

        corrected = self.apply_perspective_correction(image, corners)
        return corrected, True

    def remove_borders(self, image: np.ndarray, border_percent: float = 2.0) -> np.ndarray:
        """
        Remove a percentage of border from all sides.
        Useful for removing dark edges from phone photos.
        """
        h, w = image.shape[:2]
        border_h = int(h * border_percent / 100)
        border_w = int(w * border_percent / 100)

        return image[border_h:h-border_h, border_w:w-border_w]

    def process_image(self, image: np.ndarray,
                     apply_perspective: bool = True,
                     remove_border: bool = True) -> np.ndarray:
        """
        Complete advanced processing pipeline.
        """
        result = image.copy()

        # Remove borders if requested
        if remove_border:
            if self.debug:
                print("Removing borders...")
            result = self.remove_borders(result)

        # Apply perspective correction if requested
        if apply_perspective:
            if self.debug:
                print("Detecting perspective...")
            result, corrected = self.auto_correct_perspective(result)

        return result


def main():
    parser = argparse.ArgumentParser(
        description='Advanced deskewing with perspective correction'
    )
    parser.add_argument('input', type=str, help='Input image file or directory')
    parser.add_argument('-o', '--output', type=str, help='Output file or directory')
    parser.add_argument('--no-perspective', action='store_true',
                       help='Skip perspective correction')
    parser.add_argument('--no-border-removal', action='store_true',
                       help='Skip border removal')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Print debug information')

    args = parser.parse_args()

    # Initialize processor
    processor = AdvancedDeskewer(debug=args.debug)

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
            return

        # Process
        result = processor.process_image(
            img,
            apply_perspective=not args.no_perspective,
            remove_border=not args.no_border_removal
        )

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.parent / f"{input_path.stem}_corrected{input_path.suffix}"

        # Save result
        cv2.imwrite(str(output_path), result)
        print(f"Saved: {output_path}")

    elif input_path.is_dir():
        # Directory
        if args.output:
            output_dir = Path(args.output)
        else:
            output_dir = input_path / "corrected"

        output_dir.mkdir(exist_ok=True)

        # Find images
        patterns = ['*.png', '*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.PNG']
        image_files = []
        for pattern in patterns:
            image_files.extend(input_path.glob(pattern))

        if not image_files:
            print(f"No image files found in {input_path}")
            return

        print(f"Found {len(image_files)} images to process\n")

        # Process each image
        for i, img_path in enumerate(image_files, 1):
            print(f"[{i}/{len(image_files)}] {img_path.name}...", end=' ', flush=True)

            # Read image
            img = cv2.imread(str(img_path))
            if img is None:
                print("Skipped (could not read)")
                continue

            # Process
            result = processor.process_image(
                img,
                apply_perspective=not args.no_perspective,
                remove_border=not args.no_border_removal
            )

            # Save result
            out_path = output_dir / img_path.name
            cv2.imwrite(str(out_path), result)
            print(f"Done")

        print(f"\nAll images saved to: {output_dir}")


if __name__ == '__main__':
    main()
