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
                    padding: "16px 18px",
                  }}
                >
                  <div className="flex justify-between items-center mb-1">
                    <div className="flex items-center gap-1.5">
                      <div className="pulse-dot w-2 h-2 rounded-full flex-shrink-0" style={{ background: col }} />
                      <Tag text={alert.severity} color={col} />
                      <span className="text-sub text-xs">{alert.zone}</span>
                      <span className="text-dim text-[9px] font-mono ml-auto">
                        {alert.time}
                      </span>
                    </div>
                  </div>
                  <div className="text-text text-xs leading-relaxed">{alert.msg}</div>
                  <div className="flex flex-col gap-2 flex-shrink-0">
                    <button
                      onClick={() => ack(alert.id)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold"
                      style={{
                        background: "rgba(2,195,154,0.18)",
                        border: "1px solid rgba(2,195,154,0.44)",
                        color: COLORS.success,
                      }}
                    >
                      Acknowledge
                    </button>
                    <button
                      className="px-3 py-1.5 rounded-lg text-xs font-bold"
                      style={{
                        background: `${col}18`,
                        border: `1px solid ${col}44`,
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
