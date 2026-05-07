# Mapbox Zone Map Implementation

## Overview

This document describes the Mapbox zone map implementation for UrjaYukti AI, including the data pipeline, null-safe expression handling, and camera control.

## Architecture

### Data Pipeline

1. **osmnx Extraction** (`scripts/get_zones.py`)
   - Downloads real Bengaluru zone boundaries from OpenStreetMap
   - Produces `urjayukti_zones_raw.geojson` with ~300 vertices per zone

2. **Mapshaper Simplification** (`scripts/simplify_zones.sh`)
   - Reduces vertex count by 15% while preserving road-hugging shape
   - Produces `urjayukti_zones.geojson`

3. **Zone Enrichment** (`scripts/enrich_zones.js`)
   - Adds EV data (load, risk, headroom, etc.) to each zone
   - Produces `urjayukti_zones_enriched.geojson`

### Mapbox Layers

- **zone-fill**: Fill layer with null-safe opacity expression
- **zone-stroke**: Outline layer with null-safe width/opacity
- **zone-halo**: Glow effect for selected zone
- **zone-labels**: Custom labels (Mapbox labels hidden)
- **zone-load-badge**: Load percentage badge
- **demand-nodes-bg**: Demand node circles

### Null-Safe Expressions

Mapbox's C++ engine crashes when comparing feature properties to JavaScript null. We intercept null values in JavaScript using helper functions in `src/lib/mapboxHelpers.ts`:

- `toSafe()`: Convert null to empty string
- `anyZone()`: Check if value is not null
- `getFillOpacity()`, `getLineWidth()`, etc.: Return flat value when nothing selected, case expression when zone selected

### Camera Control

- `fitBounds()` with padding for stats panel (320px right)
- `maxZoom: 15` to prevent over-zooming
- 1s duration with easeInOutCubic easing

## Running the Data Pipeline

```bash
# Install dependencies
pip install osmnx geopandas shapely
npm install -g mapshaper

# Extract zones
python scripts/get_zones.py

# Simplify
bash scripts/simplify_zones.sh

# Enrich
node scripts/enrich_zones.js
```

## Troubleshooting

### Mapbox Expression Errors

If you see "Invalid expression" errors in console:
- Check that all case expressions have at least 3 arguments
- Verify no conditional spread operators in expressions
- Use helper functions from `mapboxHelpers.ts`

### Label Clash

If you see overlapping labels:
- Verify Mapbox labels are hidden on style.load
- Check console for "Hidden Mapbox label layers" message

### Camera Not Framing Correctly

If camera zooms to wrong spot:
- Verify fitBounds padding includes right: 320
- Check that maxZoom is set to 15
- Ensure bounding box is calculated from real coordinates
