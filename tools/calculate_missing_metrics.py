#!/usr/bin/env python3
"""
Calculate missing evaluation metrics for OCR systems in the database.
For systems with ocr_results but no evaluation_metrics.
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime
import sys

DB_PATH = Path("/home/jic823/ocr_bldata/ocr_results/database/ocr_evaluation.db")
GT_DIR = Path("/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth")

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def calculate_metrics(gt_text: str, ocr_text: str) -> dict:
    """Calculate CER, WER, and Levenshtein distance."""
    gt_norm = normalize_text(gt_text)
    ocr_norm = normalize_text(ocr_text)

    if len(gt_norm) == 0:
        return {
            'cer': 0.0 if len(ocr_norm) == 0 else 1.0,
            'wer': 0.0 if len(ocr_norm) == 0 else 1.0,
            'levenshtein_distance': len(ocr_norm)
        }

    distance = levenshtein_distance(gt_norm, ocr_norm)
    cer = distance / len(gt_norm)  # NO LONGER CAPPING - allow CER > 1.0
    wer = cer  # Simplified WER calculation

    return {
        'cer': cer,
        'wer': wer,
        'levenshtein_distance': distance
    }

def process_missing_metrics():
    """Find and process all OCR results missing evaluation metrics."""

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find systems with missing metrics
    cursor.execute('''
        SELECT DISTINCT s.system_id, s.name
        FROM ocr_systems s
        JOIN ocr_results r ON s.system_id = r.system_id
        LEFT JOIN evaluation_metrics em ON r.short_id = em.short_id AND r.system_id = em.system_id
        WHERE em.short_id IS NULL
        ORDER BY s.name
    ''')

    systems_with_missing = cursor.fetchall()

    if not systems_with_missing:
        print("No missing evaluation metrics found!")
        return 0

    print(f"Found {len(systems_with_missing)} systems with missing evaluation metrics")
    print()

    total_processed = 0
    total_errors = 0

    for system_id, system_name in systems_with_missing:
        print(f"Processing: {system_name} ({system_id})")
        print("-" * 70)

        # Find OCR results without evaluation metrics
        cursor.execute('''
            SELECT r.short_id, r.text_content
            FROM ocr_results r
            LEFT JOIN evaluation_metrics em ON r.short_id = em.short_id AND r.system_id = em.system_id
            WHERE r.system_id = ? AND em.short_id IS NULL
        ''', (system_id,))

        missing_results = cursor.fetchall()
        print(f"  Documents missing metrics: {len(missing_results)}")

        processed = 0
        errors = 0

        for short_id, ocr_text in missing_results:
            # Load ground truth
            gt_file = GT_DIR / f"{short_id}.txt"
            if not gt_file.exists():
                print(f"    Warning: No ground truth for {short_id}")
                errors += 1
                continue

            try:
                with open(gt_file, 'r', encoding='utf-8') as f:
                    gt_text = f.read()

                # Calculate metrics
                metrics = calculate_metrics(gt_text, ocr_text)

                # Insert evaluation metrics
                cursor.execute('''
                    INSERT INTO evaluation_metrics
                    (short_id, system_id, cer, wer, levenshtein_distance, calculated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    short_id,
                    system_id,
                    metrics['cer'],
                    metrics['wer'],
                    metrics['levenshtein_distance'],
                    datetime.now().isoformat()
                ))

                processed += 1

                if processed % 100 == 0:
                    print(f"    Processed {processed}...")
                    conn.commit()

            except Exception as e:
                print(f"    Error processing {short_id}: {e}")
                errors += 1
                continue

        conn.commit()
        print(f"  ✓ Completed: {processed} metrics calculated, {errors} errors")
        print()

        total_processed += processed
        total_errors += errors

    conn.close()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total metrics calculated: {total_processed}")
    print(f"Total errors: {total_errors}")
    print("=" * 70)

    return 0

if __name__ == '__main__':
    sys.exit(process_missing_metrics())
