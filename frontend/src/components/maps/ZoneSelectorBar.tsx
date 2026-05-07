"use client";

import { HEATMAP_ZONES, type HeatmapZone } from "@/lib/mockData";

interface ZoneSelectorBarProps {
  zones: HeatmapZone[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export default function ZoneSelectorBar({
  zones,
  selected,
  onSelect,
}: ZoneSelectorBarProps) {
  return (
    <div className="bg-panel/90 border-b border-border flex items-center gap-2 flex-wrap flex-shrink-0 p-2.5">
      {/* Live Indicator */}
      <div className="flex items-center gap-1.5 mr-2">
        <div className="live-blink w-1.5 h-1.5 rounded-full bg-primary" />
        <span className="text-primary text-[9px] font-mono font-bold">
          LIVE · {zones.length} ZONES
        </span>
      </div>

      {/* All Zones Reset Button */}
      <button
        onClick={() => onSelect("")}
        className={`px-3 py-1 rounded-lg text-[11px] font-semibold transition-all ${
          !selected
            ? "bg-primary/12 border-primary/40 text-primary"
            : "bg-white/4 border-border text-sub hover:bg-white/6"
        }`}
      >
        All Zones
      </button>

      {/* Zone Buttons */}
      {zones.map((zone) => (
        <button
          key={zone.id}
          onClick={() => onSelect(zone.id)}
          className={`px-3 py-1 rounded-lg text-[11px] font-semibold transition-all flex items-center gap-1.5 ${
            selected === zone.id
              ? `bg-[${zone.rCol}]/22 border-[${zone.rCol}]/66 text-[${zone.rCol}]`
              : "bg-white/4 border-border text-sub hover:bg-white/6"
          }`}
          style={
            selected === zone.id
              ? {
                  backgroundColor: `${zone.rCol}22`,
                  borderColor: `${zone.rCol}66`,
                  color: zone.rCol,
                }
              : {}
          }
        >
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: zone.rCol,
              boxShadow: selected === zone.id ? `0 0 6px ${zone.rCol}` : "none",
            }}
          />
          {zone.name}
          <span className="font-mono font-bold text-[9px]">{zone.load}%</span>
        </button>
      ))}

      {/* Full City View Button (shown when zone is selected) */}
      {selected && (
        <button
          onClick={() => onSelect(selected)}
          className="ml-auto px-3 py-1 rounded-lg text-[11px] bg-white/5 border-border text-sub hover:bg-white/6"
        >
          ← Full City View
        </button>
      )}
    </div>
  );
}
