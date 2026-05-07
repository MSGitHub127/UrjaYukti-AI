"use client";

import { useState } from "react";
import { GlassCard, SectionLabel, Tag } from "@/components/ui/card";
import { COLORS } from "@/lib/mapLayers";
import { ALERTS } from "@/lib/mockData";

export default function AlertsView() {
  const [alerts, setAlerts] = useState(ALERTS);
  const ack = (id: number) => setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, ack: true } : a)));

  const active = alerts.filter((a) => !a.ack);
  const resolved = alerts.filter((a) => a.ack);

  return (
    <div className="flex flex-col gap-5">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-3.5">
        {[
          { label: "Active Alerts", value: active.length, color: COLORS.danger },
          { label: "Critical", value: active.filter((a) => a.severity === "CRITICAL").length, color: COLORS.danger },
          { label: "High", value: active.filter((a) => a.severity === "HIGH").length, color: COLORS.warn },
          { label: "Acknowledged", value: resolved.length, color: COLORS.success },
        ].map((s) => (
          <GlassCard key={s.label} className="card-hover" style={{ padding: "16px 20px", borderTop: `2px solid ${s.color}` }}>
            <div className="font-mono text-2xl font-bold" style={{ color: s.color }}>
              {s.value}
            </div>
            <div className="text-sub text-[11px] mt-1">{s.label}</div>
          </GlassCard>
        ))}
      </div>

      {/* Active Alerts */}
      {active.length > 0 && (
        <GlassCard style={{ padding: "22px" }}>
          <SectionLabel color={COLORS.danger}>Active Alerts — Requires Action</SectionLabel>
          <div className="flex flex-col gap-2.5">
            {active.map((alert) => {
              const col = alert.severity === "CRITICAL" ? COLORS.danger : alert.severity === "HIGH" ? COLORS.warn : COLORS.teal;
              return (
                <div
                  key={alert.id}
                  className="scale-in"
                  style={{
                    background: `${col}0A`,
                    border: `1px solid ${col}33`,
                    borderLeft: `3px solid ${col}`,
                    borderRadius: 10,
                    padding: "12px 16px", // Optimized padding to save space
                    display: "flex",       // Horizontal layout
                    alignItems: "center",  // Vertical center alignment
                    justifyContent: "space-between",
                    gap: "20px"
                  }}
                >
                  {/* LEFT SIDE: Alert Metadata & Message */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="pulse-dot w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: col }} />
                      <Tag text={alert.severity} color={col} />
                      <span className="text-sub text-[11px] font-bold tracking-tight">{alert.zone}</span>
                      <span className="text-dim text-[9px] font-mono ml-2 opacity-60">
                        {alert.time}
                      </span>
                    </div>

                    {/* Message now has the full remaining width to prevent "confinement" */}
                    <div className="text-text text-[11px] leading-relaxed max-w-[95%]">
                      {alert.msg}
                    </div>
                  </div>

                  {/* RIGHT SIDE: Compact Action Buttons */}
                  <div className="flex flex-col gap-1.5 flex-shrink-0 w-28">
                    <button
                      onClick={() => ack(alert.id)}
                      className="px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-widest transition-all hover:brightness-125"
                      style={{
                        background: "rgba(2,195,154,0.12)",
                        border: "1px solid rgba(2,195,154,0.3)",
                        color: COLORS.success,
                      }}
                    >
                      Acknowledge
                    </button>
                    <button
                      className="px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-widest transition-all hover:brightness-125"
                      style={{
                        background: `${col}12`,
                        border: `1px solid ${col}30`,
                        color: col,
                      }}
                    >
                      Take Action
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      )}

      {/* Acknowledged Alerts */}
      <GlassCard style={{ padding: "22px" }}>
        <SectionLabel color={COLORS.success}>Acknowledged</SectionLabel>
        <div className="flex flex-col gap-2">
          {resolved.map((alert) => {
            const col = alert.severity === "CRITICAL" ? COLORS.danger : alert.severity === "HIGH" ? COLORS.warn : COLORS.teal;
            return (
              <div
                key={alert.id}
                className="bg-glass border-border rounded-lg p-3 opacity-70"
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-1">
                    <span className="text-success">✓</span>
                    <Tag text={alert.severity} color={col} />
                    <span className="text-sub text-xs">{alert.zone}</span>
                    <span className="text-dim text-[9px] font-mono">—</span>
                    <span className="text-sub text-xs">{alert.msg}</span>
                  </div>
                  <span className="text-dim text-[9px] font-mono">{alert.time}</span>
                </div>
              </div>
            );
          })}
        </div>
      </GlassCard>
    </div>
  );
}
