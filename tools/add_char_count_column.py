#!/usr/bin/env python3
"""
Add character count column for raw_line to CSV.
"""
import csv
import sys
from pathlib import Path

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)

def add_char_count_column(input_file: Path, output_file: Path):
    """Add raw_line_char_count column to CSV."""

    print(f"Reading from: {input_file}")
    print(f"Writing to: {output_file}")

    record_count = 0

    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)

        # Get existing fieldnames and add new column
        fieldnames = reader.fieldnames.copy()
        fieldnames.append('raw_line_char_count')

        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                # Calculate character count of raw_line
                raw_line = row.get('raw_line', '')
                row['raw_line_char_count'] = len(raw_line)

                writer.writerow(row)
                record_count += 1

                if record_count % 10000 == 0:
                    print(f"  Processed {record_count:,} records...")

    print(f"\nCompleted!")
    print(f"Total records processed: {record_count:,}")
    print(f"Output file: {output_file}")

if __name__ == '__main__':
    input_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final.csv")
    temp_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_final_temp.csv")

    # Write to temp file first
    add_char_count_column(input_file, temp_file)

    # Move temp file to replace original
    print(f"\nReplacing original file...")
    temp_file.rename(input_file)
    print(f"Done!")
