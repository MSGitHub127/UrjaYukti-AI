"use client";

import { useState } from "react";
import { AreaChart, Area, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { GlassCard, SectionLabel, KPICard } from "@/components/ui/card";
import ChartTooltip from "@/components/ui/chart";
import { COLORS } from "@/lib/mapLayers";
import { forecastData, ZONES } from "@/lib/mockData";
import { Tag } from "@/components/ui/Tag";

export default function ForecastView() {
  const [selectedZone, setSelectedZone] = useState("Z7");
  const zone = ZONES.find((z) => z.id === selectedZone);
  if (!zone) return null;
  const col = zone.risk === "CRITICAL" ? COLORS.danger : zone.risk === "HIGH" ? COLORS.warn : COLORS.teal;

  return (
    <div className="flex flex-col gap-5">
      {/* Zone Selector */}
      <div className="flex gap-2 flex-wrap">
        {ZONES.map((z) => {
          const c = z.risk === "CRITICAL" ? COLORS.danger : z.risk === "HIGH" ? COLORS.warn : COLORS.teal;
          return (
            <button
              key={z.id}
              onClick={() => setSelectedZone(z.id)}
              className="px-4 py-2 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: selectedZone === z.id ? `${c}18` : "transparent",
                border: selectedZone === z.id ? `1px solid ${c}66` : `1px solid ${COLORS.border}`,
                color: selectedZone === z.id ? c : COLORS.sub,
              }}
            >
              {z.name}
            </button>
          );
        })}
      </div>

      {/* Zone Info Card */}
      <GlassCard glow glowColor={col} style={{ padding: "20px 24px" }}>
        <div className="grid grid-cols-1fr 1fr 1fr 1fr gap-5 items-center">
          <div>
            <div className="text-sub text-[9px] font-mono mb-1">ZONE</div>
            <div className="text-text text-lg font-extrabold font-display">{zone.name}</div>
            <Tag text={zone.risk} color={col} dot />
          </div>
          {[
            { label: "Current Load", value: `${zone.load}%`, color: col },
            { label: "Grid Headroom", value: `${zone.headroom}%`, color: zone.headroom < 20 ? COLORS.danger : COLORS.teal },
            { label: "EV Density Score", value: `${zone.evDensity}/100`, color: COLORS.purple },
            { label: "Growth Trajectory", value: zone.growth, color: COLORS.success },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-sub text-[9px] mb-1">{s.label}</div>
              <div className="font-mono text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Forecast Chart */}
      <GlassCard style={{ padding: "22px" }}>
        <SectionLabel>72-Hour Demand Forecast — TFT Model with 80% / 95% Confidence Bands</SectionLabel>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={forecastData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
            <defs>
              <linearGradient id="fEV" x1="0%" y1="0" x2="0%" y2="1">
                <stop offset="5%" stopColor={COLORS.danger} stopOpacity={0.3} />
                <stop offset="95%" stopColor={COLORS.danger} stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="fOpt" x1="0%" y1="0" x2="0%" y2="1">
                <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.35} />
                <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="fCI95" x1="0%" y1="0" x2="0%" y2="1">
                <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.08} />
                <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
            <XAxis dataKey="h" tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine y={300} stroke={COLORS.danger} strokeDasharray="4 4" strokeWidth={1} />
            <Area type="monotone" dataKey="ci95hi" stroke="none" fill="url(#fCI95)" name="95% CI Upper" />
            <Area type="monotone" dataKey="ci80hi" stroke={COLORS.primary + "44"} strokeWidth={0.5} fill="none" name="80% CI" />
            <Area type="monotone" dataKey="ev" stroke={COLORS.danger} fill="url(#fEV)" strokeWidth={2} name="Unmanaged EV" />
            <Area type="monotone" dataKey="opt" stroke={COLORS.primary} fill="url(#fOpt)" strokeWidth={2.5} name="Optimized" />
            <Line type="monotone" dataKey="base" stroke={COLORS.sub} strokeDasharray="5 5" strokeWidth={1.5} dot={false} name="Baseline" />
          </AreaChart>
        </ResponsiveContainer>
      </GlassCard>

      {/* Metrics Cards */}
      <div className="grid grid-cols-4 gap-3.5">
        {[
          { label: "Model MAPE", value: "9.4%", sub: "vs 22.1% ARIMA baseline", color: COLORS.primary },
          { label: "Forecast Horizon", value: "72 hr", sub: "3-day ahead prediction", color: COLORS.teal },
          { label: "Peak at 20:00", value: "385 MW", sub: "unmanaged scenario", color: COLORS.danger },
          { label: "Optimized Peak", value: "315 MW", sub: "18% reduction achieved", color: COLORS.primary },
        ].map((m) => (
          <GlassCard key={m.label} className="card-hover" style={{ padding: "16px 18px", borderTop: `2px solid ${m.color}` }}>
            <div className="text-sub text-[9px] mb-1">{m.label}</div>
            <div className="font-mono text-2xl font-bold" style={{ color: m.color, marginBottom: 4 }}>{m.value}</div>
            <div className="text-sub text-[10px]">{m.sub}</div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}
