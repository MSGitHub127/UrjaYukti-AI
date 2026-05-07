"use client";

import { type HeatmapZone, nodeColor } from "@/lib/mockData";

interface StatsPanelProps {
  zone: HeatmapZone;
  onClose: () => void;
}

export default function StatsPanel({ zone, onClose }: StatsPanelProps) {
  const peakNodes = zone.nodes.filter((n) => n.type === "peak").length;
  const highNodes = zone.nodes.filter((n) => n.type === "high").length;
  const optNodes = zone.nodes.filter((n) => n.type === "opt").length;

  return (
    <div
      className="slide-inR w-[268px] flex-shrink-0 flex flex-col overflow-hidden rounded-xl"
      style={{
        background: "#141B2D",
        border: "1px solid rgba(255,255,255,0.07)",
        boxShadow:
          "0 0 40px rgba(0,229,255,0.08), 0 8px 32px rgba(0,0,0,0.5)",
      }}
    >
      {/* Header */}
      <div
        className="px-4 py-3.5 border-b border-border"
        style={{
          background: `linear-gradient(135deg, ${zone.rCol}18, transparent)`,
        }}
      >
        <div className="flex justify-between items-start">
          <div>
            <div
              className="font-mono font-bold text-[9px] mb-1"
              style={{
                color: zone.rCol,
                letterSpacing: "0.12em",
              }}
            >
              {zone.zoneId} · {zone.risk}
            </div>
            <div className="font-display font-extrabold text-lg text-text">
              {zone.name}
            </div>
          </div>
          <button
            onClick={onClose}
            className="bg-white/6 border border-border text-sub w-6.5 h-6.5 rounded-lg text-xs flex items-center justify-center hover:bg-white/10"
          >
            ✕
          </button>
        </div>
        <div className="mt-2.5 flex gap-1.5 flex-wrap">
          <span
            className="tag"
            style={{
              background: `${zone.rCol}22`,
              color: zone.rCol,
              border: `1px solid ${zone.rCol}44`,
            }}
          >
            {zone.risk}
          </span>
          <span
            className="tag"
            style={{
              background: "rgba(0,229,255,0.12)",
              color: "#00E5FF",
              border: "1px solid rgba(0,229,255,0.3)",
            }}
          >
            MCDA {zone.score}/100
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 overflow-y-auto flex-1">
        {/* Current Load */}
        <div className="mb-4">
          <div className="flex justify-between mb-1.5">
            <span className="text-sub text-[10px]">Current Load</span>
            <span
              className="font-mono font-bold text-sm"
              style={{ color: zone.rCol }}
            >
              {zone.load}%
            </span>
          </div>
          <div
            className="rounded-full h-1.5 overflow-hidden"
            style={{ background: "#1A2340" }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${zone.load}%`,
                background: `linear-gradient(90deg, ${zone.rCol}, ${zone.rCol}88)`,
                boxShadow: `0 0 8px ${zone.rCol}66`,
              }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-dim text-[9px] font-mono">0%</span>
            <span
              className={`text-[9px] font-mono ${
                zone.headroom < 15 ? "text-danger" : "text-teal"
              }`}
            >
              Headroom {zone.headroom}%
            </span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-2 mb-3.5">
          {[
            { l: "EV Density", v: `${zone.evDensity}/100`, c: "#A78BFA" },
            { l: "Growth", v: zone.growth, c: "#10B981" },
            { l: "Score", v: `${zone.score}/100`, c: "#02C39A" },
            {
              l: "Headroom",
              v: `${zone.headroom}%`,
              c: zone.headroom < 15 ? "#F43F5E" : "#0891B2",
            },
          ].map((k) => (
            <div
              key={k.l}
              className="rounded-lg p-2 border border-border"
              style={{ background: "#1A2340" }}
            >
              <div className="text-sub text-[9px] mb-0.5">{k.l}</div>
              <div
                className="font-mono font-bold text-sm"
                style={{ color: k.c }}
              >
                {k.v}
              </div>
            </div>
          ))}
        </div>

        {/* Demand Nodes */}
        <div
          className="mb-3.5 p-2.5 rounded-xl border border-border"
          style={{ background: "#1A2340" }}
        >
          <div
            className="text-sub text-[9px] font-mono font-bold mb-2"
            style={{ letterSpacing: "0.1em" }}
          >
            DEMAND NODES
          </div>
          <div className="flex gap-2.5">
            {[
              { col: "#F43F5E", label: "Peak", count: peakNodes },
              { col: "#F59E0B", label: "High", count: highNodes },
              { col: "#02C39A", label: "Optimal", count: optNodes },
            ].map((n) => (
              <div key={n.label} className="flex items-center gap-1">
                <div
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: n.col, boxShadow: `0 0 6px ${n.col}` }}
                />
                <span className="text-text text-[11px] font-semibold">
                  {n.count}
                </span>
                <span className="text-sub text-[10px]">{n.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* VPP Recommendation */}
        <div
          className="p-3 rounded-xl"
          style={{
            background: "rgba(2,195,154,0.06)",
            border: "1px solid rgba(2,195,154,0.2)",
          }}
        >
          <div className="flex items-center gap-1.5 mb-1.5">
            <div className="live-blink w-1.5 h-1.5 rounded-full bg-primary" />
            <span className="text-primary text-[9px] font-mono font-bold">
              MISTRAL 7B · VPP RECOMMENDATION
            </span>
          </div>
          <div className="text-text text-[11px] leading-relaxed italic">
            "{zone.rec}"
          </div>
          <div className="mt-2 flex gap-1.5 flex-wrap">
            {["0 Violations", "Confidence 84%"].map((t) => (
              <span
                key={t}
                className="tag"
                style={{
                  background: "rgba(2,195,154,0.12)",
                  color: "#02C39A",
                  border: "1px solid rgba(2,195,154,0.25)",
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
