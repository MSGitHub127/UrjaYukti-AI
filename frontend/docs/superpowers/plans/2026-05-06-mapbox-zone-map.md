# Mapbox Zone Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement high-fidelity Mapbox zone map with real Bengaluru ward boundaries, null-safe Mapbox expressions, custom labels, and camera swoop effects.

**Architecture:** Mapbox GL JS map with GeoJSON zone data source, multiple paint layers (fill, stroke, halo, labels), null-safe expression helpers, and fitBounds camera control with panel-aware padding.

**Tech Stack:** Mapbox GL JS, React, TypeScript, osmnx (Python), Mapshaper CLI, @turf/turf

---

## File Structure

```
frontend/
├── public/
│   └── urjayukti_zones_enriched.geojson  [CREATE] - Final zone boundaries with EV data
├── scripts/
│   ├── get_zones.py                       [CREATE] - osmnx extraction script
│   └── enrich_zones.js                    [CREATE] - GeoJSON enrichment script
├── src/
│   ├── components/maps/
│   │   └── ZoneHeatMap.tsx               [MODIFY] - Main map component
│   ├── lib/
│   │   ├── mapLayers.ts                  [MODIFY] - Layer specifications
│   │   └── mapboxHelpers.ts              [CREATE] - Null-safe expression helpers
│   └── data/
│       └── bengaluru-zones.json         [REPLACE] - Real shapefile data
```

---

## Task 1: Create Null-Safe Mapbox Expression Helpers

**Files:**
- Create: `src/lib/mapboxHelpers.ts`

- [ ] **Step 1: Write the helper functions**

```typescript
// src/lib/mapboxHelpers.ts

/**
 * Null-safe Mapbox expression helpers
 *
 * Mapbox's C++ engine crashes when comparing feature properties to JavaScript null.
 * These helpers intercept null values in JavaScript BEFORE passing to Mapbox.
 */

/**
 * Convert null/undefined to empty string for safe Mapbox comparisons
 */
export const toSafe = (value: string | null | undefined): string => value ?? "";

/**
 * Check if a value is not null or undefined
 */
export const anyZone = (value: string | null | undefined): boolean =>
  value !== null && value !== undefined;

/**
 * Get fill opacity expression - null-safe
 * Returns flat value when nothing selected, case expression when zone selected
 */
export function getFillOpacity(selected: string | null): number | any {
  if (!anyZone(selected)) return 0.16;
  return [
    "case",
    ["==", ["get", "id"], toSafe(selected)],
    0.32,  // selected zone opacity
    0.04,  // faded zone opacity
  ];
}

/**
 * Get line width expression - null-safe
 * Returns flat value when nothing selected, case expression when zone selected
 */
export function getLineWidth(selected: string | null): number | any {
  if (!anyZone(selected)) return 1.4;
  return [
    "case",
    ["==", ["get", "id"], toSafe(selected)],
    3.2,  // selected zone width
    0.5,  // faded zone width
  ];
}

/**
 * Get line opacity expression - null-safe
 */
export function getLineOpacity(selected: string | null): number | any {
  if (!anyZone(selected)) return 0.85;
  return [
    "case",
    ["==", ["get", "id"], toSafe(selected)],
    1.0,  // selected zone opacity
    0.12, // faded zone opacity
  ];
}

/**
 * Get filter expression for cyan perimeter - null-safe
 */
export function getCyanFilter(selected: string | null): any {
  if (!anyZone(selected)) return ["==", ["get", "id"], ""];
  return ["==", ["get", "id"], toSafe(selected)];
}

/**
 * Get label color expression - null-safe
 */
export function getLabelColor(selected: string | null): any {
  if (!anyZone(selected)) return ["get", "risk_color"];
  return [
    "case",
    ["==", ["get", "id"], toSafe(selected)],
    "#00E5FF",  // cyan when selected
    ["get", "risk_color"],  // zone color when not selected
  ];
}

/**
 * Get label opacity expression - null-safe
 */
export function getLabelOpacity(selected: string | null): number | any {
  if (!anyZone(selected)) return 1.0;
  return [
    "case",
    ["==", ["get", "id"], toSafe(selected)],
    1.0,  // selected zone label opacity
    0.25, // faded zone label opacity
  ];
}
```

- [ ] **Step 2: Commit**

```bash
git add src/lib/mapboxHelpers.ts
git commit -m "feat: add null-safe Mapbox expression helpers"
```

---

## Task 2: Fix Conditional Spread in mapLayers.ts

**Files:**
- Modify: `src/lib/mapLayers.ts:29-60`

- [ ] **Step 1: Write the test for zoneStrokeLayer**

```typescript
// src/lib/mapLayers.test.ts (create if not exists)

import { zoneStrokeLayer } from "./mapLayers";

describe("zoneStrokeLayer", () => {
  it("should return valid case expression when zone selected", () => {
    const layer = zoneStrokeLayer("whitefield", null);
    const lineColor = layer.paint["line-color"];

    // Should be a case expression with at least 3 elements
    expect(Array.isArray(lineColor)).toBe(true);
    expect(lineColor[0]).toBe("case");
    expect(lineColor.length).toBeGreaterThanOrEqual(3);
  });

  it("should return valid case expression when nothing selected", () => {
    const layer = zoneStrokeLayer(null, null);
    const lineColor = layer.paint["line-color"];

    // Should be a case expression with at least 3 elements
    expect(Array.isArray(lineColor)).toBe(true);
    expect(lineColor[0]).toBe("case");
    expect(lineColor.length).toBeGreaterThanOrEqual(3);
  });

  it("should not have conditional spread that could produce < 3 args", () => {
    const layer = zoneStrokeLayer(null, null);
    const lineColor = layer.paint["line-color"];

    // Verify the expression is well-formed
    expect(Array.isArray(lineColor)).toBe(true);
    expect(lineColor.length).toBeGreaterThanOrEqual(3);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/mapLayers.test.ts`
Expected: FAIL (conditional spread causes invalid expression when nothing selected)

- [ ] **Step 3: Fix zoneStrokeLayer to remove conditional spread**

```typescript
// src/lib/mapLayers.ts - Replace zoneStrokeLayer function

export const zoneStrokeLayer = (selected: string | null, hovered: string | null): LayerSpecification => {
  const sel = selected ?? "";
  const hov = hovered ?? "";

  // Build line-color expression without conditional spread
  // When nothing selected: simple case with 3 conditions
  // When zone selected: case with 4 conditions
  let lineColor: any;

  if (sel === "") {
    // Nothing selected - simple 3-condition case
    lineColor = [
      "case",
      ["==", ["get", "id"], hov],
      ["get", "rCol"],
      ["get", "rCol"],
    ];
  } else {
    // Zone selected - 4-condition case
    lineColor = [
      "case",
      ["==", ["get", "id"], sel],
      ["get", "rCol"],
      ["==", ["get", "id"], hov],
      ["get", "rCol"],
      ["!=", ["get", "id"], sel],
      "rgba(255,255,255,0.06)",
      ["get", "rCol"],
    ];
  }

  return {
    id: "zone-stroke",
    type: "line",
    source: "zones",
    paint: {
      "line-color": lineColor,
      "line-opacity": sel !== ""
        ? ["case", ["!=", ["get", "id"], sel], 0.15, 1.0]
        : 1.0,
      "line-width": [
        "case",
        ["==", ["get", "id"], sel],
        1.8,
        ["==", ["get", "id"], hov],
        1.4,
        1.0,
      ],
    },
  };
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/mapLayers.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/lib/mapLayers.ts src/lib/mapLayers.test.ts
git commit -m "fix: remove conditional spread from zoneStrokeLayer to prevent Mapbox expression errors"
```

---

## Task 3: Hide Mapbox Settlement Labels on Style Load

**Files:**
- Modify: `src/components/maps/ZoneHeatMap.tsx:116-188`

- [ ] **Step 1: Add label hiding logic after map load**

```typescript
// In ZoneHeatMap.tsx, inside map.on("load", ...) callback, after adding sources

// ─── Hide Mapbox Built-in Labels ───────────────────────────────────────
const HIDE_LABEL_TYPES = [
  'settlement-label',
  'settlement-subdivision-label',
  'neighborhood-label',
  'place-label',
  'poi-label',
  'state-label',
  'country-label',
];

const style = map.getStyle();
const layers = style.layers || [];

layers.forEach((layer: any) => {
  const isLabelLayer = HIDE_LABEL_TYPES.some((type) =>
    layer.id.includes(type) || layer.id.includes('label')
  );
  if (isLabelLayer) {
    map.setLayoutProperty(layer.id, 'visibility', 'none');
  }
});

console.log("Hidden Mapbox label layers:", layers.filter((l: any) =>
  HIDE_LABEL_TYPES.some((t) => l.id.includes(t))
).map((l: any) => l.id));
```

- [ ] **Step 2: Commit**

```bash
git add src/components/maps/ZoneHeatMap.tsx
git commit -m "feat: hide Mapbox settlement labels to prevent label clash"
```

---

## Task 4: Update ZoneHeatMap to Use Null-Safe Helpers

**Files:**
- Modify: `src/components/maps/ZoneHeatMap.tsx:1-10,224-264`

- [ ] **Step 1: Import null-safe helpers**

```typescript
// Add to imports at top of ZoneHeatMap.tsx
import {
  getFillOpacity,
  getLineWidth,
  getLineOpacity,
  getCyanFilter,
  getLabelColor,
  getLabelOpacity,
} from "@/lib/mapboxHelpers";
```

- [ ] **Step 2: Replace layer update logic with null-safe helpers**

```typescript
// Replace the useEffect that updates layers when selected/hovered changes (lines 224-264)

useEffect(() => {
  const map = mapRef.current;
  if (!map || !map.isStyleLoaded() || !map.getSource("zones")) return;

  // Update zone fill layer
  if (map.getLayer("zone-fill")) {
    map.setPaintProperty("zone-fill", "fill-opacity", getFillOpacity(selected));
  }

  // Update zone stroke layer
  if (map.getLayer("zone-stroke")) {
    map.setPaintProperty("zone-stroke", "line-color", (zoneStrokeLayer(selected, hovered) as any).paint["line-color"]);
    map.setPaintProperty("zone-stroke", "line-opacity", getLineOpacity(selected));
    map.setPaintProperty("zone-stroke", "line-width", getLineWidth(selected));
  }

  // Update zone halo layer
  if (map.getLayer("zone-halo")) {
    map.setFilter("zone-halo", getCyanFilter(selected));
  }

  // Update zone label layer
  if (map.getLayer("zone-labels")) {
    map.setPaintProperty("zone-labels", "text-color", getLabelColor(selected));
    map.setPaintProperty("zone-labels", "text-opacity", getLabelOpacity(selected));
  }

  // Update load badge layer
  if (map.getLayer("zone-load-badge")) {
    map.setFilter("zone-load-badge", getCyanFilter(selected));
  }

  // Update demand node layer
  if (map.getLayer("demand-nodes-bg")) {
    map.setFilter("demand-nodes-bg", selected ? ["==", ["get", "zoneId"], selected] : ["!=", ["get", "zoneId"], ""]);
  }
}, [selected, hovered]);
```

- [ ] **Step 3: Commit**

```bash
git add src/components/maps/ZoneHeatMap.tsx
git commit -m "refactor: use null-safe helpers for Mapbox paint updates"
```

---

## Task 5: Create osmnx Extraction Script

**Files:**
- Create: `scripts/get_zones.py`

- [ ] **Step 1: Write the Python extraction script**

```python
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
            print(f"  ✓ {name}: {vertices} vertices")
        except Exception as e:
            print(f"  ✗ {name}: {e}")

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

    print(f"\n✅ Saved: {output_path}")
    print(f"   Total zones: {len(geojson['features'])}")

if __name__ == "__main__":
    extract_zone_boundaries()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/get_zones.py
git commit -m "feat: add osmnx script for extracting real zone boundaries"
```

---

## Task 6: Create Mapshaper Simplification Script

**Files:**
- Create: `scripts/simplify_zones.sh`

- [ ] **Step 1: Write the simplification script**

```bash
#!/bin/bash
# Simplify zone boundaries using Mapshaper
# Reduces vertex count while preserving road-hugging shape

set -e

INPUT="public/urjayukti_zones_raw.geojson"
OUTPUT="public/urjayukti_zones.geojson"

if [ ! -f "$INPUT" ]; then
    echo "Error: $INPUT not found. Run get_zones.py first."
    exit 1
fi

echo "Simplifying zone boundaries..."
mapshaper "$INPUT" \
  -simplify 15% keep-shapes \
  -clean \
  -o "$OUTPUT" format=geojson

echo "✅ Simplified zones saved to: $OUTPUT"
echo "   Run 'node scripts/enrich_zones.js' to add EV data"
```

- [ ] **Step 2: Make script executable**

```bash
chmod +x scripts/simplify_zones.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/simplify_zones.sh
git commit -m "feat: add Mapshaper simplification script"
```

---

## Task 7: Create Zone Enrichment Script

**Files:**
- Create: `scripts/enrich_zones.js`

- [ ] **Step 1: Write the enrichment script**

```javascript
#!/usr/bin/env node
/**
 * Enrich zone GeoJSON with UrjaYukti EV data
 *
 * Usage:
 *     node scripts/enrich_zones.js
 *
 * Output:
 *     public/urjayukti_zones_enriched.geojson
 */

const fs = require('fs');
const path = require('path');

// UrjaYukti EV data for each zone
const ZONE_DATA = {
  "Whitefield": {
    id: "whitefield",
    zoneId: "Z7",
    risk: "CRITICAL",
    risk_color: "#F43F5E",
    load: 92,
    headroom: 8,
    evDensity: 94,
    growth: 28,
    score: 94,
    fillColor: "#F43F5E",
    lineColor: "#F43F5E",
  },
  "HSR Layout": {
    id: "hsr-layout",
    zoneId: "Z3",
    risk: "HIGH",
    risk_color: "#F59E0B",
    load: 78,
    headroom: 22,
    evDensity: 76,
    growth: 22,
    score: 81,
    fillColor: "#F59E0B",
    lineColor: "#F59E0B",
  },
  "Indiranagar": {
    id: "indiranagar",
    zoneId: "Z1",
    risk: "MODERATE",
    risk_color: "#0891B2",
    load: 71,
    headroom: 29,
    evDensity: 68,
    growth: 18,
    score: 75,
    fillColor: "#0891B2",
    lineColor: "#0891B2",
  },
  "Koramangala": {
    id: "koramangala",
    zoneId: "Z9",
    risk: "MODERATE",
    risk_color: "#0891B2",
    load: 65,
    headroom: 35,
    evDensity: 58,
    growth: 15,
    score: 68,
    fillColor: "#0891B2",
    lineColor: "#0891B2",
  },
  "Electronic City": {
    id: "electronic-city",
    zoneId: "Z11",
    risk: "LOW",
    risk_color: "#10B981",
    load: 58,
    headroom: 42,
    evDensity: 52,
    growth: 31,
    score: 71,
    fillColor: "#10B981",
    lineColor: "#10B981",
  },
  "Marathahalli": {
    id: "marathahalli",
    zoneId: "Z5",
    risk: "LOW",
    risk_color: "#10B981",
    load: 52,
    headroom: 48,
    evDensity: 44,
    growth: 19,
    score: 63,
    fillColor: "#10B981",
    lineColor: "#10B981",
  },
};

function enrichZones() {
  const inputPath = path.join(__dirname, '../public/urjayukti_zones.geojson');
  const outputPath = path.join(__dirname, '../public/urjayukti_zones_enriched.geojson');

  if (!fs.existsSync(inputPath)) {
    console.error(`Error: ${inputPath} not found. Run simplify_zones.sh first.`);
    process.exit(1);
  }

  console.log('Enriching zone GeoJSON with EV data...');

  const raw = JSON.parse(fs.readFileSync(inputPath, 'utf8'));

  // Enrich each feature with EV data
  raw.features = raw.features.map((feature) => {
    const zoneName = feature.properties.name || feature.properties.Name || "";
    const match = Object.keys(ZONE_DATA).find((key) =>
      zoneName.toLowerCase().includes(key.toLowerCase())
    );

    const data = match ? ZONE_DATA[match] : {};

    return {
      ...feature,
      properties: {
        ...feature.properties,
        ...data,
      },
    };
  });

  // Write enriched GeoJSON
  fs.writeFileSync(outputPath, JSON.stringify(raw, null, 2));

  console.log(`✅ Enriched zones saved to: ${outputPath}`);
  console.log(`   Total zones: ${raw.features.length}`);
}

enrichZones();
```

- [ ] **Step 2: Make script executable**

```bash
chmod +x scripts/enrich_zones.js
```

- [ ] **Step 3: Commit**

```bash
git add scripts/enrich_zones.js
git commit -m "feat: add zone enrichment script for EV data"
```

---

## Task 8: Update ZoneHeatMap to Use Enriched GeoJSON

**Files:**
- Modify: `src/components/maps/ZoneHeatMap.tsx:8,118-127`

- [ ] **Step 1: Update import to use enriched GeoJSON**

```typescript
// Replace line 8
import zonesGeoJSON from "../../data/bengaluru-zones.json";

// With:
import zonesGeoJSON from "../../../public/urjayukti_zones_enriched.geojson";
```

- [ ] **Step 2: Update source data path in map load**

```typescript
// In map.on("load", ...) callback, update zones source (around line 118)
map.addSource("zones", {
  type: "geojson",
  data: "/urjayukti_zones_enriched.geojson",
});
```

- [ ] **Step 3: Commit**

```bash
git add src/components/maps/ZoneHeatMap.tsx
git commit -m "feat: use enriched GeoJSON with real zone boundaries"
```

---

## Task 9: Verify Camera Swoop with Proper Padding

**Files:**
- Modify: `src/components/maps/ZoneHeatMap.tsx:268-323`

- [ ] **Step 1: Review and verify fitBounds padding**

```typescript
// Verify the fitBounds call has proper padding (around line 282-292)
map.fitBounds(
  [
    [minLng, minLat],
    [maxLng, maxLat],
  ],
  {
    padding: { top: 80, bottom: 80, left: 60, right: 320 },  // right: 320px for stats panel
    duration: 1000,
    easing: easeInOutCubic as any,
    maxZoom: 15,  // Add this to prevent over-zooming
  }
);
```

- [ ] **Step 2: Add maxZoom if not present**

```typescript
// Add maxZoom: 15 to fitBounds options
```

- [ ] **Step 3: Commit**

```bash
git add src/components/maps/ZoneHeatMap.tsx
git commit -m "fix: add maxZoom to fitBounds for better camera control"
```

---

## Task 10: Create Integration Test for Map Component

**Files:**
- Create: `src/components/maps/ZoneHeatMap.test.tsx`

- [ ] **Step 1: Write integration test**

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import ZoneHeatMap from "./ZoneHeatMap";

// Mock mapbox-gl
jest.mock("mapbox-gl", () => ({
  __esModule: true,
  default: {
    Map: jest.fn(() => ({
      on: jest.fn(),
      addSource: jest.fn(),
      addLayer: jest.fn(),
      addControl: jest.fn(),
      getCanvas: jest.fn(() => ({ style: {} })),
      isStyleLoaded: jest.fn(() => true),
      getSource: jest.fn(() => ({})),
      getLayer: jest.fn(() => ({})),
      setPaintProperty: jest.fn(),
      setLayoutProperty: jest.fn(),
      setFilter: jest.fn(),
      fitBounds: jest.fn(),
      flyTo: jest.fn(),
      once: jest.fn(),
      off: jest.fn(),
      remove: jest.fn(),
      project: jest.fn(() => ({ x: 100, y: 100 })),
    })),
    NavigationControl: jest.fn(),
  },
}));

// mock @turf/bbox
jest.mock("@turf/turf", () => ({
  bbox: jest.fn(() => [77.7, 12.9, 77.8, 13.0]),
}));

describe("ZoneHeatMap", () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
  });

  it("should render map container", () => {
    const { container } = render(
      <ZoneHeatMap selected={null} setSelected={jest.fn()} />
    );
    expect(container.querySelector(".w-full.h-full")).toBeInTheDocument();
  });

  it("should handle zone selection", async () => {
    const setSelected = jest.fn();
    render(<ZoneHeatMap selected={null} setSelected={setSelected} />);

    // Wait for map to initialize
    await waitFor(() => {
      expect(setSelected).not.toHaveBeenCalled();
    });
  });

  it("should handle null selection safely", () => {
    const setSelected = jest.fn();
    render(<ZoneHeatMap selected={null} setSelected={setSelected} />);

    // Should not crash with null selection
    expect(setSelected).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

Run: `npm test -- src/components/maps/ZoneHeatMap.test.tsx`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/components/maps/ZoneHeatMap.test.tsx
git commit -m "test: add integration tests for ZoneHeatMap component"
```

---

## Task 11: Run Data Pipeline

**Files:**
- Execute: `scripts/get_zones.py`, `scripts/simplify_zones.sh`, `scripts/enrich_zones.js`

- [ ] **Step 1: Install Python dependencies**

```bash
pip install osmnx geopandas shapely
```

- [ ] **Step 2: Install Mapshaper**

```bash
npm install -g mapshaper
```

- [ ] **Step 3: Run zone extraction**

```bash
python scripts/get_zones.py
```

Expected output:
```
Extracting Whitefield, Bengaluru...
  ✓ Whitefield, Bengaluru: 284 vertices
Extracting HSR Layout, Bengaluru...
  ✓ HSR Layout, Bengaluru: 312 vertices
...
✅ Saved: public/urjayukti_zones_raw.geojson
   Total zones: 6
```

- [ ] **Step 4: Run simplification**

```bash
bash scripts/simplify_zones.sh
```

Expected output:
```
Simplifying zone boundaries...
✅ Simplified zones saved to: public/urjayukti_zones.geojson
   Run 'node scripts/enrich_zones.js' to add EV data
```

- [ ] **Step 5: Run enrichment**

```bash
node scripts/enrich_zones.js
```

Expected output:
```
Enriching zone GeoJSON with EV data...
✅ Enriched zones saved to: public/urjayukti_zones_enriched.geojson
   Total zones: 6
```

- [ ] **Step 6: Verify enriched GeoJSON**

```bash
cat public/urjayukti_zones_enriched.geojson | jq '.features[0].properties'
```

Expected: Properties include id, zoneId, risk, risk_color, load, headroom, etc.

- [ ] **Step 7: Commit generated files**

```bash
git add public/urjayukti_zones_*.geojson
git commit -m "feat: add real Bengaluru zone boundaries with EV data"
```

---

## Task 12: Manual Testing and Verification

**Files:**
- Test: `src/components/maps/ZoneHeatMap.tsx`

- [ ] **Step 1: Start development server**

```bash
npm run dev
```

- [ ] **Step 2: Open browser and navigate to zone map**

Navigate to: `http://localhost:3000/dashboard` (or appropriate route)

- [ ] **Step 3: Verify Mapbox labels are hidden**

Checklist:
- [ ] No grey settlement labels visible
- [ ] Only custom zone labels visible
- [ ] Labels have correct colors (cyan when selected, risk color otherwise)

- [ ] **Step 4: Test zone selection**

Checklist:
- [ ] Click on a zone
- [ ] Camera swoops to frame the zone
- [ ] Zone highlights with proper opacity
- [ ] Other zones fade to dark background
- [ ] Cyan perimeter appears around selected zone
- [ ] No console errors related to Mapbox expressions

- [ ] **Step 5: Test null handling**

Checklist:
- [ ] Click outside zones to deselect
- [ ] Camera returns to full city view
- [ ] All zones return to default opacity
- [ ] No crashes or freezes
- [ ] No "null comparison" errors in console

- [ ] **Step 6: Test hover effects**

Checklist:
- [ ] Hover over zones
- [ ] Cursor changes to pointer
- [ ] Zone highlights on hover
- [ ] Tooltip appears with zone info

- [ ] **Step 7: Verify camera swoop**

Checklist:
- [ ] fitBounds calculates correct bounding box
- [ ] Zone is framed on left side of screen
- [ ] Right side has space for stats panel (320px)
- [ ] Animation is smooth (1s duration)
- [ ] maxZoom prevents over-zooming

- [ ] **Step 8: Document any issues found**

Create: `docs/mapbox-testing-notes.md` with any issues found during testing

---

## Task 13: Update Documentation

**Files:**
- Create: `docs/mapbox-implementation.md`

- [ ] **Step 1: Write implementation documentation**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add docs/mapbox-implementation.md
git commit -m "docs: add Mapbox implementation documentation"
```

---

## Task 14: Final Verification and Cleanup

**Files:**
- Verify: All files, tests, documentation

- [ ] **Step 1: Run all tests**

```bash
npm test
```

Expected: All tests pass

- [ ] **Step 2: Build production bundle**

```bash
npm run build
```

Expected: Build succeeds without errors

- [ ] **Step 3: Check for console errors**

Open production build in browser and check console for:
- [ ] No Mapbox expression errors
- [ ] No null comparison errors
- [ ] No label overlap issues

- [ ] **Step 4: Verify all files are committed**

```bash
git status
```

Expected: No uncommitted changes (except maybe docs/testing-notes.md)

- [ ] **Step 5: Create summary of changes**

Create: `docs/mapbox-changes-summary.md`

```markdown
# Mapbox Implementation Changes Summary

## Files Created

- `src/lib/mapboxHelpers.ts` - Null-safe expression helpers
- `scripts/get_zones.py` - osmnx extraction script
- `scripts/simplify_zones.sh` - Mapshaper simplification script
- `scripts/enrich_zones.js` - Zone enrichment script
- `public/urjayukti_zones_enriched.geojson` - Final zone data
- `src/components/maps/ZoneHeatMap.test.tsx` - Integration tests
- `docs/mapbox-implementation.md` - Implementation docs

## Files Modified

- `src/components/maps/ZoneHeatMap.tsx` - Added label hiding, null-safe helpers
- `src/lib/mapLayers.ts` - Fixed conditional spread in zoneStrokeLayer

## Roadblocks Fixed

1. **Roadblock A**: Real shapefile data via osmnx + Mapshaper
2. **Roadblock B**: null intercept via mapboxHelpers.ts
3. **Roadblock C**: case syntax fix in zoneStrokeLayer
4. **Roadblock D**: Mapbox label hiding on style.load

## Testing

- All unit tests pass
- Integration tests pass
- Manual testing verified:
  - Labels hidden correctly
  - No Mapbox expression errors
  - Camera swoop works properly
  - Null handling safe
```

- [ ] **Step 6: Final commit**

```bash
git add docs/mapbox-changes-summary.md
git commit -m "docs: add Mapbox implementation changes summary"
```

---

## Verification Checklist

Before considering this implementation complete:

- [ ] All 14 tasks completed
- [ ] All tests pass
- [ ] Production build succeeds
- [ ] Manual testing verified:
  - [ ] Mapbox labels hidden
  - [ ] No expression errors in console
  - [ ] Zone selection works correctly
  - [ ] Camera swoop frames zone properly
  - [ ] Null handling safe (no crashes)
  - [ ] Hover effects work
- [ ] Documentation complete
- [ ] Data pipeline tested and verified
- [ ] Real zone boundaries loaded (not mock data)
