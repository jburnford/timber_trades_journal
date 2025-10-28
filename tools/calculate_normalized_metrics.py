#!/usr/bin/env python3
"""
Calculate Normalized CER/WER metrics for OCR evaluation.

Normalized metrics remove superficial differences (punctuation, case, whitespace)
to better assess semantic accuracy vs. raw character-level differences.

Purpose: Test hypothesis that OLMoCR's 7% CER is mostly superficial errors
         while Gemini's 0.98% CER includes both superficial and semantic errors.
"""

import sqlite3
import re
from pathlib import Path
from typing import Tuple
import sys

# Database and ground truth paths
DB_PATH = Path("/home/jic823/ocr_bldata/ocr_results/database/ocr_evaluation.db")
GT_DIR = Path("/home/jic823/ocr_bldata/25439023/BLN600/Ground Truth")


def normalize_for_comparison(text: str) -> str:
    """
    Remove superficial differences for normalized comparison.

    Steps:
    1. Lowercase
    2. Remove all punctuation
    3. Normalize whitespace to single spaces
    4. Strip leading/trailing whitespace

    This tests semantic accuracy: "Hello, World!" == "hello world"
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text.strip()


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
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


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate."""
    if len(reference) == 0:
        return 0.0 if len(hypothesis) == 0 else 1.0

    distance = levenshtein_distance(reference, hypothesis)
    return distance / len(reference)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0

    distance = levenshtein_distance(' '.join(ref_words), ' '.join(hyp_words))
    return distance / len(' '.join(ref_words))


def calculate_normalized_metrics(gt_text: str, ocr_text: str) -> dict:
    """
    Calculate both raw and normalized CER/WER.

    Returns:
        dict with 'raw_cer', 'raw_wer', 'norm_cer', 'norm_wer'
    """
    # Raw metrics (original text)
    raw_cer = calculate_cer(gt_text, ocr_text)
    raw_wer = calculate_wer(gt_text, ocr_text)

    # Normalized metrics (remove punctuation/case)
    gt_norm = normalize_for_comparison(gt_text)
    ocr_norm = normalize_for_comparison(ocr_text)

    norm_cer = calculate_cer(gt_norm, ocr_norm)
    norm_wer = calculate_wer(gt_norm, ocr_norm)

    return {
        'raw_cer': raw_cer,
        'raw_wer': raw_wer,
        'norm_cer': norm_cer,
        'norm_wer': norm_wer,
        'cer_reduction': ((raw_cer - norm_cer) / raw_cer * 100) if raw_cer > 0 else 0,
        'wer_reduction': ((raw_wer - norm_wer) / raw_wer * 100) if raw_wer > 0 else 0
    }


def update_database_with_normalized_metrics():
    """
    Calculate and store normalized metrics for all OCR results in database.

    Updates evaluation_metrics table with norm_cer and norm_wer values.
    """

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return 1

    if not GT_DIR.exists():
        print(f"Error: Ground truth directory not found at {GT_DIR}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # First, add columns if they don't exist
    try:
        cursor.execute("ALTER TABLE evaluation_metrics ADD COLUMN norm_cer REAL")
        cursor.execute("ALTER TABLE evaluation_metrics ADD COLUMN norm_wer REAL")
        print("✓ Added norm_cer and norm_wer columns to database")
    except sqlite3.OperationalError:
        print("✓ Columns norm_cer and norm_wer already exist")

    # Get all OCR results that need normalized metrics
    cursor.execute("""
        SELECT r.short_id, r.system_id, r.text_content, s.name
        FROM ocr_results r
        JOIN ocr_systems s ON r.system_id = s.system_id
        JOIN evaluation_metrics em ON r.short_id = em.short_id AND r.system_id = em.system_id
        WHERE em.norm_cer IS NULL OR em.norm_wer IS NULL
        ORDER BY s.name, r.short_id
    """)

    results = cursor.fetchall()

    if not results:
        print("\n✓ All records already have normalized metrics!")

        # Show summary
        cursor.execute("""
            SELECT
                s.name,
                COUNT(*) as files,
                ROUND(AVG(em.cer) * 100, 2) as avg_cer,
                ROUND(AVG(em.norm_cer) * 100, 2) as avg_norm_cer,
                ROUND(AVG(em.wer) * 100, 2) as avg_wer,
                ROUND(AVG(em.norm_wer) * 100, 2) as avg_norm_wer
            FROM ocr_systems s
            JOIN evaluation_metrics em ON s.system_id = em.system_id
            WHERE em.norm_cer IS NOT NULL
            GROUP BY s.system_id
            ORDER BY avg_norm_cer
        """)

        print("\n" + "=" * 100)
        print("NORMALIZED METRICS SUMMARY")
        print("=" * 100)
        print(f"{'System':<40} {'Files':<8} {'Raw CER':<10} {'Norm CER':<10} {'Raw WER':<10} {'Norm WER':<10}")
        print("-" * 100)

        for row in cursor.fetchall():
            name, files, raw_cer, norm_cer, raw_wer, norm_wer = row
            print(f"{name:<40} {files:<8} {raw_cer:<10.2f} {norm_cer:<10.2f} {raw_wer:<10.2f} {norm_wer:<10.2f}")

        conn.close()
        return 0

    print(f"\nCalculating normalized metrics for {len(results)} OCR results...")
    print("=" * 80)

    processed = 0
    errors = 0

    current_system = None
    system_stats = {}

    for short_id, system_id, ocr_text, system_name in results:
        # Track progress by system
        if current_system != system_name:
            if current_system is not None:
                stats = system_stats[current_system]
                print(f"  ✓ {current_system}: {stats['processed']} processed, {stats['errors']} errors")
            current_system = system_name
            system_stats[current_system] = {'processed': 0, 'errors': 0}
            print(f"\nProcessing: {system_name}")

        # Load ground truth
        gt_file = GT_DIR / f"{short_id}.txt"
        if not gt_file.exists():
            print(f"  Warning: No ground truth for {short_id}")
            system_stats[current_system]['errors'] += 1
            errors += 1
            continue

        try:
            with open(gt_file, 'r', encoding='utf-8') as f:
                gt_text = f.read()

            # Calculate normalized metrics
            metrics = calculate_normalized_metrics(gt_text, ocr_text)

            # Update database
            cursor.execute("""
                UPDATE evaluation_metrics
                SET norm_cer = ?, norm_wer = ?
                WHERE short_id = ? AND system_id = ?
            """, (
                metrics['norm_cer'],
                metrics['norm_wer'],
                short_id,
                system_id
            ))

            processed += 1
            system_stats[current_system]['processed'] += 1

            if processed % 100 == 0:
                print(f"    Progress: {processed}/{len(results)}...")
                conn.commit()

        except Exception as e:
            print(f"  Error processing {short_id}: {e}")
            system_stats[current_system]['errors'] += 1
            errors += 1
            continue

    # Final system summary
    if current_system is not None:
        stats = system_stats[current_system]
        print(f"  ✓ {current_system}: {stats['processed']} processed, {stats['errors']} errors")

    conn.commit()

    print("\n" + "=" * 80)
    print("CALCULATION COMPLETE")
    print("=" * 80)
    print(f"Total processed: {processed}")
    print(f"Total errors: {errors}")

    # Generate comparison report
    print("\n" + "=" * 100)
    print("NORMALIZED METRICS COMPARISON")
    print("=" * 100)

    cursor.execute("""
        SELECT
            s.name,
            COUNT(*) as files,
            ROUND(AVG(em.cer) * 100, 2) as avg_raw_cer,
            ROUND(AVG(em.norm_cer) * 100, 2) as avg_norm_cer,
            ROUND((AVG(em.cer) - AVG(em.norm_cer)) / AVG(em.cer) * 100, 1) as cer_reduction_pct,
            ROUND(AVG(em.wer) * 100, 2) as avg_raw_wer,
            ROUND(AVG(em.norm_wer) * 100, 2) as avg_norm_wer,
            ROUND((AVG(em.wer) - AVG(em.norm_wer)) / AVG(em.wer) * 100, 1) as wer_reduction_pct
        FROM ocr_systems s
        JOIN evaluation_metrics em ON s.system_id = em.system_id
        WHERE em.norm_cer IS NOT NULL
        GROUP BY s.system_id
        ORDER BY avg_norm_cer
    """)

    print(f"{'System':<40} {'Files':<8} {'Raw CER':<10} {'Norm CER':<10} {'↓%':<8} {'Raw WER':<10} {'Norm WER':<10} {'↓%':<8}")
    print("-" * 100)

    for row in cursor.fetchall():
        name, files, raw_cer, norm_cer, cer_red, raw_wer, norm_wer, wer_red = row
        print(f"{name:<40} {files:<8} {raw_cer:<10.2f} {norm_cer:<10.2f} {cer_red:<8.1f} {raw_wer:<10.2f} {norm_wer:<10.2f} {wer_red:<8.1f}")

    print("=" * 100)

    # Highlight key findings
    print("\nKEY FINDINGS:")
    print("-" * 100)

    cursor.execute("""
        SELECT name,
               ROUND(AVG(cer) * 100, 2) as raw_cer,
               ROUND(AVG(norm_cer) * 100, 2) as norm_cer,
               ROUND((AVG(cer) - AVG(norm_cer)) / AVG(cer) * 100, 1) as reduction
        FROM evaluation_metrics em
        JOIN ocr_systems s ON em.system_id = s.system_id
        WHERE s.name IN ('Google Gemini 2.5 Pro', 'olmocr', 'DeepSeek OCR')
        GROUP BY s.system_id
    """)

    for name, raw_cer, norm_cer, reduction in cursor.fetchall():
        print(f"  {name}: {raw_cer}% → {norm_cer}% CER ({reduction}% reduction)")

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(update_database_with_normalized_metrics())
