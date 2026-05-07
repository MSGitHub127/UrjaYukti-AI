"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import mapboxgl from "mapbox-gl";
import { bbox } from "@turf/turf";
import "mapbox-gl/dist/mapbox-gl.css";

import nodesGeoJSON from "../../data/demand-nodes.json";
import { HEATMAP_ZONES, easeInOutCubic, nodeColor, nodeR } from "@/lib/mockData";
import {
  zoneFillLayer,
  zoneStrokeLayer,
  zoneHaloLayer,
  zoneLabelLayer,
  loadBadgeLayer,
  demandNodeLayer,
  flowLayer,
  COLORS,
} from "@/lib/mapLayers";

// ─── Constants ───────────────────────────────────────────────────────────────

const BENGALURU_CENTER = [77.5946, 12.9716] as [number, number];
const INITIAL_ZOOM = 11.2;

// ─── Demand Node Marker Component ────────────────────────────────────────────

interface DemandNodeMarkerProps {
  load: number;
  type: "peak" | "high" | "opt";
  ms: number;
  zoomed: boolean;
}

function DemandNodeMarker({ load, type, ms, zoomed }: DemandNodeMarkerProps) {
  const col = nodeColor(type);
  const r = nodeR(load) * (zoomed ? 1 : 0.7);
  const rOut = r * 2.6;

  return (
    <div className="demand-node-wrapper" style={{ animationDelay: `${ms}ms` }}>
      {/* Ripple ring */}
      <div
        className="ripple"
        style={{
          width: `${rOut * 2}px`,
          height: `${rOut * 2}px`,
          background: "none",
          border: `${0.7}px solid ${col}`,
          opacity: 0.45,
        }}
      />
      {/* Dot beat */}
      <div
        className="dot-beat"
        style={{
          width: `${r * 2}px`,
          height: `${r * 2}px`,
          background: col,
          borderRadius: "50%",
        }}
      />
      {/* Load label for high load nodes when zoomed */}
      {zoomed && load >= 75 && (
        <span
          className="absolute -top-4 left-1/2 -translate-x-1/2 font-mono font-bold text-[7px]"
          style={{ color: col }}
        >
          {load}%
        </span>
      )}
    </div>
  );
}

// ─── Main Zone Heat Map Component ────────────────────────────────────────────

interface ZoneHeatMapProps {
  selected: string | null;
  setSelected: (id: string | null) => void;
}

export default function ZoneHeatMap({ selected, setSelected }: ZoneHeatMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);

  const [hovered, setHovered] = useState<string | null>(null);
  const [perimKey, setPerimKey] = useState(0);
  const [perimPts, setPerimPts] = useState<string | null>(null);
  const [zonesGeoJSON, setZonesGeoJSON] = useState<any>(null);

  // ─── Load Zone GeoJSON Data ───────────────────────────────────────────────────

  useEffect(() => {
    fetch("/urjayukti_zones_enriched.geojson")
      .then((res) => res.json())
      .then((data) => setZonesGeoJSON(data))
      .catch((err) => console.error("Failed to load zones GeoJSON:", err));
  }, []);

  // ─── Initialize Map ───────────────────────────────────────────────────────

  useEffect(() => {
    if (!mapContainerRef.current || !zonesGeoJSON) return;

    // Initialize the map
    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      accessToken: process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "",
      style: "mapbox://styles/mapbox/navigation-night-v1",
      center: BENGALURU_CENTER,
      zoom: INITIAL_ZOOM,
      pitch: 0,
      bearing: 0,
    });

    mapRef.current = map;

    // Add navigation control
    map.addControl(new mapboxgl.NavigationControl({ showCompass: true, showZoom: false }), "top-left");

    // ─── Add Sources and Layers on Load ───────────────────────────────────────

    map.on("load", () => {
      // Add zones source
      map.addSource("zones", {
        type: "geojson",
        data: "/urjayukti_zones_enriched.geojson",
      });

      // Add nodes source
      map.addSource("nodes", {
        type: "geojson",
        data: nodesGeoJSON as any,
      });

      // Build flow lines GeoJSON
      const flowLinesGeoJSON = {
        type: "FeatureCollection" as const,
        features: zonesGeoJSON ? HEATMAP_ZONES.slice(0, -1).map((z, i) => {
          const next = HEATMAP_ZONES[i + 1];
          if (!next) return null;

          const currentFeature = zonesGeoJSON.features.find((f: any) => f.id === z.id);
          const nextFeature = zonesGeoJSON.features.find((f: any) => f.id === next.id);

          if (!currentFeature || !nextFeature) return null;

          const currentCoords = currentFeature.geometry.coordinates[0][0];
          const nextCoords = nextFeature.geometry.coordinates[0][0];

          return {
            type: "Feature" as const,
            geometry: {
              type: "LineString" as const,
              coordinates: [currentCoords, nextCoords],
            },
            properties: { load: z.load },
          };
        }).filter(Boolean) : [],
      };

      // Add flows source
      map.addSource("flows", {
        type: "geojson",
        data: flowLinesGeoJSON as any,
      });

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

      // Add layers
      // ✅ Resolve null → "" BEFORE building expressions
      const sel = selected ?? "";
      const hov = hovered ?? "";

      map.addLayer(zoneHaloLayer(sel) as any);
      map.addLayer(zoneFillLayer(sel, hov) as any);
      map.addLayer(zoneStrokeLayer(sel, hov) as any);
      map.addLayer(zoneLabelLayer(sel) as any);
      map.addLayer(loadBadgeLayer(sel) as any);
      map.addLayer(demandNodeLayer(sel) as any);
      map.addLayer(flowLayer as any);

      // ─── Animate Flow Dasharray ─────────────────────────────────────────────

      let offset = 0;
      const animateFlow = () => {
        offset = (offset - 0.5 + 14) % 14;
        if (map.isStyleLoaded() && map.getLayer("zone-flows")) {
          map.setPaintProperty("zone-flows", "line-dasharray", [
            Math.max(0, 8 - offset),
            6 + offset,
          ]);
        }
        requestAnimationFrame(animateFlow);
      };
      requestAnimationFrame(animateFlow);
    });

    // ─── Click Handler ───────────────────────────────────────────────────────

    map.on("click", "zone-fill", (e) => {
      const feature = e.features?.[0];
      if (feature && feature.properties) {
        setSelected(feature.properties.id);
      }
    });

    // ─── Hover Handlers ───────────────────────────────────────────────────────

    map.on("mousemove", "zone-fill", (e) => {
      const feature = e.features?.[0];
      if (feature && feature.properties) {
        setHovered(feature.properties.id);
        map.getCanvas().style.cursor = "pointer";
      }
    });

    map.on("mouseleave", "zone-fill", () => {
      setHovered(null);
      map.getCanvas().style.cursor = "";
    });

    // ─── Cleanup ─────────────────────────────────────────────────────────────

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [zonesGeoJSON]); // Re-initialize when zonesGeoJSON is loaded

  // ─── Update Layers When Selected/Hovered Changes ───────────────────────────

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded() || !map.getSource("zones")) return;

    // ✅ Resolve null → "" BEFORE building expressions
    const sel = selected ?? "";
    const hov = hovered ?? "";

    // Update zone fill layer
    if (map.getLayer("zone-fill")) {
      map.setPaintProperty("zone-fill", "fill-opacity", (zoneFillLayer(sel, hov) as any).paint["fill-opacity"]);
    }

    // Update zone stroke layer
    if (map.getLayer("zone-stroke")) {
      map.setPaintProperty("zone-stroke", "line-color", (zoneStrokeLayer(sel, hov) as any).paint["line-color"]);
      map.setPaintProperty("zone-stroke", "line-opacity", (zoneStrokeLayer(sel, hov) as any).paint["line-opacity"]);
      map.setPaintProperty("zone-stroke", "line-width", (zoneStrokeLayer(sel, hov) as any).paint["line-width"]);
    }

    // Update zone halo layer
    if (map.getLayer("zone-halo")) {
      map.setFilter("zone-halo", (zoneHaloLayer(sel) as any).filter);
    }

    // Update zone label layer
    if (map.getLayer("zone-labels")) {
      map.setLayoutProperty("zone-labels", "text-size", (zoneLabelLayer(sel) as any).layout["text-size"]);
      map.setPaintProperty("zone-labels", "text-color", (zoneLabelLayer(sel) as any).paint["text-color"]);
    }

    // Update load badge layer
    if (map.getLayer("zone-load-badge")) {
      map.setFilter("zone-load-badge", (loadBadgeLayer(sel) as any).filter);
    }

    // Update demand node layer
    if (map.getLayer("demand-nodes-bg")) {
      map.setFilter("demand-nodes-bg", (demandNodeLayer(sel) as any).filter);
    }
  }, [selected, hovered]);

  // ─── Handle Zone Selection (Camera Swoop) ─────────────────────────────────

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (selected) {
      const feature = zonesGeoJSON.features.find((f: any) => f.id === selected);
      if (!feature) return;

      setPerimKey((k) => k + 1);

      // Calculate bounding box with @turf/bbox
      const [minLng, minLat, maxLng, maxLat] = bbox(feature as any);

      // Fit bounds with padding
      map.fitBounds(
        [
          [minLng, minLat],
          [maxLng, maxLat],
        ],
        {
          padding: { top: 80, bottom: 80, left: 60, right: 320 },
          duration: 1000,
          easing: easeInOutCubic as any,
        }
      );

      // After pan ends, project polygon to screen space for SVG perimeter overlay
      const handleMoveEnd = () => {
        const coords =
          feature.geometry.type === "Polygon"
            ? feature.geometry.coordinates[0]
            : feature.geometry.coordinates[0][0];

        const pts = (coords as [number, number][])
          .map(([lng, lat]: [number, number]) => {
            const { x, y } = map.project([lng, lat]);
            return `${x},${y}`;
          })
          .join(" ");

        setPerimPts(pts);
        map.off("moveend", handleMoveEnd);
      };

      map.once("moveend", handleMoveEnd);
    } else {
      // Reset to full city view
      map.flyTo({
        center: BENGALURU_CENTER,
        zoom: INITIAL_ZOOM,
        duration: 1000,
        easing: easeInOutCubic as any,
      });
      setPerimPts(null);
    }
  }, [selected]);

  // ─── Reproject Perimeter on Map Move ───────────────────────────────────────

  const reprojectPerim = useCallback((): void => {
    if (!selected || !mapRef.current) return;

    const map = mapRef.current;
    const feature = zonesGeoJSON.features.find((f: any) => f.id === selected);
    if (!feature) return;

    const coords =
      feature.geometry.type === "Polygon"
        ? feature.geometry.coordinates[0]
        : feature.geometry.coordinates[0][0];

    const pts = (coords as [number, number][])
      .map(([lng, lat]: [number, number]) => {
        const { x, y } = map.project([lng, lat]);
        return `${x},${y}`;
      })
      .join(" ");

    setPerimPts(pts);
  }, [selected]);

  // Re-run on every map render frame while a zone is selected
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selected) return;

    map.on("render", reprojectPerim);
    return () => {
      map.off("render", reprojectPerim);
    };
  }, [selected, reprojectPerim]);

  // ─── Update HTML Markers for Demand Nodes ───────────────────────────────────

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    // Only show markers when a zone is selected
    if (selected) {
      const selZone = HEATMAP_ZONES.find((z) => z.id === selected);
      if (!selZone) return;

      nodesGeoJSON.features
        .filter((f: any) => f.properties.zoneId === selected)
        .forEach((f: any) => {
          // Create a DOM element for the marker
          const el = document.createElement("div");
          el.style.width = "0";
          el.style.height = "0";

          // Render the DemandNodeMarker into the element
          const marker = new mapboxgl.Marker({
            element: el,
            anchor: "center",
          })
            .setLngLat([f.geometry.coordinates[0], f.geometry.coordinates[1]])
            .addTo(map);

          // Use React to render the marker content
          import("react-dom/client").then(({ createRoot }) => {
            const root = createRoot(el);
            root.render(
              <DemandNodeMarker
                load={f.properties.load}
                type={f.properties.type}
                ms={f.properties.ms}
                zoomed
              />
            );
          });

          markersRef.current.push(marker);
        });
    }
  }, [selected]);

  // ─── Get Zone Data ─────────────────────────────────────────────────────────

  const selZone = selected ? HEATMAP_ZONES.find((z) => z.id === selected) : null;
  const hovZone = hovered ? HEATMAP_ZONES.find((z) => z.id === hovered) : null;

  return (
    <div className="flex-1 relative overflow-hidden">
      {/* ── Mapbox Canvas Container ──────────────────────────────────────────── */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* ── Animated Perimeter SVG Overlay ──────────────────────────────────── */}
      {perimPts && selected && (
        <svg
          className="absolute inset-0 pointer-events-none w-full h-full"
          style={{ zIndex: 10 }}
        >
          <polygon
            key={`perim-${selected}-${perimKey}`}
            points={perimPts}
            fill="none"
            stroke={COLORS.cyan}
            strokeWidth={2.2}
            strokeLinejoin="round"
            className="draw-perim"
          />
        </svg>
      )}

      {/* ── Hover Tooltip ─────────────────────────────────────────────────────── */}
      {hovZone && !selected && (
        <div
          className="absolute top-20 left-6 bg-card2 border rounded-xl p-3 pointer-events-none"
          style={{
            borderColor: `${hovZone.rCol}55`,
            boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
          }}
        >
          <div
            className="font-mono font-bold text-[9px] mb-1"
            style={{ color: hovZone.rCol }}
          >
            {hovZone.zoneId} · {hovZone.risk}
          </div>
          <div className="text-text text-sm font-bold mb-1.5">{hovZone.name}</div>
          <div className="flex gap-3">
            <div>
              <div className="text-sub text-[10px]">Load</div>
              <div
                className="font-mono font-bold text-lg"
                style={{ color: hovZone.rCol }}
              >
                {hovZone.load}%
              </div>
            </div>
            <div>
              <div className="text-sub text-[10px]">Headroom</div>
              <div className="font-mono font-bold text-lg text-teal">
                {hovZone.headroom}%
              </div>
            </div>
          </div>
          <div className="mt-2 text-sub text-[10px] italic">
            Click to zoom in →
          </div>
        </div>
      )}
    </div>
  );
}
