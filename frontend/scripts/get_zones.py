#!/usr/bin/env python3
"""
Extract real Bengaluru zone boundaries from OpenStreetMap using osmnx.

Usage:
    python scripts/get_zones.py

Output:
    public/urjayukti_zones_raw.geojson
"""

import osmnx as ox
import geopandas as gpd
import json
from pathlib import Path

# Define zones to extract
ZONES = [
    "Whitefield, Bengaluru",
    "HSR Layout, Bengaluru",
    "Indiranagar, Bengaluru",
    "Koramangala, Bengaluru",
    "Electronic City, Bengaluru",
    "Marathahalli, Bengaluru",
]

def extract_zone_boundaries():
    """Extract zone boundaries from OpenStreetMap."""
    zones = {}

    for name in ZONES:
        try:
            print(f"Extracting {name}...")
            gdf = ox.geocode_to_gdf(name)
            zones[name] = gdf
            vertices = len(gdf.geometry.iloc[0].exterior.coords)
            print(f"  [OK] {name}: {vertices} vertices")
        except Exception as e:
            print(f"  [X] {name}: {e}")

    if not zones:
        raise ValueError("No zones extracted successfully")

    # Merge all zones into one GeoDataFrame
    combined = gpd.pd.concat(zones.values(), ignore_index=True)

    # Add zone names as properties
    combined['name'] = list(zones.keys())

    # Convert to GeoJSON
    geojson = json.loads(combined.to_json())

    # Save to public directory
    output_path = Path("public/urjayukti_zones_raw.geojson")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"\n[OK] Saved: {output_path}")
    print(f"   Total zones: {len(geojson['features'])}")

if __name__ == "__main__":
    extract_zone_boundaries()
