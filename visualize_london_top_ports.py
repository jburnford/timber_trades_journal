#!/usr/bin/env python3
"""
Create visualization of top 10 origin ports to London for specific years
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

# Read the data
df = pd.read_csv('analysis/london_origin_port_counts_by_year.csv')

# Selected years
years = [1875, 1879, 1881, 1883, 1885, 1887, 1889, 1891, 1893, 1895]

# Create figure with subplots (2 rows, 5 columns)
fig, axes = plt.subplots(2, 5, figsize=(20, 10))
fig.suptitle('Top 10 Origin Ports to London by Year\nTimber Trades Journal Data',
             fontsize=16, fontweight='bold', y=0.98)

# Flatten axes for easier iteration
axes = axes.flatten()

# Color palette - using a warm palette for timber trade theme
colors = plt.cm.YlOrBr(np.linspace(0.3, 0.8, 10))

# Process each year
for idx, year in enumerate(years):
    ax = axes[idx]

    # Filter data for this year
    year_data = df[df['year'] == year].copy()

    if len(year_data) == 0:
        ax.text(0.5, 0.5, f'No data for {year}',
                ha='center', va='center', fontsize=12)
        ax.set_title(f'{year}', fontweight='bold', fontsize=12)
        ax.axis('off')
        continue

    # Get top 10 ports
    top10 = year_data.nlargest(10, 'ship_count')

    # Create horizontal bar chart
    bars = ax.barh(range(len(top10)), top10['ship_count'], color=colors[:len(top10)])

    # Set y-axis labels (port names)
    ax.set_yticks(range(len(top10)))
    ax.set_yticklabels(top10['origin_port'], fontsize=9)

    # Add ship counts at the end of bars
    for i, (port, count) in enumerate(zip(top10['origin_port'], top10['ship_count'])):
        ax.text(count + 1, i, f'{int(count)}',
                va='center', fontsize=8, fontweight='bold')

    # Styling
    ax.set_xlabel('Ships', fontsize=9)
    ax.set_title(f'{year} ({int(year_data["ship_count"].sum())} total ships)',
                 fontweight='bold', fontsize=11)
    ax.invert_yaxis()  # Top port at the top
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Set x-axis limit with some padding
    max_count = top10['ship_count'].max()
    ax.set_xlim(0, max_count * 1.15)

plt.tight_layout(rect=[0, 0.03, 1, 0.96])

# Save figure
output_file = 'analysis/london_top10_ports_by_year.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✅ Saved visualization: {output_file}")

# Also create a summary table
print("\n" + "="*80)
print("SUMMARY: TOP 10 PORTS TO LONDON BY YEAR")
print("="*80)

for year in years:
    year_data = df[df['year'] == year]
    if len(year_data) == 0:
        print(f"\n{year}: No data")
        continue

    total = year_data['ship_count'].sum()
    top10 = year_data.nlargest(10, 'ship_count')
    top10_total = top10['ship_count'].sum()

    print(f"\n{year} - Total: {int(total)} ships | Top 10: {int(top10_total)} ships ({top10_total/total*100:.1f}%)")
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        port = row['origin_port']
        count = int(row['ship_count'])
        pct = count / total * 100
        print(f"  {i:2d}. {port:20s} {count:4d} ships ({pct:5.1f}%)")

plt.show()
