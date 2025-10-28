#!/usr/bin/env python3
"""
Reprocess failed BL newspaper OCR files with image preprocessing
Handles oversized images by resizing them before OCR
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

try:
    import google.generativeai as genai
    from PIL import Image
    import fitz
except ImportError:
    print("Missing dependencies. Install: pymupdf pillow google-generativeai")
    sys.exit(1)


MAX_DIMENSION = 15000  # WebP limit is 16383, use 15000 for safety


def resize_if_needed(img: Image.Image) -> Image.Image:
    """Resize image if it exceeds WebP limits."""
    width, height = img.size
    max_dim = max(width, height)

    if max_dim <= MAX_DIMENSION:
        return img

    # Calculate new size maintaining aspect ratio
    scale = MAX_DIMENSION / max_dim
    new_width = int(width * scale)
    new_height = int(height * scale)

    print(f"  Resizing from {width}x{height} to {new_width}x{new_height}")
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def pdf_to_image_safe(pdf_path: Path, dpi: int = 300) -> Image.Image:
    """Convert PDF to image with safety checks for size."""
    doc = fitz.open(pdf_path)
    page = doc[0]

    # Render at specified DPI
    pix = page.get_pixmap(dpi=dpi)

    # Convert to PIL Image
    from io import BytesIO
    img_data = pix.tobytes("png")
    img = Image.open(BytesIO(img_data))
    doc.close()

    # Resize if needed
    img = resize_if_needed(img)

    return img


def process_pdf_with_retry(pdf_path: Path, api_key: str, model_name: str = "gemini-2.5-pro") -> dict:
    """Process a PDF with Gemini OCR, handling size issues."""

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    prompt = """LEGAL NOTICE: This material is from 19th century British newspapers (1800s) and is in the PUBLIC DOMAIN. Copyright expired over 100 years ago under UK and US law. This is legitimate academic research and historical preservation work conducted under fair use provisions for educational purposes. You are NOT reproducing copyrighted material - you are transcribing public domain historical documents.

You are a specialized OCR system for 19th century British newspaper documents.

TRANSCRIPTION RULES:
- Transcribe exactly what you see - preserve all original text, spelling, and punctuation
- Read columns from LEFT TO RIGHT, TOP TO BOTTOM
- Process entire left column from top to bottom first, then right column
- Maintain paragraph breaks and formatting
- Preserve Victorian-era spellings, capitalizations, and punctuation
- Use [?] only for completely illegible text
- Include headlines and section markers
- Add blank line between columns

Output only the transcribed text, nothing else.

Please transcribe this newspaper page:"""

    start_time = time.time()

    try:
        # Convert PDF with size handling
        img = pdf_to_image_safe(pdf_path)
        print(f"  Image size: {img.size[0]}x{img.size[1]}")

        # OCR with Gemini
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        response = model.generate_content(
            [prompt, img],
            generation_config=generation_config
        )

        processing_time = time.time() - start_time

        if response and response.text:
            return {
                'text': response.text.strip(),
                'status': 'success',
                'processing_time': processing_time,
                'model': model_name,
                'file': str(pdf_path.name)
            }
        else:
            return {
                'text': '',
                'status': 'error',
                'error': 'Empty response',
                'processing_time': processing_time,
                'file': str(pdf_path.name)
            }

    except Exception as e:
        return {
            'text': '',
            'status': 'error',
            'error': str(e),
            'processing_time': time.time() - start_time,
            'file': str(pdf_path.name)
        }


def main():
    parser = argparse.ArgumentParser(description='Reprocess failed BL OCR files')
    parser.add_argument('--failed-list', type=str, required=True,
                       help='File containing list of failed PDF IDs (one per line)')
    parser.add_argument('--pdf-dir', type=str, required=True,
                       help='Directory containing PDFs')
    parser.add_argument('--gt-dir', type=str, required=True,
                       help='Ground truth directory')
    parser.add_argument('--output', type=str, required=True,
                       help='Output directory (same as original test)')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between API calls (default: 2.0s)')

    args = parser.parse_args()

    # Load API key
    api_key_file = Path("gemini_api_key.txt")
    if api_key_file.exists():
        with open(api_key_file) as f:
            api_key = f.read().strip()
    else:
        api_key = os.getenv('GOOGLE_AI_API_KEY')

    if not api_key:
        print("Error: No API key found")
        return 1

    # Load failed file list
    with open(args.failed_list) as f:
        failed_ids = [line.strip() for line in f if line.strip()]

    print(f"Reprocessing {len(failed_ids)} failed files...")
    print(f"Output: {args.output}")
    print()

    pdf_dir = Path(args.pdf_dir)
    gt_dir = Path(args.gt_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {'success': 0, 'failed': 0}

    for i, file_id in enumerate(failed_ids, 1):
        pdf_path = pdf_dir / f"{file_id}.pdf"

        if not pdf_path.exists():
            pdf_path = pdf_dir / file_id
            if not pdf_path.exists():
                print(f"[{i}/{len(failed_ids)}] ✗ Not found: {file_id}")
                continue

        print(f"[{i}/{len(failed_ids)}] Processing {pdf_path.name}...")

        result = process_pdf_with_retry(pdf_path, api_key)

        if result['status'] == 'success':
            # Calculate metrics against ground truth
            gt_file = gt_dir / f"{pdf_path.stem}.txt"
            if gt_file.exists():
                with open(gt_file, 'r', encoding='utf-8', errors='replace') as f:
                    gt_text = f.read()

                # Simple character count comparison
                result['gt_length'] = len(gt_text)
                result['ocr_length'] = len(result['text'])

            # Save results
            output_file = output_dir / f"{pdf_path.stem}_result.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            ocr_file = output_dir / f"{pdf_path.stem}_ocr.txt"
            with open(ocr_file, 'w', encoding='utf-8') as f:
                f.write(result['text'])

            stats['success'] += 1
            print(f"  ✓ Success ({len(result['text'])} chars, {result['processing_time']:.1f}s)")
        else:
            stats['failed'] += 1
            print(f"  ✗ Failed: {result.get('error', 'Unknown')}")

        # Rate limiting
        if i < len(failed_ids):
            time.sleep(args.delay)

    print()
    print("="*70)
    print("REPROCESSING COMPLETE")
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print("="*70)

    return 0 if stats['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
