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
