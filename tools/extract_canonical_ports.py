#!/usr/bin/env python3
"""
Extract canonical port lists from human-transcribed Excel files.
Creates authoritative reference lists for normalization.
"""

import pandas as pd
import json
from pathlib import Path


def extract_canonical_origin_ports(excel_path: Path) -> list:
    """
    Extract canonical origin ports from cargoes sheet.

    Coverage: 3 years (1883, 1889, 1897)
    Source: London Timber imports data ttj.xlsx -> cargoes sheet -> City column
    """
    print("=" * 80)
    print("EXTRACTING CANONICAL ORIGIN PORTS")
    print("=" * 80)

    df = pd.read_excel(excel_path, sheet_name='cargoes')

    print(f"Total records in cargoes sheet: {len(df)}")
    print(f"Years covered: {sorted(df['Year'].unique())}")

    # Get unique cities
    cities = df['City'].dropna().unique()
    print(f"Total unique ports (raw): {len(cities)}")

    # Clean placeholders and invalid entries
    placeholders = {'(vide)', '---', 'vide', 'Vide'}
    cleaned_ports = set()
    removed = []

    for port in cities:
        port_str = str(port).strip()

        # Skip placeholders
        if port_str in placeholders:
            removed.append(f"{port_str} (placeholder)")
            continue

        # Skip empty or too short
        if not port_str or len(port_str) <= 1:
            removed.append(f"{port_str} (too short)")
            continue

        # Skip if purely numeric
        if port_str.isdigit():
            removed.append(f"{port_str} (numeric)")
            continue

        cleaned_ports.add(port_str)

    print(f"\nCleaned canonical ports: {len(cleaned_ports)}")
    print(f"Removed {len(removed)} invalid entries:")
    for entry in removed[:10]:
        print(f"  - {entry}")
    if len(removed) > 10:
        print(f"  ... and {len(removed) - 10} more")

    # Show some statistics
    port_frequencies = df['City'].value_counts()
    print(f"\nPort frequency distribution:")
    print(f"  Ports with 1-3 total cargoes: {len(port_frequencies[port_frequencies <= 3])}")
    print(f"  Ports with 4-10 cargoes: {len(port_frequencies[(port_frequencies > 3) & (port_frequencies <= 10)])}")
    print(f"  Ports with >10 cargoes: {len(port_frequencies[port_frequencies > 10])}")

    print(f"\nTop 20 origin ports by cargo frequency:")
    for i, (port, count) in enumerate(port_frequencies.head(20).items(), 1):
        if port in cleaned_ports:
            print(f"  {i:2}. {port:30} {count:4} cargoes")

    return sorted(cleaned_ports)


def extract_canonical_destination_ports(excel_path: Path) -> list:
    """
    Extract canonical destination ports from Timber Trades Journal Data.

    Coverage: 1 year (1888)
    Source: England & Wales + Scotland sheets -> Port of Entry column
    """
    print("\n" + "=" * 80)
    print("EXTRACTING CANONICAL DESTINATION PORTS")
    print("=" * 80)

    xls = pd.ExcelFile(excel_path)
    dest_ports = set()

    for sheet_name in ['England & Wales', 'Scotland']:
        df = pd.read_excel(xls, sheet_name=sheet_name)

        if 'Port of Entry' in df.columns:
            ports = df['Port of Entry'].dropna().unique()
            dest_ports.update(ports)
            print(f"{sheet_name}: {len(ports)} destination ports")

    # Clean
    cleaned_ports = set()
    for port in dest_ports:
        port_str = str(port).strip()
        if port_str and len(port_str) > 1:
            cleaned_ports.add(port_str)

    print(f"\nTotal unique British destination ports: {len(cleaned_ports)}")

    # Group by base city (before dock/wharf details)
    base_cities = set()
    london_details = []

    for port in sorted(cleaned_ports):
        if port.startswith('London ('):
            london_details.append(port)
        else:
            base_cities.add(port)

    print(f"\nBreakdown:")
    print(f"  Base cities/ports: {len(base_cities)}")
    print(f"  London with dock details: {len(london_details)}")

    print(f"\nLondon dock variations (first 10):")
    for dock in london_details[:10]:
        print(f"  - {dock}")
    if len(london_details) > 10:
        print(f"  ... and {len(london_details) - 10} more")

    return sorted(cleaned_ports)


def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    output_dir = base_dir / "reference_data"
    output_dir.mkdir(exist_ok=True)

    print("CANONICAL PORT EXTRACTION")
    print("Source: Human-transcribed Excel files")
    print()

    # Extract origin ports
    origin_ports = extract_canonical_origin_ports(
        base_dir / "London Timber imports data ttj.xlsx"
    )

    # Extract destination ports
    destination_ports = extract_canonical_destination_ports(
        base_dir / "Timber Trades Journal Data.xlsx"
    )

    # Save to JSON
    print("\n" + "=" * 80)
    print("SAVING CANONICAL PORT LISTS")
    print("=" * 80)

    origin_file = output_dir / "canonical_origin_ports.json"
    with open(origin_file, 'w', encoding='utf-8') as f:
        json.dump(origin_ports, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(origin_ports)} origin ports to: {origin_file}")

    dest_file = output_dir / "canonical_destination_ports.json"
    with open(dest_file, 'w', encoding='utf-8') as f:
        json.dump(destination_ports, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(destination_ports)} destination ports to: {dest_file}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Canonical origin ports: {len(origin_ports)} (from 3 years: 1883, 1889, 1897)")
    print(f"Canonical destination ports: {len(destination_ports)} (from 1 year: 1888)")
    print("\nNOTE: Origin list is comprehensive; destination list may miss some ports")
    print("      from other years. Human review will identify legitimate unmapped ports.")
    print("=" * 80)


if __name__ == '__main__':
    main()
