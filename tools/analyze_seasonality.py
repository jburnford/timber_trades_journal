#!/usr/bin/env python3
"""
Analyze seasonal patterns in ship arrivals to identify anomalies.
Expected: Fewer ships in Nov-Mar (winter), peak in May-Sep (summer shipping season)
"""
import pandas as pd
import numpy as np
from collections import defaultdict

# Load the issue inventory
df = pd.read_csv("/home/jic823/TTJ Forest of Numbers/ttj_issue_inventory.csv")

# Convert to int
df['year'] = df['year'].astype(int)
df['month'] = df['month'].astype(int)
df['ships_parsed'] = df['ships_parsed'].fillna(0).astype(int)

# Only analyze issues with successful OCR
df_ocr = df[df['status'].isin(['OCR_COMPLETE', 'PARTIAL_FAIL'])].copy()

print("SEASONAL PATTERN ANALYSIS - TTJ Ship Arrivals")
print("=" * 80)
print("\nExpected Pattern:")
print("  WINTER (Nov-Mar): Low ship counts (frozen ports, storms)")
print("  SPRING (Apr-May): Rising counts (ice breakup, shipping resumes)")
print("  SUMMER (Jun-Sep): Peak counts (ideal sailing conditions)")
print("  FALL (Oct): Declining counts (preparing for winter)")
print()

# Calculate average ships per issue by month (across all years)
monthly_stats = df_ocr.groupby('month')['ships_parsed'].agg(['mean', 'median', 'sum', 'count'])
monthly_stats['ships_per_issue'] = monthly_stats['sum'] / monthly_stats['count']

print("=" * 80)
print("AVERAGE SHIPS PER ISSUE BY MONTH (All Years Combined)")
print("=" * 80)

month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
               7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

for month in range(1, 13):
    if month in monthly_stats.index:
        stats = monthly_stats.loc[month]
        season = ('WINTER' if month in [11, 12, 1, 2, 3] else
                 'SPRING' if month in [4, 5] else
                 'SUMMER' if month in [6, 7, 8, 9] else 'FALL')

        print(f"{month_names[month]:>3} ({season:>6}): "
              f"{stats['ships_per_issue']:6.1f} ships/issue  "
              f"({int(stats['count']):2d} issues, {int(stats['sum']):5,d} total ships)")
    else:
        print(f"{month_names[month]:>3}: No data")

# Identify the expected pattern (baseline)
winter_months = [11, 12, 1, 2, 3]
summer_months = [6, 7, 8, 9]

winter_avg = monthly_stats.loc[monthly_stats.index.isin(winter_months), 'ships_per_issue'].mean()
summer_avg = monthly_stats.loc[monthly_stats.index.isin(summer_months), 'ships_per_issue'].mean()

print(f"\nBaseline averages:")
print(f"  Winter (Nov-Mar): {winter_avg:.1f} ships/issue")
print(f"  Summer (Jun-Sep): {summer_avg:.1f} ships/issue")
print(f"  Summer:Winter ratio: {summer_avg/winter_avg:.2f}x")

# Now check each year for anomalies
print("\n" + "=" * 80)
print("YEAR-BY-YEAR SEASONAL ANALYSIS (Anomaly Detection)")
print("=" * 80)

anomalies = []

for year in sorted(df_ocr['year'].unique()):
    df_year = df_ocr[df_ocr['year'] == year]

    # Calculate seasonal totals for this year
    winter_ships = df_year[df_year['month'].isin(winter_months)]['ships_parsed'].sum()
    winter_issues = len(df_year[df_year['month'].isin(winter_months)])

    summer_ships = df_year[df_year['month'].isin(summer_months)]['ships_parsed'].sum()
    summer_issues = len(df_year[df_year['month'].isin(summer_months)])

    total_ships = df_year['ships_parsed'].sum()
    total_issues = len(df_year)

    # Calculate per-issue averages
    winter_per_issue = winter_ships / winter_issues if winter_issues > 0 else 0
    summer_per_issue = summer_ships / summer_issues if summer_issues > 0 else 0

    # Check for anomalies
    year_anomalies = []

    # Anomaly 1: Winter higher than summer (inverted seasonality)
    if summer_issues > 0 and winter_issues > 0:
        if winter_per_issue > summer_per_issue:
            year_anomalies.append(f"INVERTED: Winter>{summer} ({winter_per_issue:.0f} vs {summer_per_issue:.0f} ships/issue)")

    # Anomaly 2: Very low summer counts (missing data?)
    if summer_issues > 0 and summer_per_issue < summer_avg * 0.5:
        year_anomalies.append(f"LOW_SUMMER: {summer_per_issue:.0f} ships/issue (expected {summer_avg:.0f})")

    # Anomaly 3: Sparse coverage (< 12 issues for full year)
    if total_issues < 12:
        year_anomalies.append(f"SPARSE: Only {total_issues} issues (incomplete year)")

    # Anomaly 4: Missing entire seasons
    if winter_issues == 0 and summer_issues > 0:
        year_anomalies.append(f"MISSING_WINTER: No winter issues")
    if summer_issues == 0 and winter_issues > 0:
        year_anomalies.append(f"MISSING_SUMMER: No summer issues")

    # Print year summary
    status = "⚠️  ANOMALY" if year_anomalies else "✓ Normal"
    print(f"\n{year} [{status}]:")
    print(f"  Issues: {total_issues} (Winter: {winter_issues}, Summer: {summer_issues})")
    print(f"  Ships: {total_ships:,} total")
    print(f"  Ships/issue: Winter={winter_per_issue:.1f}, Summer={summer_per_issue:.1f}")

    if year_anomalies:
        for anomaly in year_anomalies:
            print(f"    → {anomaly}")
            anomalies.append({'year': year, 'anomaly': anomaly})

# Check for missing months per year
print("\n" + "=" * 80)
print("MONTH COVERAGE BY YEAR (Identifying Gaps)")
print("=" * 80)

for year in sorted(df_ocr['year'].unique()):
    df_year = df_ocr[df_ocr['year'] == year]
    months_present = sorted(df_year['month'].unique())
    months_missing = [m for m in range(1, 13) if m not in months_present]

    if months_missing:
        missing_names = [month_names[m] for m in months_missing]
        print(f"{year}: MISSING {len(months_missing)} months → {', '.join(missing_names)}")

# Check for issues with surprisingly low ship counts
print("\n" + "=" * 80)
print("ISSUES WITH ANOMALOUSLY LOW SHIP COUNTS")
print("=" * 80)
print("(Filtering: Summer issues with <30 ships, Winter issues with <10 ships)")
print()

for _, row in df_ocr.iterrows():
    month = row['month']
    ships = row['ships_parsed']
    issue_date = row['issue_date']

    # Define thresholds by season
    if month in summer_months:
        threshold = 30
        season = "SUMMER"
    elif month in winter_months:
        threshold = 10
        season = "WINTER"
    else:
        continue

    if ships < threshold and ships > 0:
        print(f"{issue_date} ({season:6}): {int(ships):3d} ships (expected >{threshold})")

# Check for issues with zero ships (possible parsing failures)
print("\n" + "=" * 80)
print("ISSUES WITH ZERO SHIPS PARSED")
print("=" * 80)
print("(These may indicate parsing failures, not actual empty issues)")
print()

zero_ship_issues = df_ocr[df_ocr['ships_parsed'] == 0]
if len(zero_ship_issues) > 0:
    for _, row in zero_ship_issues.iterrows():
        print(f"{row['issue_date']} - {row['ocr_files']} OCR file(s), 0 ships")
else:
    print("✓ No issues with zero ships")

# Summary
print("\n" + "=" * 80)
print("ANOMALY SUMMARY")
print("=" * 80)
print(f"\nTotal anomalies detected: {len(anomalies)}")

if anomalies:
    anomaly_types = defaultdict(int)
    for a in anomalies:
        anomaly_type = a['anomaly'].split(':')[0]
        anomaly_types[anomaly_type] += 1

    print("\nBy type:")
    for atype, count in sorted(anomaly_types.items(), key=lambda x: -x[1]):
        print(f"  {atype}: {count} years")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print("""
1. INVERTED SEASONALITY: Check if OCR failed on summer issues
2. LOW_SUMMER: Indicates missing summer issues - check source archives
3. SPARSE: Years with <12 issues need more OCR coverage
4. MISSING_WINTER/SUMMER: Check if specific season archives are missing
5. Zero ships: Likely parser detection failures - need regex improvements
6. Low summer counts (<30): May indicate partial OCR (multi-page issues incomplete)
""")
