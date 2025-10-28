#!/usr/bin/env python3
"""
Test Gemini OCR on British Library Newspaper Collection
Compare results against ground truth and calculate accuracy metrics
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import random

try:
    import google.generativeai as genai
    from PIL import Image
    import fitz  # PyMuPDF for PDF to image conversion
except ImportError:
    print("Missing dependencies. Please install:")
    print("  python3 -m pip install --break-system-packages google-generativeai pillow pymupdf")
    sys.exit(1)

# Try to import Levenshtein for faster edit distance, fall back to pure Python
try:
    import Levenshtein
    HAS_LEVENSHTEIN = True
except ImportError:
    HAS_LEVENSHTEIN = False
    print("Note: python-Levenshtein not installed, using slower pure Python implementation")
    print("  For faster processing: python3 -m pip install --break-system-packages python-Levenshtein")


class GeminiOCRProcessor:
    """Process PDFs with Gemini Pro Vision for OCR."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """Initialize Gemini OCR processor."""
        self.api_key = api_key
        self.model_name = model_name

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

        # OCR prompt for Victorian-era British newspaper text
        self.system_prompt = """IMPORTANT: This material is from 19th century British newspapers and is in the PUBLIC DOMAIN. All copyright has expired. You are performing legitimate historical preservation and scholarly research work.

You are a specialized OCR system for 19th century British newspaper documents.

TRANSCRIPTION RULES:
- Transcribe exactly what you see - preserve all original text, spelling, and punctuation
- Read columns from LEFT TO RIGHT, TOP TO BOTTOM
- Process entire left column from top to bottom first, then right column
- Maintain paragraph breaks and formatting
- Preserve Victorian-era spellings, capitalizations, and punctuation
- Preserve special characters (£, s., d., &c.)
- Use [?] only for completely illegible text
- Include headlines and section markers
- Add blank line between columns

Output only the transcribed text, nothing else."""

    def pdf_to_image(self, pdf_path: Path, dpi: int = 300) -> Optional[Image.Image]:
        """Convert single-page PDF to PIL Image."""
        try:
            doc = fitz.open(pdf_path)
            if len(doc) != 1:
                logging.warning(f"{pdf_path.name}: Expected 1 page, found {len(doc)}")

            page = doc[0]
            # Render at high DPI for quality
            pix = page.get_pixmap(dpi=dpi)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            from io import BytesIO
            img = Image.open(BytesIO(img_data))

            doc.close()
            return img

        except Exception as e:
            logging.error(f"Error converting {pdf_path.name} to image: {e}")
            return None

    def process_pdf(self, pdf_path: Path) -> Dict:
        """Process a single PDF with Gemini OCR."""
        start_time = time.time()

        try:
            # Convert PDF to image
            img = self.pdf_to_image(pdf_path)
            if img is None:
                return {
                    'text': '',
                    'status': 'error',
                    'error': 'Failed to convert PDF to image',
                    'processing_time': time.time() - start_time,
                    'file': str(pdf_path.name)
                }

            logging.debug(f"Converted {pdf_path.name} to image: {img.size[0]}x{img.size[1]}")

            # Send to Gemini
            prompt = f"{self.system_prompt}\n\nPlease transcribe this newspaper page:"

            generation_config = {
                "temperature": 0.1,  # Very low for deterministic OCR
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }

            response = self.model.generate_content(
                [prompt, img],
                generation_config=generation_config
            )

            processing_time = time.time() - start_time

            if response and response.text:
                return {
                    'text': response.text.strip(),
                    'status': 'success',
                    'processing_time': processing_time,
                    'model': self.model_name,
                    'file': str(pdf_path.name)
                }
            else:
                return {
                    'text': '',
                    'status': 'error',
                    'error': 'Empty response from API',
                    'processing_time': processing_time,
                    'file': str(pdf_path.name)
                }

        except Exception as e:
            logging.error(f"Error processing {pdf_path.name}: {e}")
            return {
                'text': '',
                'status': 'error',
                'error': str(e),
                'processing_time': time.time() - start_time,
                'file': str(pdf_path.name)
            }


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance (edit distance) between two strings."""
    if HAS_LEVENSHTEIN:
        return Levenshtein.distance(s1, s2)

    # Pure Python implementation (slower but works without dependencies)
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalize_text(text: str) -> str:
    """Normalize text for comparison - preserve content but standardize whitespace."""
    # Replace multiple spaces/newlines with single space
    import re
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate."""
    ref_norm = normalize_text(reference)
    hyp_norm = normalize_text(hypothesis)

    if len(ref_norm) == 0:
        return 0.0 if len(hyp_norm) == 0 else 1.0

    distance = levenshtein_distance(ref_norm, hyp_norm)
    cer = distance / len(ref_norm)
    return cer


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate."""
    ref_words = normalize_text(reference).split()
    hyp_words = normalize_text(hypothesis).split()

    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0

    # Use word-level edit distance
    distance = levenshtein_distance(' '.join(ref_words), ' '.join(hyp_words))
    # Normalize by number of words (approximate)
    wer = distance / len(' '.join(ref_words))
    return wer


def load_ground_truth(gt_dir: Path, file_id: str) -> Optional[str]:
    """Load ground truth text for a given file ID."""
    gt_file = gt_dir / f"{file_id}.txt"

    if not gt_file.exists():
        logging.warning(f"Ground truth not found: {gt_file}")
        return None

    try:
        with open(gt_file, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading ground truth {gt_file}: {e}")
        return None


def process_and_evaluate(pdf_path: Path, gt_dir: Path, processor: GeminiOCRProcessor,
                        output_dir: Path) -> Dict:
    """Process a PDF and evaluate against ground truth."""
    file_id = pdf_path.stem

    # Process with OCR
    logging.info(f"Processing {file_id}...")
    ocr_result = processor.process_pdf(pdf_path)

    if ocr_result['status'] != 'success':
        logging.error(f"  ✗ OCR failed: {ocr_result.get('error', 'Unknown')}")
        return {
            'file_id': file_id,
            'status': 'ocr_failed',
            'error': ocr_result.get('error', 'Unknown'),
            **ocr_result
        }

    # Load ground truth
    gt_text = load_ground_truth(gt_dir, file_id)
    if gt_text is None:
        logging.warning(f"  ⚠ No ground truth found")
        return {
            'file_id': file_id,
            'status': 'no_ground_truth',
            **ocr_result
        }

    # Calculate metrics
    cer = calculate_cer(gt_text, ocr_result['text'])
    wer = calculate_wer(gt_text, ocr_result['text'])

    result = {
        'file_id': file_id,
        'status': 'evaluated',
        'cer': cer,
        'wer': wer,
        'gt_length': len(gt_text),
        'ocr_length': len(ocr_result['text']),
        'processing_time': ocr_result['processing_time']
    }

    # Save detailed results
    output_file = output_dir / f"{file_id}_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            **result,
            'ocr_text': ocr_result['text'],
            'ground_truth': gt_text
        }, f, indent=2, ensure_ascii=False)

    # Also save just OCR text
    ocr_file = output_dir / f"{file_id}_ocr.txt"
    with open(ocr_file, 'w', encoding='utf-8') as f:
        f.write(ocr_result['text'])

    logging.info(f"  ✓ CER: {cer:.1%}, WER: {wer:.1%}, Time: {ocr_result['processing_time']:.1f}s")

    return result


def select_sample(pdf_dir: Path, sample_size: int, random_seed: int = 42) -> List[Path]:
    """Select random sample of PDFs."""
    all_pdfs = sorted(list(pdf_dir.glob("*.pdf")))

    if len(all_pdfs) <= sample_size:
        logging.info(f"Using all {len(all_pdfs)} PDFs (requested {sample_size})")
        return all_pdfs

    random.seed(random_seed)
    sample = random.sample(all_pdfs, sample_size)
    return sorted(sample)


def generate_report(results: List[Dict], output_dir: Path):
    """Generate summary report with statistics."""
    evaluated = [r for r in results if r['status'] == 'evaluated']

    if not evaluated:
        logging.error("No successfully evaluated files!")
        return

    # Calculate statistics
    cers = [r['cer'] for r in evaluated]
    wers = [r['wer'] for r in evaluated]
    times = [r['processing_time'] for r in evaluated]

    avg_cer = sum(cers) / len(cers)
    avg_wer = sum(wers) / len(wers)
    avg_time = sum(times) / len(times)

    # Sort by CER for best/worst analysis
    sorted_results = sorted(evaluated, key=lambda x: x['cer'])
    best_5 = sorted_results[:5]
    worst_5 = sorted_results[-5:]

    # Generate report
    report = f"""# British Library Newspaper OCR Test Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary Statistics

- **Total Files Processed**: {len(results)}
- **Successfully Evaluated**: {len(evaluated)}
- **Failed**: {len([r for r in results if r['status'] == 'ocr_failed'])}
- **No Ground Truth**: {len([r for r in results if r['status'] == 'no_ground_truth'])}

## Accuracy Metrics

- **Average CER**: {avg_cer:.2%}
- **Average WER**: {avg_wer:.2%}
- **CER Range**: {min(cers):.2%} - {max(cers):.2%}
- **WER Range**: {min(wers):.2%} - {max(wers):.2%}

## Performance

- **Average Processing Time**: {avg_time:.1f}s per page
- **Total Processing Time**: {sum(times):.1f}s ({sum(times)/60:.1f} minutes)

## Quality Assessment

"""

    if avg_cer < 0.05:
        report += "✅ **EXCELLENT** - CER < 5% indicates high-quality OCR\n"
    elif avg_cer < 0.10:
        report += "✓ **GOOD** - CER < 10% indicates acceptable OCR quality\n"
    elif avg_cer < 0.20:
        report += "⚠ **MODERATE** - CER 10-20% suggests OCR challenges\n"
    else:
        report += "✗ **POOR** - CER > 20% indicates significant OCR issues\n"

    report += f"\n## Best Results (Lowest CER)\n\n"
    for r in best_5:
        report += f"- {r['file_id']}: CER={r['cer']:.2%}, WER={r['wer']:.2%}\n"

    report += f"\n## Worst Results (Highest CER)\n\n"
    for r in worst_5:
        report += f"- {r['file_id']}: CER={r['cer']:.2%}, WER={r['wer']:.2%}\n"

    report += f"\n## Detailed Results\n\nSee individual result files in `{output_dir}/`\n"
    report += f"- `*_result.json` - Full metrics and text comparison\n"
    report += f"- `*_ocr.txt` - OCR output text only\n"

    # Save report
    report_file = output_dir / "ocr_test_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print("\n" + "="*70)
    print(report)
    print("="*70)
    print(f"\nFull report saved to: {report_file}")

    # Also save CSV for further analysis
    import csv
    csv_file = output_dir / "ocr_test_results.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file_id', 'status', 'cer', 'wer',
                                                'gt_length', 'ocr_length', 'processing_time'])
        writer.writeheader()
        writer.writerows(results)

    print(f"CSV results saved to: {csv_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Test Gemini OCR on British Library Newspaper Collection'
    )
    parser.add_argument('--pdf-dir', type=str, required=True,
                       help='Directory containing PDF files')
    parser.add_argument('--gt-dir', type=str, required=True,
                       help='Directory containing ground truth text files')
    parser.add_argument('-o', '--output', type=str, required=True,
                       help='Output directory for results')
    parser.add_argument('-k', '--api-key-file', type=str,
                       help='Path to API key file (default: gemini_api_key.txt)')
    parser.add_argument('-m', '--model', type=str, default='gemini-2.0-flash-exp',
                       help='Gemini model to use (default: gemini-2.0-flash-exp)')
    parser.add_argument('-n', '--sample-size', type=int, default=50,
                       help='Number of files to test (default: 50)')
    parser.add_argument('--all', action='store_true',
                       help='Process all files (ignores sample-size)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between API calls in seconds (default: 1.0)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for sample selection (default: 42)')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Enable debug logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"bl_ocr_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            logging.StreamHandler()
        ]
    )

    print("="*70)
    print("BRITISH LIBRARY NEWSPAPER OCR TEST")
    print("="*70)

    # Load API key
    api_key_file = Path(args.api_key_file) if args.api_key_file else Path("gemini_api_key.txt")
    if api_key_file.exists():
        with open(api_key_file, 'r') as f:
            api_key = f.read().strip()
    else:
        api_key = os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GEMINI_API_KEY')

    if not api_key:
        logging.error("No API key found! Set GOOGLE_AI_API_KEY or create gemini_api_key.txt")
        return 1

    print(f"✓ API key loaded")
    print(f"✓ Model: {args.model}")

    # Setup directories
    pdf_dir = Path(args.pdf_dir)
    gt_dir = Path(args.gt_dir)
    output_dir = Path(args.output)

    if not pdf_dir.exists():
        logging.error(f"PDF directory not found: {pdf_dir}")
        return 1

    if not gt_dir.exists():
        logging.error(f"Ground truth directory not found: {gt_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # Select sample
    if args.all:
        sample_pdfs = sorted(list(pdf_dir.glob("*.pdf")))
    else:
        sample_pdfs = select_sample(pdf_dir, args.sample_size, args.seed)

    print(f"✓ Selected {len(sample_pdfs)} PDFs to process")
    print("-"*70)

    # Initialize processor
    processor = GeminiOCRProcessor(api_key, model_name=args.model)

    # Process all PDFs
    results = []
    start_time = time.time()

    for i, pdf_path in enumerate(sample_pdfs, 1):
        print(f"\n[{i}/{len(sample_pdfs)}] {pdf_path.name}")

        result = process_and_evaluate(pdf_path, gt_dir, processor, output_dir)
        results.append(result)

        # Rate limiting
        if i < len(sample_pdfs):
            time.sleep(args.delay)

    total_time = time.time() - start_time

    print("\n" + "="*70)
    print(f"Completed in {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print("="*70)

    # Generate report
    generate_report(results, output_dir)

    return 0


if __name__ == '__main__':
    sys.exit(main())
