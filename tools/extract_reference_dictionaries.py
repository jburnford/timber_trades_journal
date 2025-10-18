#!/usr/bin/env python3
"""
Extract normalization dictionaries from human-transcribed Excel files.
Creates reference lists for ports, commodities, and units.
"""

import pandas as pd
import json
from pathlib import Path
from collections import Counter
import re


def extract_ports_from_excel(excel_dir: Path):
    """Extract all unique port names from human transcriptions."""

    ports = set()

    # File 1: Export Ports - canonical list
    print("Extracting from Export Ports.xlsx...")
    df = pd.read_excel(excel_dir / "Export Ports.xlsx", sheet_name="Export ports")
    canonical_ports = df['Port of Origin'].dropna().unique()
    ports.update(canonical_ports)
    print(f"  Added {len(canonical_ports)} canonical export ports")

    # File 2: London imports - origin ports
    print("\nExtracting from London Timber imports data ttj.xlsx...")
    xls = pd.ExcelFile(excel_dir / "London Timber imports data ttj.xlsx")

    # 1883 sheet
    df = pd.read_excel(xls, sheet_name="London imports 1883")
    if "Ville d'origine" in df.columns:
        origin_ports = df["Ville d'origine"].dropna().unique()
        ports.update(origin_ports)
        print(f"  1883: Added {len(origin_ports)} ports")

    # 1889 sheet
    df = pd.read_excel(xls, sheet_name="Lon imp. 1889")
    if "Port de départ" in df.columns:
        origin_ports = df["Port de départ"].dropna().unique()
        ports.update(origin_ports)
        print(f"  1889: Added {len(origin_ports)} ports")

    # 1897 sheet
    df = pd.read_excel(xls, sheet_name="Lon imp.1897")
    if "Port de départ" in df.columns:
        origin_ports = df["Port de départ"].dropna().unique()
        ports.update(origin_ports)
        print(f"  1897: Added {len(origin_ports)} ports")

    # File 3: Timber Trades Journal Data
    print("\nExtracting from Timber Trades Journal Data.xlsx...")
    xls = pd.ExcelFile(excel_dir / "Timber Trades Journal Data.xlsx")

    for sheet in ["England & Wales", "Scotland", "Canada"]:
        df = pd.read_excel(xls, sheet_name=sheet)

        # Origin ports
        if "Port of Origin" in df.columns:
            origin_ports = df["Port of Origin"].dropna().unique()
            ports.update(origin_ports)
            print(f"  {sheet}: Added {len(origin_ports)} origin ports")

        # Entry ports (destinations)
        if "Port of Entry" in df.columns:
            entry_ports = df["Port of Entry"].dropna().unique()
            ports.update(entry_ports)
            print(f"  {sheet}: Added {len(entry_ports)} entry ports")

    # Clean and normalize
    cleaned_ports = set()
    for port in ports:
        port_str = str(port).strip()
        if port_str and len(port_str) > 1 and not port_str.isdigit():
            cleaned_ports.add(port_str)

    return sorted(cleaned_ports)


def extract_commodities_from_excel(excel_dir: Path):
    """Extract all unique commodity names from human transcriptions."""

    commodities = Counter()

    print("\nExtracting commodities from London Timber imports data ttj.xlsx...")
    xls = pd.ExcelFile(excel_dir / "London Timber imports data ttj.xlsx")

    # Check if there's a commodities sheet
    if "commodities" in xls.sheet_names:
        print("  Found 'commodities' sheet")
        df = pd.read_excel(xls, sheet_name="commodities")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Shape: {df.shape}")
        # Show first few rows to understand structure
        print(f"  First 5 rows:")
        print(df.head().to_string())

    # Extract from import sheets
    for sheet in ["London imports 1883", "Lon imp. 1889", "Lon imp.1897"]:
        df = pd.read_excel(xls, sheet_name=sheet)

        # Look for product/commodity columns
        product_col = None
        if "Produit" in df.columns:
            product_col = "Produit"
        elif "Produits" in df.columns:
            product_col = "Produits"
        elif "Product" in df.columns:
            product_col = "Product"

        if product_col:
            products = df[product_col].dropna()
            for prod in products:
                prod_str = str(prod).strip().lower()
                if prod_str and len(prod_str) > 2:
                    commodities[prod_str] += 1
            print(f"  {sheet}: Found {len(products)} commodity entries")

    return commodities


def extract_units_from_excel(excel_dir: Path):
    """Extract all unit abbreviations from human transcriptions."""

    units = Counter()

    print("\nExtracting units from London Timber imports data ttj.xlsx...")
    xls = pd.ExcelFile(excel_dir / "London Timber imports data ttj.xlsx")

    for sheet in ["London imports 1883", "Lon imp. 1889", "Lon imp.1897"]:
        df = pd.read_excel(xls, sheet_name=sheet)

        # Look for unit columns
        unit_col = None
        if "Unité" in df.columns:
            unit_col = "Unité"
        elif "Unités" in df.columns:
            unit_col = "Unités"
        elif "Unit" in df.columns:
            unit_col = "Unit"

        if unit_col:
            unit_vals = df[unit_col].dropna()
            for unit in unit_vals:
                unit_str = str(unit).strip().lower()
                if unit_str and len(unit_str) > 0:
                    units[unit_str] += 1
            print(f"  {sheet}: Found {len(unit_vals)} unit entries")

    return units


def analyze_parsed_data_variants(csv_path: Path):
    """Analyze our parsed data to find port and commodity variants."""

    import csv as csvmod
    csvmod.field_size_limit(1000000)

    print("\nAnalyzing parsed data for variants...")

    origin_ports = Counter()
    dest_ports = Counter()

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csvmod.DictReader(f)
        for row in reader:
            if row['origin_port']:
                origin_ports[row['origin_port'].strip()] += 1
            if row['destination_port']:
                dest_ports[row['destination_port'].strip()] += 1

    print(f"  Found {len(origin_ports)} unique origin ports in parsed data")
    print(f"  Found {len(dest_ports)} unique destination ports in parsed data")

    return origin_ports, dest_ports


def main():
    excel_dir = Path("/home/jic823/TTJ Forest of Numbers")
    csv_path = Path("/home/jic823/TTJ Forest of Numbers/parsed_output/ttj_shipments_multipage.csv")
    output_dir = Path("/home/jic823/TTJ Forest of Numbers/reference_data")
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("EXTRACTING REFERENCE DICTIONARIES")
    print("=" * 80)

    # Extract from human transcriptions
    canonical_ports = extract_ports_from_excel(excel_dir)
    commodities = extract_commodities_from_excel(excel_dir)
    units = extract_units_from_excel(excel_dir)

    # Analyze parsed data
    origin_ports, dest_ports = analyze_parsed_data_variants(csv_path)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Canonical ports: {len(canonical_ports)}")
    print(f"Commodity types: {len(commodities)}")
    print(f"Unit types: {len(units)}")
    print(f"Origin ports in parsed data: {len(origin_ports)}")
    print(f"Destination ports in parsed data: {len(dest_ports)}")

    # Save to JSON files
    print("\n" + "=" * 80)
    print("SAVING DICTIONARIES")
    print("=" * 80)

    # Canonical ports
    with open(output_dir / "canonical_ports.json", 'w', encoding='utf-8') as f:
        json.dump(canonical_ports, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved: {output_dir / 'canonical_ports.json'}")

    # Commodities
    with open(output_dir / "commodities.json", 'w', encoding='utf-8') as f:
        json.dump(dict(commodities.most_common()), f, indent=2, ensure_ascii=False)
    print(f"✓ Saved: {output_dir / 'commodities.json'}")

    # Units
    with open(output_dir / "units.json", 'w', encoding='utf-8') as f:
        json.dump(dict(units.most_common()), f, indent=2, ensure_ascii=False)
    print(f"✓ Saved: {output_dir / 'units.json'}")

    # Parsed data ports
    with open(output_dir / "parsed_origin_ports.json", 'w', encoding='utf-8') as f:
        json.dump(dict(origin_ports.most_common()), f, indent=2, ensure_ascii=False)
    print(f"✓ Saved: {output_dir / 'parsed_origin_ports.json'}")

    with open(output_dir / "parsed_destination_ports.json", 'w', encoding='utf-8') as f:
        json.dump(dict(dest_ports.most_common()), f, indent=2, ensure_ascii=False)
    print(f"✓ Saved: {output_dir / 'parsed_destination_ports.json'}")

    # Show top commodities and units
    print("\n" + "=" * 80)
    print("TOP 30 COMMODITIES (from human transcripts)")
    print("=" * 80)
    for commodity, count in commodities.most_common(30):
        print(f"  {commodity:40} {count:>6,}")

    print("\n" + "=" * 80)
    print("TOP 20 UNITS (from human transcripts)")
    print("=" * 80)
    for unit, count in units.most_common(20):
        print(f"  {unit:15} {count:>6,}")

    print("\n" + "=" * 80)
    print("TOP 30 ORIGIN PORTS (from parsed data)")
    print("=" * 80)
    for port, count in origin_ports.most_common(30):
        print(f"  {port:30} {count:>6,}")


if __name__ == '__main__':
    main()
