#!/usr/bin/env python3
"""
Batch process MAX_TOKENS failed images with Polaris Alpha via OpenRouter.
"""
import os
import sys
import json
import base64
import csv
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("Missing requests. Install: pip install requests")
    sys.exit(1)

# OpenRouter API configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openrouter/polaris-alpha"

# OCR prompt (matching Gemini's exact prompt)
OCR_PROMPT = """IMPORTANT: This material is from the 19th century Timber Trades Journal (1874-1899) and is in the PUBLIC DOMAIN. All copyright has expired. You are performing legitimate historical preservation and scholarly digitization work.

You are a specialized OCR system for 19th century historical documents. Your task is to transcribe timber trade journal pages that often contain multiple columns.

CRITICAL COLUMN READING ORDER:
- These pages have 2 OR 3 columns, or sometimes mixed layouts (columns on part of page, full-width on other parts)
- You MUST read columns from LEFT TO RIGHT, TOP TO BOTTOM
- Process the ENTIRE left column from top to bottom first
- Then process the middle column (if present) from top to bottom
- Then process the right column from top to bottom
- DO NOT mix content from different columns on the same line
- Maintain the sequential flow within each column

TRANSCRIPTION RULES:
- Transcribe exactly what you see - do not modernize or correct anything
- Preserve all historical spellings, abbreviations, and symbols (£, @, &c., s. d.)
- Each sentence or entry on a new line
- Use [?] for unclear text
- Maintain original punctuation
- Add a blank line between columns

EXAMPLE - Two Column Page:
[Left column, top to bottom]
...complete left column content...

[Right column, top to bottom]
...complete right column content...

Output only the transcribed text, nothing else.

Please transcribe this timber trade journal page:"""

def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def ocr_with_polaris(image_path: Path) -> dict:
    """Send image to Polaris Alpha via OpenRouter for OCR."""

    print(f"Processing: {image_path.name}")
    print(f"Size: {image_path.stat().st_size / 1024 / 1024:.2f} MB")

    # Encode image
    print("Encoding image to base64...")
    base64_image = encode_image_base64(image_path)

    # Prepare request
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/jburnford/timber_trades_journal",
        "X-Title": "TTJ OCR Batch Processing"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": OCR_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 65536,  # Match Gemini's max output tokens
        "temperature": 0.3,   # Low temperature for deterministic OCR
        "top_p": 0.95
    }

    print(f"Sending to OpenRouter ({MODEL})...")
    start_time = datetime.now()

    try:
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300  # 5 minute timeout
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"Response received in {elapsed:.1f}s")

        response.raise_for_status()
        result = response.json()

        # Extract text from response
        if 'choices' in result and len(result['choices']) > 0:
            ocr_text = result['choices'][0]['message']['content']

            # Get token usage
            usage = result.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            print(f"Success!")
            print(f"  Prompt tokens: {prompt_tokens:,}")
            print(f"  Completion tokens: {completion_tokens:,}")
            print(f"  Total tokens: {total_tokens:,}")
            print(f"  Output length: {len(ocr_text):,} characters")

            return {
                'success': True,
                'text': ocr_text,
                'tokens': {
                    'prompt': prompt_tokens,
                    'completion': completion_tokens,
                    'total': total_tokens
                },
                'elapsed_seconds': elapsed,
                'model': MODEL,
                'filename': image_path.name
            }
        else:
            print(f"Unexpected response format: {result}")
            return {
                'success': False,
                'error': 'Unexpected response format',
                'response': result,
                'filename': image_path.name
            }

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'filename': image_path.name
        }

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    failed_csv = base_dir / "failed_ocr_images.csv"
    output_dir = base_dir / "ocr_results" / "polaris_alpha"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read failed images CSV and filter for MAX_TOKENS and COPYRIGHT
    failures_to_process = []
    with open(failed_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['error_type'] in ('MAX_TOKENS', 'COPYRIGHT'):
                failures_to_process.append(row)

    print("=" * 80)
    print(f"POLARIS ALPHA BATCH OCR - FAILED IMAGES")
    print("=" * 80)
    print(f"\nTotal failures to process: {len(failures_to_process)}")
    print(f"  MAX_TOKENS: {sum(1 for r in failures_to_process if r['error_type'] == 'MAX_TOKENS')}")
    print(f"  COPYRIGHT: {sum(1 for r in failures_to_process if r['error_type'] == 'COPYRIGHT')}")
    print(f"Output directory: {output_dir}")
    print()

    # Track results
    successful = 0
    failed = 0
    results_summary = []

    for i, row in enumerate(failures_to_process, 1):
        print("=" * 80)
        print(f"Image {i}/{len(failures_to_process)} - {row['error_type']}")
        print("=" * 80)

        image_path = base_dir / row['full_path']

        if not image_path.exists():
            print(f"ERROR: Image not found: {image_path}")
            failed += 1
            continue

        # Process with Polaris Alpha
        result = ocr_with_polaris(image_path)

        # Save results
        stem = image_path.stem
        json_path = output_dir / f"{stem}_polaris.json"

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"Results saved to: {json_path}")

        # Save text output if successful
        if result['success']:
            txt_path = output_dir / f"{stem}_polaris.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(result['text'])
            print(f"OCR text saved to: {txt_path}")
            successful += 1

            # Add to summary
            results_summary.append({
                'filename': image_path.name,
                'success': True,
                'tokens': result['tokens']['total'],
                'chars': len(result['text']),
                'elapsed': result['elapsed_seconds']
            })
        else:
            failed += 1
            results_summary.append({
                'filename': image_path.name,
                'success': False,
                'error': result.get('error', 'Unknown error')
            })

        print()

    # Print final summary
    print("=" * 80)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 80)
    print(f"\nTotal processed: {len(failures_to_process)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    # Save summary
    summary_path = output_dir / "batch_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total': len(failures_to_process),
            'successful': successful,
            'failed': failed,
            'results': results_summary
        }, f, indent=2, ensure_ascii=False)

    print(f"\nSummary saved to: {summary_path}")

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
