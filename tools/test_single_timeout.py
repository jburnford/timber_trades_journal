#!/usr/bin/env python3
"""Quick test of a single timeout file with the fixed parser."""
from pathlib import Path
import time
from ttj_parser_v3 import TTJContextParser

def test_timeout_file():
    """Test one of the known timeout files."""
    ocr_dir = Path("/home/jic823/TTJ Forest of Numbers/ocr_results/gemini_full")

    # Test with one of the files that timed out
    test_file = ocr_dir / "18800110.txt"

    print(f"Testing timeout file: {test_file.name}")
    print("=" * 80)

    parser = TTJContextParser()

    start = time.time()
    records, error = parser.parse_file(test_file, year=1880)
    elapsed = time.time() - start

    print(f"\nResult:")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Records: {len(records) if records else 0}")
    print(f"  Error: {error if error else 'None'}")

    if records and len(records) > 0:
        print(f"\nFirst 3 records:")
        for i, rec in enumerate(records[:3], 1):
            print(f"  {i}. {rec.ship_name} from {rec.origin_port} to {rec.destination_port}")
            print(f"     Cargo: {rec.cargo[:50]}..." if len(rec.cargo) > 50 else f"     Cargo: {rec.cargo}")

    if elapsed < 5.0:
        print(f"\n✓ SUCCESS! Completed in {elapsed:.2f}s (under 5s timeout)")
    else:
        print(f"\n✗ FAIL! Took {elapsed:.2f}s (would have timed out)")

if __name__ == '__main__':
    test_timeout_file()
