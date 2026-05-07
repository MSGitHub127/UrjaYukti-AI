"use client";

import { useState } from "react";
import { AreaChart, Area, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { GlassCard, SectionLabel, Tag, Mono } from "@/components/ui/card";
import { COLORS } from "@/lib/mapLayers";
import { forecastData, ZONES } from "@/lib/mockData";

export default function VPPView() {
  const [compliance, setCompliance] = useState(70);
  const [applied, setApplied] = useState(false);
  const [applying, setApplying] = useState(false);

  const reduction = Math.round(compliance * 0.257);
  const shifted = Math.round(compliance * 4.857);

  const handleApply = () => {
    setApplying(true);
    setTimeout(() => {
      setApplying(false);
      setApplied(true);
    }, 2200);
  };

  const scheduleData = forecastData.map((d) => ({
    h: d.h,
    before: d.ev,
    after: applied ? d.opt : d.ev,
  }));

  return (
    <div className="flex flex-col gap-5">
      {/* LP Formulation Card */}
      <GlassCard style={{ padding: "16px 22px" }}>
        <div className="flex items-center gap-5 flex-wrap">
          <div>
            <div className="text-primary text-[9px] font-mono font-bold mb-1">LP FORMULATION · ACTIVE</div>
            <div className="text-text text-xs">
              min <span className="text-primary">Σ PLI(t)</span> &nbsp;|&nbsp; s.t. Σ x<sub>ij</sub>·kWh ≤ C<sub>transformer</sub>(t) ∀t &nbsp;|&nbsp; shifted ≤ <span className="text-warn">70%</span> off-peak capacity
            </div>
          </div>
          <div className="ml-auto flex gap-2.5">
            <Tag text="OR-Tools LP" color={COLORS.primary} />
            <Tag text="N-1 Constraint Active" color={COLORS.danger} />
            <Tag text="0 Violations" color={COLORS.success} />
          </div>
        </div>
      </GlassCard>

      {/* Main Content */}
      <div className="grid grid-cols-[1.5fr_1fr] gap-5">
        {/* Load Shift Chart */}
        <GlassCard style={{ padding: "22px" }}>
          <SectionLabel>Load Shift — Before vs After VPP Optimization</SectionLabel>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={scheduleData} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="vBef" x1="0%" y1="0" x2="0%" y2="1">
                  <stop offset="5%" stopColor={COLORS.danger} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={COLORS.danger} stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="vAft" x1="0%" y1="0" x2="0%" y2="1">
                  <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
              <XAxis dataKey="h" tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: COLORS.card2, border: `1px solid ${COLORS.border}`, borderRadius: 10, fontSize: 10 }} />
              <ReferenceLine y={300} stroke={COLORS.danger + "88"} strokeDasharray="4 4" strokeWidth={1} />
              <Area type="monotone" dataKey="before" stroke={COLORS.danger} fill="url(#vBef)" strokeWidth={2} name="Before" strokeDasharray={applied ? "4 4" : "0"} />
              <Area type="monotone" dataKey="after" stroke={COLORS.primary} fill="url(#vAft)" strokeWidth={2.5} name="After" />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Side Column */}
        <div className="flex flex-col gap-3.5">
          {/* Compliance Configuration */}
          <GlassCard style={{ padding: "20px" }}>
            <SectionLabel>Compliance Configuration</SectionLabel>
            <div className="mb-4">
              <div className="flex justify-between mb-2">
                <span className="text-text text-xs font-semibold">User Compliance Rate</span>
                <Mono color={COLORS.warn}>{compliance}%</Mono>
              </div>
              <input
                type="range"
                min={10}
                max={95}
                value={compliance}
                onChange={(e) => setCompliance(Number(e.target.value))}
                className="w-full h-1.5 rounded-full"
                style={{
                  background: `linear-gradient(90deg,${COLORS.primary} ${compliance}%,${COLORS.card2} ${compliance}%)`,
                }}
              />
              <div className="flex justify-between mt-1">
                <span className="text-dim text-[9px] font-mono">Pessimistic 10%</span>
                <span className="text-dim text-[9px] font-mono">Optimistic 95%</span>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {[
                { scenario: "Pessimistic", pct: 30, col: COLORS.danger },
                { scenario: "Realistic", pct: compliance, col: COLORS.warn },
                { scenario: "Optimistic", pct: 85, col: COLORS.success },
              ].map((s) => (
                <div key={s.scenario}>
                  <div className="flex justify-between mb-1">
                    <span className="text-sub text-xs">{s.scenario}</span>
                    <span className="font-mono text-xs" style={{ color: s.col }}>
                      {Math.round(s.pct * 0.257)}% reduction
                    </span>
                  </div>
                  <div className="h-1 w-full rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${(s.pct * 0.257 / 25) * 100}%`, background: s.col, borderRadius: 99, transition: "width 0.4s ease" }} />
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Shift Schedule */}
          <GlassCard style={{ padding: "20px" }}>
            <SectionLabel color={COLORS.warn}>Shift Schedule — Zone 7 Whitefield</SectionLabel>
            <div className="flex flex-col gap-2">
              {[
                { slot: "18:00–20:00", action: "Defer 180 kWh", dir: "↓", col: COLORS.danger },
                { slot: "20:00–22:00", action: "Defer 160 kWh", dir: "↓", col: COLORS.danger },
                { slot: "22:00–00:00", action: "Absorb 180 kWh", dir: "≈", col: COLORS.teal },
                { slot: "00:00–02:00", action: "Route 340 kWh", dir: "↑", col: COLORS.primary },
                { slot: "02:00–04:00", action: "Off-peak buffer", dir: "◎", col: COLORS.success },
              ].map((s) => (
                <div
                  key={s.slot}
                  className="flex items-center gap-2.5 rounded-lg p-2"
                  style={{
                    background: `${s.col}0A`,
                    border: `1px solid ${s.col}22`,
                  }}
                >
                  <span className="text-[16px] font-bold w-5 text-center" style={{ color: s.col }}>
                    {s.dir}
                  </span>
                  <span className="font-mono text-xs text-sub w-[110px]">{s.slot}</span>
                  <span className="text-text text-xs flex-1">{s.action}</span>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Apply Button */}
          <GlassCard style={{ padding: "16px" }}>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="text-center bg-card2 rounded-lg p-2">
                <Mono color={COLORS.primary} size={22}>{shifted} kWh</Mono>
                <div className="text-sub text-[9px] mt-0.5">Total shifted load</div>
              </div>
              <div className="text-center bg-card2 rounded-lg p-2">
                <Mono color={COLORS.warn} size={22}>{reduction}%</Mono>
                <div className="text-sub text-[9px] mt-0.5">PLI reduction</div>
              </div>
            </div>
            <button
              onClick={handleApply}
              disabled={applying || applied}
              className="w-full py-3 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-all"
              style={{
                background: applied ? COLORS.success + "18" : applying ? COLORS.warn + "18" : COLORS.primary + "18",
                border: `1px solid ${applied ? COLORS.success : applying ? COLORS.warn : COLORS.primary}55`,
                color: applied ? COLORS.success : applying ? COLORS.warn : COLORS.primary,
              }}
            >
              {applying && (
                <div className="spin w-3 h-3 rounded-full border-2 border-t-2" style={{ borderColor: "#F59E0B33", borderTopColor: "#F59E0B" }} />
              )}
              {applying ? "Optimizing schedule…" : applied ? "✓ Schedule Applied" : "Apply VPP Schedule"}
            </button>
            {applied && (
              <div className="mt-2.5 p-2 rounded-lg" style={{ background: "rgba(2,195,154,0.11)", border: "1px solid rgba(2,195,154,0.2)" }}>
                <div className="text-success text-[10px] font-bold mb-1">✓ Recommendation sent to operator</div>
                <div className="text-sub text-[10px]">Confidence: 84% · 0 constraint violations · Auditable</div>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
