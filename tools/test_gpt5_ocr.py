#!/usr/bin/env python3
"""
Test GPT-5 OCR via OpenRouter on a failed Gemini image.
"""
import os
import sys
import json
import base64
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
MODEL = "openrouter/polaris-alpha"  # Testing Polaris Alpha

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

def ocr_with_gpt5(image_path: Path) -> dict:
    """Send image to GPT-5 via OpenRouter for OCR."""

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
        "X-Title": "TTJ OCR Test"
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
        "temperature": 0.3,   # Low temperature for deterministic OCR (matching Gemini)
        "top_p": 0.95
    }

    print(f"Sending to OpenRouter ({MODEL})...")
    start_time = datetime.now()

    try:
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
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

            print(f"\nSuccess!")
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
                'model': MODEL
            }
        else:
            print(f"Unexpected response format: {result}")
            return {
                'success': False,
                'error': 'Unexpected response format',
                'response': result
            }

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

def main():
    # Test image that failed with Gemini (MAX_TOKENS)
    test_image = Path("/home/jic823/TTJ Forest of Numbers/ocr_ready/1875/2. Timber Trades Journal Vol. 3 - 1875/14. p. 212-215 - October 30 1875 - Timber Trades Journal Vol. 3 1875_p001.png")

    if not test_image.exists():
        print(f"Error: Test image not found: {test_image}")
        return 1

    print("=" * 80)
    print(f"{MODEL} OCR TEST - Failed Gemini Image")
    print("=" * 80)
    print(f"\nTest Image: {test_image.name}")
    print(f"Original Failure: MAX_TOKENS (Gemini 65,536 token limit)")
    print(f"Testing with: {MODEL}")
    print()

    # Run OCR
    result = ocr_with_gpt5(test_image)

    # Save results
    model_name = MODEL.replace('/', '_').replace(':', '_')
    output_dir = Path(f"/home/jic823/TTJ Forest of Numbers/ocr_results/{model_name}_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON result
    json_path = output_dir / f"{test_image.stem}_{model_name}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {json_path}")

    # Save text output if successful
    if result['success']:
        txt_path = output_dir / f"{test_image.stem}_{model_name}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        print(f"OCR text saved to: {txt_path}")

        # Print first 500 chars
        print("\n" + "=" * 80)
        print("FIRST 500 CHARACTERS OF OUTPUT:")
        print("=" * 80)
        print(result['text'][:500])
        print("..." if len(result['text']) > 500 else "")

    return 0 if result['success'] else 1

if __name__ == '__main__':
    sys.exit(main())
