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
