#!/usr/bin/env python3
"""
Test script for image deskewing on sample images.
"""

import cv2
import sys
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auto_deskew_ocr import ImageDeskewer


def test_on_samples():
    """Test deskewing on sample images."""

    # Test images
    base_path = Path("/home/jic823/TTJ Forest of Numbers/work/pages")
    test_images = [
        "18790830p.156-1.png",
        "18790607p.57-2.png",
        "18860102p8-9-1.png",
    ]

    # Output directory
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/work/deskew_test")
    output_dir.mkdir(exist_ok=True)

    # Initialize deskewer
    deskewer = ImageDeskewer(debug=True)

    print("=" * 70)
    print("TESTING IMAGE DESKEWING PIPELINE")
    print("=" * 70)

    for img_name in test_images:
        img_path = base_path / img_name

        if not img_path.exists():
            print(f"\nSkipping {img_name} (not found)")
            continue

        print(f"\n{'=' * 70}")
        print(f"Processing: {img_name}")
        print(f"{'=' * 70}")

        # Read image
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"Error: Could not read {img_path}")
            continue

        print(f"Image size: {img.shape[1]} x {img.shape[0]} pixels")

        # Test each method individually
        methods = ['hough', 'contours', 'projection', 'combined']

        for method in methods:
            print(f"\n--- Method: {method.upper()} ---")

            # Process
            result, angle = deskewer.process_image(img, method=method, enhance=True)

            # Save result
            output_name = f"{Path(img_name).stem}_{method}{Path(img_name).suffix}"
            output_path = output_dir / output_name
            cv2.imwrite(str(output_path), result)

            print(f"Saved: {output_name}")

        print(f"\n{'=' * 70}")

    print(f"\n\nAll test results saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Visually inspect the results in the deskew_test directory")
    print("2. Choose the best method (or use 'combined' for automatic selection)")
    print("3. Run on full directory with: python tools/auto_deskew_ocr.py work/pages -o work/pages_deskewed")


if __name__ == '__main__':
    test_on_samples()
