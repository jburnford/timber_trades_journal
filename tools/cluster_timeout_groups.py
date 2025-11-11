#!/usr/bin/env python3
"""
Cluster the 257 timeout document groups by year to create targeted parsers.
"""
import re
from pathlib import Path
from collections import defaultdict

def extract_year_from_filename(filename: str) -> int:
    """Extract publication year from filename."""
    # Pattern: YYYYMMDD at start
    match = re.match(r'^(\d{4})\d{4}', filename)
    if match:
        return int(match.group(1))

    # Pattern: year in long filenames like "April 28 1877"
    match = re.search(r'\b(18\d{2}|19\d{2})\b', filename)
    if match:
        return int(match.group(1))

    return None

def cluster_by_year():
    """Cluster timeout groups by year."""
    timeout_file = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/timeout_document_groups.txt")

    with open(timeout_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    # Cluster by year
    year_clusters = defaultdict(list)
    no_year = []

    for line in lines:
        year = extract_year_from_filename(line)
        if year:
            year_clusters[year].append(line)
        else:
            no_year.append(line)

    # Print clusters
    print("=" * 80)
    print("TIMEOUT DOCUMENT GROUPS CLUSTERED BY YEAR")
    print("=" * 80)
    print(f"Total timeout groups: {len(lines)}")
    print(f"Groups with year: {len(lines) - len(no_year)}")
    print(f"Groups without year: {len(no_year)}")
    print()

    # Sort by year and show distribution
    for year in sorted(year_clusters.keys()):
        count = len(year_clusters[year])
        print(f"{year}: {count:3d} groups")

    if no_year:
        print(f"\nNo year: {len(no_year)} groups")

    print("\n" + "=" * 80)
    print("BREAKDOWN BY DECADE")
    print("=" * 80)

    decade_counts = defaultdict(int)
    for year, groups in year_clusters.items():
        decade = (year // 10) * 10
        decade_counts[decade] += len(groups)

    for decade in sorted(decade_counts.keys()):
        print(f"{decade}s: {decade_counts[decade]:3d} groups")

    # Save clustered files for processing
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/timeout_clusters")
    output_dir.mkdir(exist_ok=True)

    for year, groups in year_clusters.items():
        cluster_file = output_dir / f"timeout_{year}.txt"
        with open(cluster_file, 'w', encoding='utf-8') as f:
            for group in groups:
                f.write(group + '\n')

    if no_year:
        cluster_file = output_dir / "timeout_no_year.txt"
        with open(cluster_file, 'w', encoding='utf-8') as f:
            for group in no_year:
                f.write(group + '\n')

    print("\n" + "=" * 80)
    print(f"✓ Saved year clusters to: {output_dir}")
    print("=" * 80)

    return year_clusters, no_year

if __name__ == '__main__':
    year_clusters, no_year = cluster_by_year()
