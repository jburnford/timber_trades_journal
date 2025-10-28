#!/usr/bin/env python3
"""
Import DeepSeek OCR results into the OCR evaluation database.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import sys

# Paths
DB_PATH = Path("/home/jic823/ocr_bldata/ocr_results/database/ocr_evaluation.db")
DEEPSEEK_RESULTS_DIR = Path("/home/jic823/DeekSeekOCR/results/full_600_dataset/base_size_1024")

def import_deepseek_results():
    """Import all DeepSeek results from JSON files."""

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # First, add DeepSeek to ocr_systems table if not exists
    system_id = 'deepseek_ocr'
    cursor.execute("SELECT system_id FROM ocr_systems WHERE system_id = ?", (system_id,))
    if not cursor.fetchone():
        print(f"Adding {system_id} to ocr_systems table...")
        cursor.execute("""
            INSERT INTO ocr_systems
            (system_id, name, version, description, cost_per_page, cost_currency, processing_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            system_id,
            'DeepSeek OCR',
            'base_size_1024',
            'DeepSeek OCR model with base size 1024',
            0.0,  # Open source/self-hosted
            'USD',
            'local',
            datetime.now().isoformat()
        ))
        conn.commit()
        print(f"✓ Added {system_id} to database")

    # Find all result JSON files
    result_files = list(DEEPSEEK_RESULTS_DIR.glob("*.json"))
    print(f"\nFound {len(result_files)} DeepSeek result files")

    imported = 0
    skipped = 0
    errors = 0

    for result_file in result_files:
        short_id = result_file.stem

        # Check if already imported
        cursor.execute("""
            SELECT short_id FROM ocr_results
            WHERE short_id = ? AND system_id = ?
        """, (short_id, system_id))

        if cursor.fetchone():
            skipped += 1
            continue

        try:
            # Load result JSON
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)

            # Use ocr_text (NOT ground_truth_text as per user instruction)
            ocr_text = result.get('ocr_text', '')
            if not ocr_text:
                print(f"  Skipping {short_id}: no ocr_text found")
                errors += 1
                continue

            processing_time = result.get('processing_time', None)

            # Use pre-calculated metrics from JSON
            # NO LONGER CAPPING - allow CER > 1.0 for catastrophic failures
            cer = result.get('cer', 0.0)
            wer = result.get('wer', 0.0)

            # Calculate Levenshtein distance from CER
            gt_text = result.get('ground_truth_text', '')
            gt_length = len(gt_text) if gt_text else len(ocr_text)
            levenshtein_distance = int(cer * gt_length) if cer is not None else 0

            metrics = {
                'cer': cer,
                'wer': wer,
                'levenshtein_distance': levenshtein_distance,
                'character_count': len(ocr_text),
                'word_count': len(ocr_text.split())
            }

            # Insert into ocr_results
            cursor.execute("""
                INSERT INTO ocr_results
                (short_id, system_id, text_content, processing_time_seconds,
                 character_count, word_count, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                short_id,
                system_id,
                ocr_text,
                processing_time,
                metrics['character_count'],
                metrics['word_count'],
                datetime.now().isoformat()
            ))

            # Insert into evaluation_metrics
            cursor.execute("""
                INSERT INTO evaluation_metrics
                (short_id, system_id, cer, wer, levenshtein_distance, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                short_id,
                system_id,
                metrics['cer'],
                metrics['wer'],
                metrics['levenshtein_distance'],
                datetime.now().isoformat()
            ))

            imported += 1

            if imported % 50 == 0:
                print(f"  Imported {imported} documents...")
                conn.commit()

        except Exception as e:
            print(f"  Error processing {short_id}: {e}")
            errors += 1
            continue

    conn.commit()
    conn.close()

    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"Imported: {imported}")
    print(f"Skipped (already in DB): {skipped}")
    print(f"Errors: {errors}")
    print("=" * 70)

    return 0

if __name__ == '__main__':
    sys.exit(import_deepseek_results())
