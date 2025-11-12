#!/usr/bin/env python3
"""
Apply context-based dock assignments using proximity analysis.
Corrects Phase 1 errors for VICTORIA DOCK, QUEEN'S DOCK, and UNION DOCK.
"""

import csv
from collections import defaultdict
import re
csv.field_size_limit(1000000)

def load_all_records_by_location(input_csv):
    """Load all records grouped by source file and line number."""
    all_records = defaultdict(lambda: defaultdict(dict))
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row['source_file']
            try:
                line_num = int(row['line_number'])
            except:
                continue
            
            all_records[source][line_num] = {
                'destination': row['destination_port'],
                'ship': row['ship_name'],
                'origin': row['origin_port']
            }
    
    return all_records

def check_dock_proximity(source, line_num, all_records, window=5):
    """Check for nearby dock mentions within window lines."""
    london_docks = [
        'TILBURY', 'SURREY COMMERCIAL', 'MILLWALL', 'WEST INDIA',
        'ROYAL ALBERT', 'LONDON DOCK', 'EAST INDIA', 'DEPTFORD',
        'GREENWICH', 'REGENT', 'ST. KATHARINE', 'WOOLWICH'
    ]
    
    hull_docks = ['ALEXANDRA DOCK', 'HUMBER']
    
    nearby = {'london': [], 'hull': []}
    
    for offset in range(-window, window + 1):
        if offset == 0:
            continue
        check_line = line_num + offset
        
        if check_line in all_records[source]:
            dest = all_records[source][check_line]['destination'].upper()
            
            for dock in london_docks:
                if dock in dest:
                    nearby['london'].append(dock)
            
            for dock in hull_docks:
                if dock in dest:
                    nearby['hull'].append(dock)
    
    return nearby

def assign_victoria_dock(origin, source, line_num, all_records):
    """Assign VICTORIA DOCK to Hull or London based on proximity and origin."""
    # Check proximity first
    nearby = check_dock_proximity(source, line_num, all_records)
    
    if nearby['london'] and not nearby['hull']:
        return "London (Victoria Dock)"
    elif nearby['hull'] and not nearby['london']:
        return "Hull (Victoria Dock)"
    
    # Use origin heuristics
    hull_origins = ['Riga', 'Kronstadt', 'Cronstadt', 'Danzig', 'Stettin', 
                    'Konigsberg', 'Wyborg', 'Archangel', 'Kotka', 'Helsingfors',
                    'Gefle', 'Sundswall', 'Drammen']
    
    london_origins = ['Boston', 'Montreal', 'Halifax']
    
    if any(h in origin for h in hull_origins):
        return "Hull (Victoria Dock)"
    elif origin in london_origins:
        return "London (Victoria Dock)"
    
    # Default to Hull (larger timber Victoria Dock)
    return "Hull (Victoria Dock)"

def assign_queens_dock(origin, source, line_num, all_records, year):
    """Assign QUEEN'S DOCK based on context."""
    # Check proximity
    nearby = check_dock_proximity(source, line_num, all_records)
    
    if nearby['london'] and not nearby['hull']:
        return "London (Queen's Dock)"
    elif nearby['hull'] and not nearby['london']:
        return "Hull (Queen's Dock)"
    
    # Hull's Queen's Dock was for timber, Grimsby's was for fish
    # Most timber cargoes from Baltic/Scandinavian → Hull
    hull_origins = ['Riga', 'Danzig', 'Konigsberg', 'Stettin', 'Christiania',
                    'Sundswall', 'Gefle', 'Archangel']
    
    if any(h in origin for h in hull_origins):
        return "Hull (Queen's Dock)"
    
    # Default to Hull after 1885 (when timber trade was active)
    try:
        if int(year) >= 1885:
            return "Hull (Queen's Dock)"
    except:
        pass
    
    return "Liverpool (Queen's Dock)"

def assign_union_dock(origin, source, line_num, all_records):
    """Assign UNION DOCK based on context."""
    nearby = check_dock_proximity(source, line_num, all_records)
    
    if nearby['london'] and not nearby['hull']:
        return "London (Union Dock)"
    elif nearby['hull'] and not nearby['london']:
        return "Hull (Union Dock)"
    
    # Default to Hull (Union Dock was part of Victoria/Albert dock complex)
    return "Hull (Union Dock)"

def apply_corrections(input_csv, output_csv):
    """Apply proximity-based dock assignments to v4 database."""
    print("Loading all records for proximity analysis...")
    all_records = load_all_records_by_location(input_csv)
    
    print("Applying corrected dock assignments...")
    
    stats = {
        'total': 0,
        'victoria_hull': 0,
        'victoria_london': 0,
        'queens_hull': 0,
        'queens_liverpool': 0,
        'queens_london': 0,
        'union_hull': 0,
        'union_liverpool': 0,
        'union_london': 0,
    }
    
    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                stats['total'] += 1
                
                dest_raw = row['destination_port'].strip()
                dest_norm = row['destination_port_normalized'].strip()
                
                # Check if this needs correction
                if dest_raw == "VICTORIA DOCK":
                    try:
                        line_num = int(row['line_number'])
                        source = row['source_file']
                        origin = row['origin_port']
                        
                        new_dest = assign_victoria_dock(origin, source, line_num, all_records)
                        row['destination_port_normalized'] = new_dest
                        
                        if "Hull" in new_dest:
                            stats['victoria_hull'] += 1
                        else:
                            stats['victoria_london'] += 1
                    except:
                        pass
                
                elif dest_raw == "QUEEN'S DOCK":
                    try:
                        line_num = int(row['line_number'])
                        source = row['source_file']
                        origin = row['origin_port']
                        year = row['publication_year']
                        
                        new_dest = assign_queens_dock(origin, source, line_num, all_records, year)
                        row['destination_port_normalized'] = new_dest
                        
                        if "Hull" in new_dest:
                            stats['queens_hull'] += 1
                        elif "Liverpool" in new_dest:
                            stats['queens_liverpool'] += 1
                        else:
                            stats['queens_london'] += 1
                    except:
                        pass
                
                elif dest_raw == "UNION DOCK":
                    try:
                        line_num = int(row['line_number'])
                        source = row['source_file']
                        origin = row['origin_port']
                        
                        new_dest = assign_union_dock(origin, source, line_num, all_records)
                        row['destination_port_normalized'] = new_dest
                        
                        if "Hull" in new_dest:
                            stats['union_hull'] += 1
                        elif "Liverpool" in new_dest:
                            stats['union_liverpool'] += 1
                        else:
                            stats['union_london'] += 1
                    except:
                        pass
                
                writer.writerow(row)
                
                if stats['total'] % 10000 == 0:
                    print(f"  Processed {stats['total']:,} records...")
    
    return stats

def main():
    from pathlib import Path
    
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    parsed_dir = base_dir / "parsed_output"
    
    print("=" * 80)
    print("APPLYING PROXIMITY-BASED DOCK ASSIGNMENTS (V4.1)")
    print("=" * 80)
    
    input_csv = parsed_dir / "ttj_shipments_normalized_v4.csv"
    output_csv = parsed_dir / "ttj_shipments_normalized_v4.1.csv"
    
    stats = apply_corrections(input_csv, output_csv)
    
    print("\n" + "=" * 80)
    print("CORRECTIONS APPLIED")
    print("=" * 80)
    
    print(f"\nVICTORIA DOCK assignments:")
    print(f"  Hull (Victoria Dock):    {stats['victoria_hull']}")
    print(f"  London (Victoria Dock):  {stats['victoria_london']}")
    
    print(f"\nQUEEN'S DOCK assignments:")
    print(f"  Hull (Queen's Dock):      {stats['queens_hull']}")
    print(f"  Liverpool (Queen's Dock): {stats['queens_liverpool']}")
    print(f"  London (Queen's Dock):    {stats['queens_london']}")
    
    print(f"\nUNION DOCK assignments:")
    print(f"  Hull (Union Dock):       {stats['union_hull']}")
    print(f"  Liverpool (Union Dock):  {stats['union_liverpool']}")
    print(f"  London (Union Dock):     {stats['union_london']}")
    
    print(f"\n✓ Output saved to: {output_csv}")
    print(f"\nHull's corrected total: {stats['victoria_hull'] + stats['queens_hull'] + stats['union_hull'] + 142} ships")
    print("(142 = standalone HULL records)")

if __name__ == '__main__':
    main()
