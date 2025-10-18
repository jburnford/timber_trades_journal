#!/usr/bin/env python3
"""
PDF to OCR-optimized image pipeline.
Extracts pages from PDFs, detects rotation, corrects alignment, and enhances for OCR.
"""

import cv2
import numpy as np
from pathlib import Path
import argparse
import sys
from pdf2image import convert_from_path
from PIL import Image

# Import our deskewer
from auto_deskew_ocr import ImageDeskewer


def pdf_to_images(pdf_path: Path, dpi: int = 300) -> list:
    """
    Convert PDF pages to PIL images.

    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for conversion (default 300 DPI)

    Returns:
        List of PIL Image objects
    """
    try:
        images = convert_from_path(str(pdf_path), dpi=dpi)
        return images
    except Exception as e:
        print(f"Error converting PDF {pdf_path}: {e}")
        return []


def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV format."""
    # Convert PIL RGB to numpy array, then BGR for OpenCV
    rgb_array = np.array(pil_image)
    # Handle grayscale images
    if len(rgb_array.shape) == 2:
        return rgb_array
    # Convert RGB to BGR
    return rgb_array[:, :, ::-1].copy()


def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    """Convert OpenCV image to PIL format."""
    # Handle grayscale images
    if len(cv2_image.shape) == 2:
        return Image.fromarray(cv2_image)
    # Convert BGR to RGB
    return Image.fromarray(cv2_image[:, :, ::-1])


def process_pdf(pdf_path: Path, output_dir: Path, dpi: int = 300,
               method: str = 'combined', enhance: bool = True,
               debug: bool = False) -> list:
    """
    Process a PDF file: extract pages, deskew, and optimize for OCR.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save processed images
        dpi: Resolution for PDF conversion
        method: Rotation detection method
        enhance: Whether to apply OCR enhancements
        debug: Print debug information

    Returns:
        List of output file paths
    """
    if debug:
        print(f"\n{'='*70}")
        print(f"Processing PDF: {pdf_path.name}")
        print(f"{'='*70}")

    # Convert PDF to images
    if debug:
        print(f"Converting PDF to images (DPI: {dpi})...")

    pil_images = pdf_to_images(pdf_path, dpi=dpi)

    if not pil_images:
        print(f"Failed to extract images from {pdf_path}")
        return []

    if debug:
        print(f"Extracted {len(pil_images)} page(s)")

    # Initialize deskewer
    deskewer = ImageDeskewer(debug=debug)

    # Process each page
    output_paths = []
    pdf_stem = pdf_path.stem

    for i, pil_img in enumerate(pil_images, 1):
        if debug:
            print(f"\n--- Page {i}/{len(pil_images)} ---")

        # Convert to OpenCV format
        cv2_img = pil_to_cv2(pil_img)

        # Process: detect rotation, correct, enhance
        processed, angle = deskewer.process_image(
            cv2_img, method=method, enhance=enhance
        )

        # Generate output filename
        if len(pil_images) == 1:
            output_name = f"{pdf_stem}.png"
        else:
            output_name = f"{pdf_stem}_p{i:03d}.png"

        output_path = output_dir / output_name

        # Save processed image
        cv2.imwrite(str(output_path), processed)

        if not debug:
            print(f"  [{i}/{len(pil_images)}] {output_name} (rotated {angle:+.2f}°)")

        output_paths.append(output_path)

    return output_paths


def main():
    parser = argparse.ArgumentParser(
        description='Extract and optimize PDF pages for OCR'
    )
    parser.add_argument('input', type=str,
                       help='Input PDF file or directory of PDFs')
    parser.add_argument('-o', '--output', type=str,
                       help='Output directory (default: input_dir/ocr_ready)')
    parser.add_argument('--dpi', type=int, default=300,
                       help='DPI for PDF conversion (default: 300)')
    parser.add_argument('-m', '--method', type=str,
                       choices=['hough', 'contours', 'projection', 'combined'],
                       default='combined',
                       help='Rotation detection method (default: combined)')
    parser.add_argument('--no-enhance', action='store_true',
                       help='Skip OCR enhancement step')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Process directory recursively')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Print detailed debug information')
    parser.add_argument('--limit', type=int,
                       help='Maximum number of PDFs to process (for testing)')

    args = parser.parse_args()

    # Process input
    input_path = Path(args.input)

    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        # Single PDF file
        if args.output:
            output_dir = Path(args.output)
        else:
            output_dir = input_path.parent / "ocr_ready"

        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processing: {input_path.name}")
        output_paths = process_pdf(
            input_path, output_dir, dpi=args.dpi,
            method=args.method, enhance=not args.no_enhance,
            debug=args.debug
        )

        print(f"\nSaved {len(output_paths)} image(s) to: {output_dir}")

    elif input_path.is_dir():
        # Directory of PDFs
        if args.output:
            output_dir = Path(args.output)
        else:
            output_dir = input_path / "ocr_ready"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all PDFs
        if args.recursive:
            pdf_files = list(input_path.rglob("*.pdf"))
            pdf_files.extend(list(input_path.rglob("*.PDF")))
        else:
            pdf_files = list(input_path.glob("*.pdf"))
            pdf_files.extend(list(input_path.glob("*.PDF")))

        if not pdf_files:
            print(f"No PDF files found in {input_path}")
            sys.exit(1)

        # Apply limit if specified
        if args.limit:
            pdf_files = pdf_files[:args.limit]
            print(f"Processing first {len(pdf_files)} PDF(s) (limit applied)\n")
        else:
            print(f"Found {len(pdf_files)} PDF file(s) to process\n")

        # Process each PDF
        total_images = 0
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] {pdf_path.name}")

            # Create subdirectory for multi-page PDFs if recursive
            if args.recursive:
                rel_path = pdf_path.parent.relative_to(input_path)
                pdf_output_dir = output_dir / rel_path
                pdf_output_dir.mkdir(parents=True, exist_ok=True)
            else:
                pdf_output_dir = output_dir

            output_paths = process_pdf(
                pdf_path, pdf_output_dir, dpi=args.dpi,
                method=args.method, enhance=not args.no_enhance,
                debug=args.debug
            )

            total_images += len(output_paths)

        print(f"\n{'='*70}")
        print(f"COMPLETE: Processed {len(pdf_files)} PDF(s)")
        print(f"Generated {total_images} OCR-ready image(s)")
        print(f"Output directory: {output_dir}")
        print(f"{'='*70}")

    else:
        print(f"Error: {input_path} must be a PDF file or directory")
        sys.exit(1)


if __name__ == '__main__':
    main()
