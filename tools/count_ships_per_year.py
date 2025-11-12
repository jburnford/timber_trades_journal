#!/usr/bin/env python3
"""
Count ships per year from the merged dataset.
"""
import csv
import sys
from pathlib import Path
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

def count_ships_per_year(merged_csv: Path, output_file: Path):
    """Count ships by publication year and arrival year."""

    print("=" * 80)
    print("COUNTING SHIPS PER YEAR")
    print("=" * 80)

    publication_year_counts = defaultdict(int)
    arrival_year_counts = defaultdict(int)
    total_records = 0
    records_with_arrival_year = 0

    print(f"\nReading {merged_csv}...")

    with open(merged_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_records += 1

            # Count by publication year
            pub_year = row.get('publication_year', '')
            if pub_year and pub_year.isdigit():
                publication_year_counts[int(pub_year)] += 1

            # Count by arrival year (if available)
            arrival_year = row.get('arrival_year', '')
            if arrival_year and str(arrival_year).isdigit():
                arrival_year_counts[int(arrival_year)] += 1
                records_with_arrival_year += 1

    print(f"Total records: {total_records:,}")
    print(f"Records with arrival year: {records_with_arrival_year:,}")

    # Write output file
    print(f"\nWriting counts to {output_file}...")

    with open(output_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("SHIPS PER YEAR - TIMBER TRADES JOURNAL DATASET\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Total records: {total_records:,}\n")
        f.write(f"Records with arrival year: {records_with_arrival_year:,}\n\n")

        # Publication Year Counts
        f.write("=" * 80 + "\n")
        f.write("SHIPS BY PUBLICATION YEAR\n")
        f.write("=" * 80 + "\n\n")

        pub_years = sorted(publication_year_counts.keys())
        f.write(f"{'Year':<10} {'Ships':>10}\n")
        f.write("-" * 22 + "\n")

        for year in pub_years:
            count = publication_year_counts[year]
            f.write(f"{year:<10} {count:>10,}\n")

        f.write("-" * 22 + "\n")
        f.write(f"{'TOTAL':<10} {sum(publication_year_counts.values()):>10,}\n\n")

        # Arrival Year Counts (if any)
        if arrival_year_counts:
            f.write("=" * 80 + "\n")
            f.write("SHIPS BY ARRIVAL YEAR (where recorded)\n")
            f.write("=" * 80 + "\n\n")

            arrival_years = sorted(arrival_year_counts.keys())
            f.write(f"{'Year':<10} {'Ships':>10}\n")
            f.write("-" * 22 + "\n")

            for year in arrival_years:
                count = arrival_year_counts[year]
                f.write(f"{year:<10} {count:>10,}\n")

            f.write("-" * 22 + "\n")
            f.write(f"{'TOTAL':<10} {sum(arrival_year_counts.values()):>10,}\n\n")

    # Print summary to console
    print("\n" + "=" * 80)
    print("SHIPS BY PUBLICATION YEAR")
    print("=" * 80)
    print(f"{'Year':<10} {'Ships':>10} {'Bar Chart':>40}")
    print("-" * 62)

    max_count = max(publication_year_counts.values())

    for year in sorted(publication_year_counts.keys()):
        count = publication_year_counts[year]
        bar_length = int((count / max_count) * 40)
        bar = "█" * bar_length
        print(f"{year:<10} {count:>10,} {bar}")

    print("-" * 62)
    print(f"{'TOTAL':<10} {sum(publication_year_counts.values()):>10,}")
    print("=" * 80)

    print(f"\nDetailed counts written to: {output_file}")

    return publication_year_counts, arrival_year_counts

if __name__ == '__main__':
    merged_csv = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_merged.csv")
    output_file = Path("/home/jic823/TTJ Forest of Numbers/analysis/ships_per_year.txt")

    count_ships_per_year(merged_csv, output_file)
