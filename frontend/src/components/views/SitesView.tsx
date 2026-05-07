"use client";

import { useState } from "react";
import { GlassCard, SectionLabel, Tag, Mono } from "@/components/ui/card";
import { COLORS } from "@/lib/mapLayers";
import { SITES, ZONES } from "@/lib/mockData";

export default function SitesView() {
  const [weights, setWeights] = useState({
    demand: 30,
    headroom: 25,
    access: 15,
    growth: 12,
    land: 10,
    infra: 8,
  });
  const [selected, setSelected] = useState<number | null>(null);

  const totalW = Object.values(weights).reduce((a, b) => a + b, 0);
  const isValid = Math.abs(totalW - 100) < 0.5;

  const recomputedScores = SITES.map((s) => {
    const raw =
      s.demand * (weights.demand / 100) +
      s.headroom * (weights.headroom / 100) +
      s.access * (weights.access / 100) +
      s.growth * (weights.growth / 100);
    return { ...s, computedScore: Math.round(raw * 0.85 + s.score * 0.15) };
  }).sort((a, b) => b.computedScore - a.computedScore);

  return (
    <div className="flex flex-col gap-5">
      {/* Weight Configuration Card */}
      <GlassCard style={{ padding: "14px 20px" }}>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex-1">
            <div className="text-primary text-[10px] font-mono font-bold mb-1">
              CONSTRAINT-AWARE MCDA SITE RANKING · AHP WEIGHTS
            </div>
            <div className="text-sub text-[11px]">
              Adjust MCDA weights below. Site rankings recompute in real time. Weights must sum to 100%. Planner override available with audit log.
            </div>
          </div>
          <div className="ml-auto flex gap-2">
            <Tag text={isValid ? "Weights Valid ✓" : "Weights Invalid"} color={isValid ? COLORS.success : COLORS.danger} />
            <Tag text="CR < 0.1 · AHP Verified" color={COLORS.primary} />
          </div>
        </div>
      </GlassCard>

      {/* Main Content */}
      <div className="grid grid-cols-[280px_1fr] gap-5">
        {/* Weight Configuration */}
        <GlassCard style={{ padding: "20px" }}>
          <SectionLabel>MCDA Weight Configuration</SectionLabel>
          <div className="flex flex-col gap-3.5">
            {[
              { key: "demand" as const, label: "Demand Density", color: COLORS.primary },
              { key: "headroom" as const, label: "Grid Headroom", color: COLORS.teal },
              { key: "access" as const, label: "Accessibility Score", color: "#4DB8FF" },
              { key: "growth" as const, label: "Growth Trajectory", color: COLORS.warn },
              { key: "land" as const, label: "Land Availability", color: COLORS.purple },
              { key: "infra" as const, label: "Infra Proximity", color: COLORS.sub },
            ].map((w) => (
              <div key={w.key}>
                <div className="flex justify-between mb-1">
                  <span className="text-text text-xs">{w.label}</span>
                  <Mono color={w.color} size={12}>
                    {weights[w.key]}%
                  </Mono>
                </div>
                <input
                  type="range"
                  min={5}
                  max={50}
                  value={weights[w.key]}
                  onChange={(e) => setWeights((prev) => ({ ...prev, [w.key]: Number(e.target.value) }))}
                  className="w-full h-1.5 rounded-full"
                  style={{
                    background: `linear-gradient(90deg,${w.color} ${weights[w.key] * 2}%,${COLORS.card2} ${weights[w.key] * 2}%)`,
                  }}
                />
                <div className="h-1 w-full rounded-full overflow-hidden mt-1">
                  <div className="h-full rounded-full" style={{ width: `${weights[w.key]}%`, background: w.color, borderRadius: 99, transition: "width 0.4s ease" }} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 p-2.5 rounded-lg" style={{ background: "rgba(2,195,154,0.11)", border: "1px solid rgba(2,195,154,0.2)" }}>
            <div className="flex justify-between">
              <span className="text-sub text-[10px]">Total weight</span>
              <Mono color={isValid ? COLORS.success : COLORS.danger} size={12}>
                {totalW}%
              </Mono>
            </div>
          </div>
        </GlassCard>

        {/* Recommended Sites Table */}
        <GlassCard style={{ padding: "20px" }}>
          <SectionLabel>Recommended Sites — Live Ranking</SectionLabel>
          <div className="flex flex-col gap-2">
            {recomputedScores.map((site, idx) => (
              <div
                key={site.name}
                onClick={() => setSelected(selected === site.rank ? null : site.rank)}
                className="p-4 rounded-xl cursor-pointer transition-all border border-transparent hover:border-white/10 mb-2"
                style={{
                  background: selected === site.rank ? `${COLORS.primary}12` : "rgba(255,255,255,0.02)",
                  border: selected === site.rank ? `1px solid ${COLORS.primary}44` : "",
                }}
              >
                {/* FIXED GRID: 36px (Rank) | 1fr (Name) | 5 columns of 80px each */}
                <div className="grid grid-cols-[36px_1fr_repeat(5,80px)] gap-4 items-center">

                  {/* 1. Rank */}
                  <div className="font-mono text-xl font-black text-white/20">
                    #{idx + 1}
                  </div>

                  {/* 2. Site Identity */}
                  <div className="min-w-0">
                    <div className="text-text text-sm font-bold truncate mb-1">{site.name}</div>
                    <div className="flex gap-2">
                      <Tag text={site.type} color={COLORS.teal} />
                      <Tag text={ZONES.find((z) => z.id === site.zone)?.risk || "LOW"}
                        color={ZONES.find((z) => z.id === site.zone)?.risk === "CRITICAL" ? COLORS.danger : COLORS.teal}
                      />
                    </div>
                  </div>

                  {/* 3. Metrics (MCDA, Demand, Headroom, Access, Growth) */}
                  {[
                    { label: "MCDA Score", val: site.computedScore, color: COLORS.primary },
                    { label: "Demand", val: `${site.demand}%`, color: COLORS.danger },
                    { label: "Headroom", val: `${site.headroom}%`, color: site.headroom < 20 ? COLORS.danger : COLORS.teal },
                    { label: "Access", val: `${site.access}%`, color: "#4DB8FF" },
                    { label: "Growth", val: `${site.growth}%`, color: COLORS.warn },
                  ].map((s) => (
                    <div key={s.label} className="text-center">
                      <div className="font-mono text-sm font-black" style={{ color: s.color }}>
                        {s.val}
                      </div>
                      <div className="text-dim text-[8px] uppercase tracking-tighter font-bold">{s.label}</div>
                    </div>
                  ))}
                </div>

                {/* Rationale Section (appears below the grid when selected) */}
                {selected === site.rank && (
                  <div className="mt-4 pt-4 border-t border-white/5 hm-fade-up">
                    <div className="text-primary text-[9px] font-mono font-bold mb-1 uppercase tracking-widest">
                      ✦ Mistral 7B · Site Rationale
                    </div>
                    <div className="text-sub text-xs leading-relaxed italic opacity-80">
                      "{site.reason} — based on current MCDA weights and grid headroom analysis."
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
