"use client";

import { useState, useEffect } from "react";
import { AreaChart, Area, LineChart, Bar, BarChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { KPICard, GlassCard, SectionLabel, Tag } from "@/components/ui/card";
import ChartTooltip from "@/components/ui/chart";
import { COLORS } from "@/lib/mapLayers";
import { ZONES, forecastData, ARCHETYPE_DATA, ALERTS } from "@/lib/mockData";

export default function OverviewView() {
  const currentHour = new Date().getHours();
  const slice = forecastData.slice(Math.max(0, currentHour - 4), currentHour + 8);

  return (
    <div className="flex flex-col gap-5">
      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3.5">
        <KPICard
          label="PEAK LOAD REDUCTION"
          value="18%"
          sub="vs unmanaged baseline"
          color={COLORS.primary}
          trend="+3%"
          icon="⚡"
          delay={0}
        />
        <KPICard
          label="CRITICAL ZONES"
          value="1"
          sub="of 6 monitored zones"
          color={COLORS.danger}
          trend="+1"
          icon="⚠"
          delay={80}
        />
        <KPICard
          label="VPP SHIFTED LOAD"
          value="340"
          sub="kWh deferred tonight"
          color={COLORS.warn}
          trend="+12%"
          icon="↕"
          delay={160}
        />
        <KPICard
          label="FORECAST ACCURACY"
          value="90.6%"
          sub="MAPE 9.4% (TFT model)"
          color={COLORS.purple}
          trend="+2.1%"
          icon="◎"
          delay={240}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-[1.6fr_1fr] gap-3.5">
        {/* Live Demand Curve Chart */}
        <GlassCard className="fade-up" style={{ padding: "22px", animationDelay: "100ms" }}>
          <SectionLabel>Live Demand Curve — Next 8 Hours</SectionLabel>
          <div className="flex gap-4 mb-4 flex-wrap">
            {[
              { color: COLORS.danger, label: "Unmanaged EV Load" },
              { color: COLORS.primary, label: "UrjaYukti Optimized" },
              { color: COLORS.sub, label: "Grid Baseline" },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1.5">
                <div className="w-5 h-0.5 rounded-full" style={{ background: l.color }} />
                <span className="text-sub text-xs">{l.label}</span>
              </div>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={slice} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gEV" x1="0%" y1="0" x2="0%" y2="1">
                  <stop offset="5%" stopColor={COLORS.danger} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={COLORS.danger} stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="gOpt" x1="0%" y1="0" x2="0%" y2="1">
                  <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
              <XAxis
                dataKey="h"
                tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine
                y={280}
                stroke={COLORS.danger}
                strokeDasharray="4 4"
                strokeWidth={1}
                label={{ value: "N-1 Limit", fill: COLORS.danger, fontSize: 9, fontFamily: "JetBrains Mono" }}
              />
              <Area type="monotone" dataKey="ev" stroke={COLORS.danger} fill="url(#gEV)" strokeWidth={2} name="Unmanaged EV" />
              <Area type="monotone" dataKey="opt" stroke={COLORS.primary} fill="url(#gOpt)" strokeWidth={2} name="Optimized" />
              <Line type="monotone" dataKey="base" stroke={COLORS.sub} strokeDasharray="4 4" strokeWidth={1.5} dot={false} name="Baseline" />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Zone Risk Matrix */}
        <GlassCard className="fade-up" style={{ padding: "22px", animationDelay: "160ms" }}>
          <SectionLabel>Zone Risk Matrix</SectionLabel>
          <div className="flex flex-col gap-2">
            {ZONES.map((z, i) => {
              const col = z.risk === "CRITICAL" ? COLORS.danger : z.risk === "HIGH" ? COLORS.warn : COLORS.teal;
              return (
                <div
                  key={z.id}
                  className="fade-up"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2.5,
                    padding: "10px 12px",
                    background: `${col}0A`,
                    border: `1px solid ${col}22`,
                    borderRadius: 9,
                    borderLeft: `3px solid ${col}`,
                    animationDelay: `${i * 60}ms`,
                  }}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-[9px] text-dim">{z.id}</span>
                      <span className="text-text text-xs font-semibold">{z.name}</span>
                    </div>
                    <div className="h-1 w-full rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${z.load}%`, background: col }} />
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-base font-bold" style={{ color: col }}>{z.load}%</div>
                    <Tag text={z.risk} color={col} />
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1fr 1fr gap-3.5">
        {/* EV Archetype Demand Breakdown */}
        <GlassCard className="fade-up" style={{ padding: "22px", animationDelay: "200ms" }}>
          <SectionLabel>EV Archetype Demand Breakdown</SectionLabel>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={ARCHETYPE_DATA} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
              <XAxis dataKey="h" tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: COLORS.sub, fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: COLORS.card2, border: `1px solid ${COLORS.border}`, borderRadius: 10, fontSize: 10 }} />
              <Bar dataKey="fleet" fill={COLORS.blue} name="Fleet" radius={[3, 3, 0, 0]} stackId="a" />
              <Bar dataKey="commuter" fill={COLORS.danger} name="Commuter" radius={[3, 3, 0, 0]} stackId="a" />
              <Bar dataKey="oppo" fill={COLORS.primary} name="Opportunity" radius={[3, 3, 0, 0]} stackId="a" />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2.5 justify-center">
            {[
              { c: COLORS.danger, l: "Commuter (61%)" },
              { c: COLORS.blue, l: "Fleet (22%)" },
              { c: COLORS.primary, l: "Opportunity (17%)" },
            ].map((x) => (
              <div key={x.l} className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full" style={{ background: x.c }} />
                <span className="text-sub text-xs">{x.l}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Active Alerts */}
        <GlassCard className="fade-up" style={{ padding: "22px", animationDelay: "240ms" }}>
          <SectionLabel color={COLORS.danger}>Active Alerts</SectionLabel>
          <div className="flex flex-col gap-2">
            {ALERTS.filter((a) => !a.ack).slice(0, 3).map((alert) => {
              const col = alert.severity === "CRITICAL" ? COLORS.danger : alert.severity === "HIGH" ? COLORS.warn : COLORS.teal;
              return (
                <div
                  key={alert.id}
                  className="scale-in"
                  style={{
                    background: `${col}0A`,
                    border: `1px solid ${col}33`,
                    borderLeft: `3px solid ${col}`,
                    borderRadius: 8,
                    padding: "10px 12px",
                  }}
                >
                  <div className="flex justify-between items-center mb-1">
                    <div className="flex items-center gap-1.5">
                      <div className="pulse-dot w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: col }} />
                      <Tag text={alert.severity} color={col} />
                      <span className="text-sub text-xs">{alert.zone}</span>
                    </div>
                    <span className="text-dim text-[9px] font-mono">{alert.time}</span>
                  </div>
                  <div className="text-text text-xs leading-relaxed">{alert.msg}</div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
