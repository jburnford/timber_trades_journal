#!/usr/bin/env python3
"""
Visualize London's timber supply network evolution over time.

Creates:
1. Static maps for different time periods
2. Interactive HTML map with time slider
3. Summary statistics by period
"""

import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

csv.field_size_limit(1000000)

def load_london_shipments(csv_path):
    """Load all shipments to London with complete geocoding."""
    shipments = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter for London destinations with complete geocoding
            dest = row['destination_port_normalized']
            if 'London' in dest:
                # Must have both origin and destination coordinates
                if (row['origin_latitude'] and row['origin_latitude'].strip() and
                    row['origin_longitude'] and row['origin_longitude'].strip() and
                    row['destination_latitude'] and row['destination_latitude'].strip() and
                    row['destination_longitude'] and row['destination_longitude'].strip()):

                    try:
                        shipments.append({
                            'year': int(row['publication_year']),
                            'origin': row['origin_port_normalized'],
                            'origin_lat': float(row['origin_latitude']),
                            'origin_lon': float(row['origin_longitude']),
                            'dest_lat': float(row['destination_latitude']),
                            'dest_lon': float(row['destination_longitude']),
                            'ship_name': row['ship_name'],
                            'cargo': row['cargo']
                        })
                    except (ValueError, TypeError):
                        continue

    return shipments

def group_by_period(shipments, period_years=5):
    """Group shipments into time periods."""
    periods = defaultdict(lambda: defaultdict(list))

    for ship in shipments:
        # Calculate period (e.g., 1875-1879, 1880-1884, etc.)
        start_year = (ship['year'] // period_years) * period_years
        end_year = start_year + period_years - 1
        period_key = f"{start_year}-{end_year}"

        periods[period_key][ship['origin']].append(ship)

    return periods

def create_static_maps(periods, output_dir):
    """Create static maps for each time period."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # London coordinates
    london_lat, london_lon = 51.5074, -0.1278

    # Create figure for all periods
    sorted_periods = sorted(periods.keys())
    n_periods = len(sorted_periods)

    # Calculate grid layout
    ncols = 3
    nrows = (n_periods + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(20, 6*nrows))
    if nrows == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    # Process each period
    for idx, period in enumerate(sorted_periods):
        ax = axes[idx]
        origins = periods[period]

        # Aggregate origin data
        origin_data = []
        for origin_name, ships in origins.items():
            count = len(ships)
            # Use first ship's coordinates (all should be same for same origin)
            lat = ships[0]['origin_lat']
            lon = ships[0]['origin_lon']
            origin_data.append({
                'name': origin_name,
                'lat': lat,
                'lon': lon,
                'count': count
            })

        # Sort by ship count
        origin_data.sort(key=lambda x: x['count'], reverse=True)

        # Set map bounds (Europe and North Atlantic)
        ax.set_xlim(-80, 35)
        ax.set_ylim(35, 70)

        # Draw coastline approximation
        ax.axhline(y=50, color='lightgray', linewidth=0.5, alpha=0.3)
        ax.axvline(x=0, color='lightgray', linewidth=0.5, alpha=0.3)

        # Plot London
        ax.plot(london_lon, london_lat, 'r*', markersize=20,
                label='London', zorder=100)

        # Plot routes and origins
        max_ships = max(o['count'] for o in origin_data) if origin_data else 1

        for origin in origin_data[:30]:  # Top 30 origins
            # Scale marker size by ship count (logarithmic)
            size = 50 + 200 * (np.log(origin['count']) / np.log(max_ships))

            # Draw line from origin to London
            ax.plot([origin['lon'], london_lon],
                   [origin['lat'], london_lat],
                   'b-', linewidth=0.5, alpha=0.2, zorder=1)

            # Plot origin port
            ax.scatter(origin['lon'], origin['lat'],
                      s=size, c='blue', alpha=0.6,
                      edgecolors='darkblue', linewidth=0.5, zorder=50)

            # Label top 5 origins
            if origin in origin_data[:5]:
                ax.text(origin['lon'], origin['lat'],
                       f"  {origin['name']}\n  ({origin['count']})",
                       fontsize=7, ha='left', va='center')

        # Title and stats
        total_ships = sum(o['count'] for o in origin_data)
        n_origins = len(origin_data)
        ax.set_title(f"{period}\n{total_ships:,} ships from {n_origins} origins",
                    fontsize=12, fontweight='bold')

        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

    # Hide unused subplots
    for idx in range(n_periods, len(axes)):
        axes[idx].axis('off')

    # Add overall title
    fig.suptitle("London's Timber Supply Network Evolution (1874-1899)",
                fontsize=16, fontweight='bold', y=0.995)

    plt.tight_layout()

    # Save figure
    output_path = output_dir / "london_supply_network_evolution.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved static map: {output_path}")

    plt.close()

    return output_path

def create_summary_report(periods, output_dir):
    """Create summary statistics report."""
    output_dir = Path(output_dir)

    report = []
    report.append("=" * 80)
    report.append("LONDON'S TIMBER SUPPLY NETWORK - SUMMARY STATISTICS")
    report.append("=" * 80)

    for period in sorted(periods.keys()):
        origins = periods[period]
        total_ships = sum(len(ships) for ships in origins.values())
        n_origins = len(origins)

        # Get top 10 origins
        origin_counts = [(name, len(ships)) for name, ships in origins.items()]
        origin_counts.sort(key=lambda x: x[1], reverse=True)

        report.append(f"\n{period}")
        report.append("-" * 40)
        report.append(f"Total ships: {total_ships:,}")
        report.append(f"Origin ports: {n_origins}")
        report.append(f"\nTop 10 Origins:")

        for i, (origin, count) in enumerate(origin_counts[:10], 1):
            pct = 100 * count / total_ships
            report.append(f"  {i:2}. {origin:30} {count:5,} ships ({pct:5.1f}%)")

    # Overall statistics
    report.append(f"\n{'=' * 80}")
    report.append("OVERALL STATISTICS (1874-1899)")
    report.append("=" * 80)

    all_origins = Counter()
    total_all = 0

    for period_origins in periods.values():
        for origin, ships in period_origins.items():
            all_origins[origin] += len(ships)
            total_all += len(ships)

    report.append(f"\nTotal ships to London: {total_all:,}")
    report.append(f"Unique origin ports: {len(all_origins)}")
    report.append(f"\nTop 20 Origins (All Years):")

    for i, (origin, count) in enumerate(all_origins.most_common(20), 1):
        pct = 100 * count / total_all
        report.append(f"  {i:2}. {origin:30} {count:5,} ships ({pct:5.1f}%)")

    # Save report
    report_text = "\n".join(report)
    report_path = output_dir / "london_supply_network_report.txt"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"✓ Saved summary report: {report_path}")

    # Also print to console
    print("\n" + report_text)

    return report_path

def create_interactive_data(periods, output_dir):
    """Create JSON data for interactive visualization."""
    output_dir = Path(output_dir)

    # London coordinates
    london_lat, london_lon = 51.5074, -0.1278

    data = {
        'london': {'lat': london_lat, 'lon': london_lon},
        'periods': {}
    }

    for period, origins in periods.items():
        period_data = {
            'origins': []
        }

        for origin_name, ships in origins.items():
            count = len(ships)
            lat = ships[0]['origin_lat']
            lon = ships[0]['origin_lon']

            period_data['origins'].append({
                'name': origin_name,
                'lat': lat,
                'lon': lon,
                'count': count
            })

        # Sort by count
        period_data['origins'].sort(key=lambda x: x['count'], reverse=True)
        data['periods'][period] = period_data

    # Save JSON
    json_path = output_dir / "london_supply_network_data.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Saved interactive data: {json_path}")

    return json_path

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")

    print("=" * 80)
    print("VISUALIZING LONDON'S TIMBER SUPPLY NETWORK")
    print("=" * 80)

    # Load data
    print("\nLoading geocoded shipments to London...")
    csv_path = base_dir / "parsed_output" / "ttj_shipments_geocoded.csv"
    shipments = load_london_shipments(csv_path)
    print(f"  Loaded {len(shipments):,} complete routes to London")

    if len(shipments) == 0:
        print("\nError: No geocoded shipments found for London")
        return

    # Group by time period
    print("\nGrouping by 5-year periods...")
    periods = group_by_period(shipments, period_years=5)
    print(f"  Created {len(periods)} time periods")

    # Create output directory
    output_dir = base_dir / "analysis" / "london_supply_network"
    output_dir.mkdir(exist_ok=True, parents=True)

    # Create visualizations
    print("\nCreating visualizations...")
    create_static_maps(periods, output_dir)
    create_summary_report(periods, output_dir)
    create_interactive_data(periods, output_dir)

    print("\n" + "=" * 80)
    print("VISUALIZATION COMPLETE")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("\nFiles created:")
    print("  - london_supply_network_evolution.png (static map)")
    print("  - london_supply_network_report.txt (statistics)")
    print("  - london_supply_network_data.json (interactive data)")

if __name__ == '__main__':
    main()
