#!/usr/bin/env python3
"""Inspect the OCR evaluation database structure."""

import sqlite3
from pathlib import Path

db_path = Path("/home/jic823/ocr_bldata/ocr_results/database/ocr_evaluation.db")

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=" * 70)
print("DATABASE SCHEMA")
print("=" * 70)
print()

for table_name in tables:
    table = table_name[0]
    print(f"\n{'='*70}")
    print(f"TABLE: {table}")
    print(f"{'='*70}")

    # Get schema
    cursor.execute(f"PRAGMA table_info({table});")
    columns = cursor.fetchall()

    print("\nColumns:")
    for col in columns:
        cid, name, dtype, notnull, default, pk = col
        print(f"  {name:20} {dtype:15} {'NOT NULL' if notnull else ''} {'PRIMARY KEY' if pk else ''}")

    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table};")
    count = cursor.fetchone()[0]
    print(f"\nRow count: {count}")

    # Show sample data
    if count > 0:
        cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
        rows = cursor.fetchall()
        print(f"\nSample data (first 3 rows):")
        col_names = [desc[1] for desc in columns]
        for row in rows:
            print("\n  Row:")
            for col_name, value in zip(col_names, row):
                # Truncate long values
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"    {col_name}: {value}")

conn.close()
