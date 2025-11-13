#!/usr/bin/env python3
"""Check if Porsgrunn coordinates match any existing GeoJSON ports"""

import json
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# Porsgrunn coordinates to check
porsgrunn_lat = 59.115556
porsgrunn_lon = 9.71

# Load GeoJSON
with open('../Ports_Master.geojson', 'r', encoding='utf-8') as f:
    geojson = json.load(f)

print(f"Checking for ports within 5km of Porsgrunn ({porsgrunn_lat}, {porsgrunn_lon})...\n")

matches = []
for feature in geojson['features']:
    if feature['geometry']['type'] == 'Point':
        coords = feature['geometry']['coordinates']
        lon, lat = coords[0], coords[1]

        distance = haversine_distance(porsgrunn_lat, porsgrunn_lon, lat, lon)

        if distance < 5:
            port_name = feature['properties'].get('Name', 'Unknown')
            matches.append({
                'name': port_name,
                'lat': lat,
                'lon': lon,
                'distance_km': round(distance, 2)
            })

if matches:
    print(f"Found {len(matches)} port(s) within 5km:")
    for match in matches:
        print(f"  - {match['name']}: ({match['lat']}, {match['lon']}) - {match['distance_km']} km away")
else:
    print("No duplicates found. Porsgrunn coordinates are unique.")
