#!/usr/bin/env python3
"""
Gemini Pro 2.5 OCR Processor for Timber Trades Journal Images
Processes OCR-ready images and extracts text using Google's Gemini API.
"""

import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import argparse

try:
    import google.generativeai as genai
    from PIL import Image
except ImportError:
    print("Missing dependencies. Please install:")
    print("  pip install --break-system-packages google-generativeai pillow")
    exit(1)


class GeminiOCRProcessor:
    """Process images with Gemini Pro Vision for OCR."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp",
                 debug: bool = False):
        """
        Initialize Gemini OCR processor.

        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
            debug: Enable debug logging
        """
        self.api_key = api_key
        self.model_name = model_name
        self.debug = debug

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

        # Historical document OCR prompt
        self.system_prompt = """You are a specialized OCR system for 19th century historical documents. Your task is to transcribe each sentence on a new line from timber trade journal pages.

IMPORTANT GUIDELINES:
- You are assisting historians studying the global timber trade in the 19th century
- Accuracy is essential - transcribe exactly what you see
- Do NOT correct abbreviations (e.g., "Christiania" not "Oslo", "£" not "pounds")
- Do NOT correct historical spellings
- Preserve original punctuation and formatting
- Each sentence should be on a new line
- If text is unclear or unreadable, use [?] to indicate uncertainty
- Preserve numbers, dates, and measurements exactly as written
- Maintain column structure where present (use spacing or tabs)

Output only the transcribed text, nothing else."""

    def process_image(self, image_path: Path) -> Optional[Dict]:
        """
        Process a single image with Gemini OCR.

        Args:
            image_path: Path to image file

        Returns:
            Dict with 'text', 'status', 'processing_time', 'error' or None if failed
        """
        if not image_path.exists():
            logging.error(f"Image not found: {image_path}")
            return None

        try:
            start_time = time.time()

            # Load image
            img = Image.open(image_path)

            if self.debug:
                logging.debug(f"Processing {image_path.name} ({img.size[0]}x{img.size[1]})")

            # Create prompt
            prompt = f"{self.system_prompt}\n\nPlease transcribe this timber trade journal page:"

            # Send to Gemini
            response = self.model.generate_content([prompt, img])

            processing_time = time.time() - start_time

            # Extract text
            if response and response.text:
                result = {
                    'text': response.text.strip(),
                    'status': 'success',
                    'processing_time': processing_time,
                    'model': self.model_name,
                    'image': str(image_path.name)
                }

                if self.debug:
                    logging.debug(f"Processed in {processing_time:.2f}s, {len(result['text'])} chars")

                return result
            else:
                logging.error(f"Empty response from Gemini for {image_path.name}")
                return {
                    'text': '',
                    'status': 'error',
                    'error': 'Empty response from API',
                    'processing_time': processing_time,
                    'image': str(image_path.name)
                }

        except Exception as e:
            logging.error(f"Error processing {image_path.name}: {e}")
            return {
                'text': '',
                'status': 'error',
                'error': str(e),
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0,
                'image': str(image_path.name)
            }

    def process_batch(self, image_paths: List[Path], output_dir: Path,
                     delay: float = 1.0) -> Dict:
        """
        Process a batch of images.

        Args:
            image_paths: List of image file paths
            output_dir: Directory to save OCR results
            delay: Delay between API calls (rate limiting)

        Returns:
            Dict with processing statistics
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        stats = {
            'total': len(image_paths),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_time': 0
        }

        for i, img_path in enumerate(image_paths, 1):
            # Check if already processed
            output_file = output_dir / f"{img_path.stem}.json"

            if output_file.exists():
                logging.info(f"[{i}/{stats['total']}] Skipping {img_path.name} (already processed)")
                stats['skipped'] += 1
                continue

            logging.info(f"[{i}/{stats['total']}] Processing {img_path.name}...")

            # Process image
            result = self.process_image(img_path)

            if result:
                # Save result
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                # Also save plain text
                text_file = output_dir / f"{img_path.stem}.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(result['text'])

                if result['status'] == 'success':
                    stats['success'] += 1
                    logging.info(f"  ✓ {len(result['text'])} chars, {result['processing_time']:.2f}s")
                else:
                    stats['failed'] += 1
                    logging.warning(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

                stats['total_time'] += result['processing_time']
            else:
                stats['failed'] += 1
                logging.error(f"  ✗ Failed to process {img_path.name}")

            # Rate limiting delay (except for last image)
            if i < stats['total']:
                time.sleep(delay)

        return stats


def load_api_key(key_file: Optional[Path] = None) -> Optional[str]:
    """Load Google AI API key from environment or file."""
    # Try environment variable first
    api_key = os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key

    # Try key file
    if key_file and key_file.exists():
        with open(key_file, 'r') as f:
            return f.read().strip()

    # Try default location
    default_key_file = Path("gemini_api_key.txt")
    if default_key_file.exists():
        with open(default_key_file, 'r') as f:
            return f.read().strip()

    return None


def find_images(input_path: Path, recursive: bool = False) -> List[Path]:
    """Find all image files in a directory."""
    patterns = ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']
    images = []

    if input_path.is_file():
        return [input_path]

    for pattern in patterns:
        if recursive:
            images.extend(input_path.rglob(pattern))
        else:
            images.extend(input_path.glob(pattern))

    return sorted(images)


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"gemini_ocr_{timestamp}.log"

    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return log_file


def main():
    parser = argparse.ArgumentParser(
        description='Process images with Gemini Pro Vision for OCR'
    )
    parser.add_argument('input', type=str,
                       help='Input image file or directory')
    parser.add_argument('-o', '--output', type=str, required=True,
                       help='Output directory for OCR results')
    parser.add_argument('-k', '--api-key-file', type=str,
                       help='Path to API key file (default: gemini_api_key.txt)')
    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-flash-exp',
                       help='Gemini model to use (default: gemini-2.0-flash-exp)')
    parser.add_argument('-r', '--recursive', action='store_true',
                       help='Process directories recursively')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between API calls in seconds (default: 1.0)')
    parser.add_argument('--limit', type=int,
                       help='Maximum number of images to process (for testing)')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Enable debug logging')

    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging(args.debug)

    logging.info("=" * 70)
    logging.info("GEMINI OCR PROCESSOR FOR TIMBER TRADES JOURNAL")
    logging.info("=" * 70)
    logging.info(f"Log file: {log_file}")

    # Load API key
    api_key_file = Path(args.api_key_file) if args.api_key_file else None
    api_key = load_api_key(api_key_file)

    if not api_key:
        logging.error("No API key found!")
        logging.error("Set GOOGLE_AI_API_KEY environment variable or create gemini_api_key.txt")
        return 1

    logging.info(f"✓ API key loaded")
    logging.info(f"✓ Model: {args.model}")

    # Find images
    input_path = Path(args.input)
    images = find_images(input_path, args.recursive)

    if not images:
        logging.error(f"No images found in {input_path}")
        return 1

    # Apply limit if specified
    if args.limit:
        images = images[:args.limit]
        logging.info(f"Processing first {len(images)} images (limit applied)")
    else:
        logging.info(f"Found {len(images)} images to process")

    # Initialize processor
    processor = GeminiOCRProcessor(api_key, model_name=args.model, debug=args.debug)

    # Create output directory
    output_dir = Path(args.output)

    # Process images
    logging.info("-" * 70)
    start_time = time.time()

    stats = processor.process_batch(images, output_dir, delay=args.delay)

    total_time = time.time() - start_time

    # Print summary
    logging.info("=" * 70)
    logging.info("PROCESSING COMPLETE")
    logging.info("=" * 70)
    logging.info(f"Total images: {stats['total']}")
    logging.info(f"  Success: {stats['success']}")
    logging.info(f"  Failed: {stats['failed']}")
    logging.info(f"  Skipped: {stats['skipped']}")
    logging.info(f"Processing time: {stats['total_time']:.1f}s")
    logging.info(f"Total runtime: {total_time:.1f}s ({total_time/60:.1f} min)")
    if stats['success'] > 0:
        logging.info(f"Average: {stats['total_time']/stats['success']:.2f}s per image")
    logging.info(f"Output directory: {output_dir}")
    logging.info(f"Log file: {log_file}")
    logging.info("=" * 70)

    return 0 if stats['failed'] == 0 else 1


if __name__ == '__main__':
    exit(main())
