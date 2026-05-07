"use client";

import { useState, useEffect } from "react";
import { ALERTS, type NavItem, type StatusItem } from "@/lib/mockData";

// ─── Logo Components ─────────────────────────────────────────────────────────

interface MarkProps {
  S?: number;
  live?: boolean;
}

function Mark({ S = 80, live = false }: MarkProps) {
  const cx = S / 2;
  const cy = S / 2;
  const R = S * 0.42;
  const sc = S / 80;

  const hex = Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    return [cx + R * Math.cos(a), cy + R * Math.sin(a)];
  });
  const hexD = hex
    .map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`)
    .join(" ") + "Z";

  const NODE_R = 0.78;
  const nodes = hex.map(([hx, hy]) => ({
    x: cx + (hx - cx) * NODE_R,
    y: cy + (hy - cy) * NODE_R,
  }));

  const boltPts = [
    [cx + 6 * sc, cy - 15 * sc],
    [cx - 4 * sc, cy - 2 * sc],
    [cx + 1 * sc, cy - 2 * sc],
    [cx - 6 * sc, cy + 15 * sc],
    [cx + 4 * sc, cy + 2 * sc],
    [cx - 2 * sc, cy + 2 * sc],
  ];
  const boltD = boltPts
    .map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`)
    .join(" ") + "Z";

  const uid = `mk${S}x${Math.round(R)}`;

  return (
    <svg
      width={S}
      height={S}
      viewBox={`0 0 ${S} ${S}`}
      fill="none"
      style={{ overflow: "visible" }}
    >
      <defs>
        <linearGradient id={`g_${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#02C39A" />
          <stop offset="55%" stopColor="#0891B2" />
          <stop offset="100%" stopColor="#065A82" />
        </linearGradient>
        <filter id={`f_${uid}`} x="-70%" y="-70%" width="240%" height="240%">
          <feGaussianBlur stdDeviation={S * 0.05} result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <clipPath id={`c_${uid}`}>
          <path d={hexD} />
        </clipPath>
      </defs>

      {/* Ambient outer glow */}
      <path
        d={hexD}
        stroke={`url(#g_${uid})`}
        strokeWidth={S * 0.014}
        fill="none"
        opacity={0.12}
        transform={`scale(1.22) translate(${(-cx * 0.22).toFixed(2)} ${(-cy * 0.22).toFixed(2)})`}
        strokeLinejoin="round"
      />

      {/* Hex background */}
      <path d={hexD} fill="#0B0D14" />
      <path d={hexD} fill={`url(#g_${uid})`} opacity={0.07} />

      {/* Hex border */}
      <path
        d={hexD}
        stroke={`url(#g_${uid})`}
        strokeWidth={S * 0.028}
        fill="none"
        strokeLinejoin="round"
        className={live ? "logo-glow-anim" : undefined}
      />

      {/* Circuit traces */}
      <g clipPath={`url(#c_${uid})`} opacity={0.28}>
        {nodes.map((n, i) => (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={n.x}
            y2={n.y}
            stroke="#02C39A"
            strokeWidth={S * 0.011}
            strokeDasharray={`${S * 0.05} ${S * 0.038}`}
            className={live ? "logo-dash-anim" : undefined}
            style={live ? { animationDelay: `${i * 0.28}s` } : {}}
          />
        ))}
      </g>

      {/* 6 corner nodes */}
      {nodes.map((n, i) => (
        <g key={i}>
          <circle
            cx={n.x}
            cy={n.y}
            r={S * 0.036}
            fill="#0B0D14"
            stroke={`url(#g_${uid})`}
            strokeWidth={S * 0.018}
          />
          <circle
            cx={n.x}
            cy={n.y}
            r={S * 0.013}
            fill="#02C39A"
            className={live ? "logo-pulse-anim" : undefined}
            style={live ? { animationDelay: `${i * 0.48}s` } : {}}
          />
        </g>
      ))}

      {/* Lightning bolt */}
      <path d={boltD} fill={`url(#g_${uid})`} filter={`url(#f_${uid})`} />
      <path
        d={boltD}
        fill="white"
        opacity={0.1}
        transform={`translate(${(-S * 0.006).toFixed(2)} ${(-S * 0.006).toFixed(2)})`}
      />

      {/* Center anchor */}
      <circle cx={cx} cy={cy} r={S * 0.036} fill="#02C39A" opacity={0.5} />
    </svg>
  );
}

interface WordProps {
  scale?: number;
}

function Word({ scale = 1 }: WordProps) {
  return (
    <div
      className="flex flex-col"
      style={{ lineHeight: 1 }}
    >
      <div
        className="font-display font-extrabold text-text"
        style={{
          fontSize: 28 * scale,
          letterSpacing: "-0.02em",
          lineHeight: 1.05,
        }}
      >
        <span className="text-primary">Urja</span>
        <span>Yukti</span>
      </div>
      <div
        className="font-mono font-bold text-primary"
        style={{
          fontSize: 9 * scale,
          letterSpacing: "0.22em",
          marginTop: 3 * scale,
          textTransform: "uppercase",
        }}
      >
        AI · EV GRID INTELLIGENCE
      </div>
    </div>
  );
}

interface LockupProps {
  S?: number;
  scale?: number;
  live?: boolean;
  stacked?: boolean;
  markOnly?: boolean;
}

function Lockup({ S = 80, scale = 1, live = false, stacked = false, markOnly = false }: LockupProps) {
  if (markOnly) return <Mark S={S} live={live} />;
  return (
    <div
      className={`flex items-center gap-3`}
      style={{ flexDirection: stacked ? "column" : "row" }}
    >
      <Mark S={S} live={live} />
      <Word scale={scale} />
    </div>
  );
}

// ─── Live Ticker Component ─────────────────────────────────────────────────────

function LiveTicker() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const items = [
    "Zone 7 · Load 92% · CRITICAL",
    "VPP Shift: 340kWh deferred 8PM→12AM",
    "Zone 3 · Headroom 22% · HIGH",
    "Site #1 Whitefield scored 94/100",
    "Mistral 7B rationale ready",
    "0 constraint violations detected",
    "Forecast MAPE: 9.4% (TFT)",
    "LangGraph agents · All 3 online",
    "Karnataka EV reg +47 this week",
  ];

  return (
    <div className="bg-panel border-b border-border flex items-center overflow-hidden h-8 flex-shrink-0">
      <div className="bg-primary text-bg text-[9px] font-mono font-black px-3 h-full flex items-center tracking-[0.1em] flex-shrink-0">
        LIVE
      </div>
      <div className="overflow-hidden flex-1">
        <div
          className="flex gap-12 animate-ticker w-max px-6"
          style={{ animationDuration: "24s" }}
        >
          {[...items, ...items].map((item, i) => (
            <span
              key={`ticker-${i}`}
              className="text-sub text-[10px] font-mono whitespace-nowrap"
            >
              <span className="text-primary mr-2">◆</span>
              {item}
            </span>
          ))}
        </div>
        {/* Subtle Fade Effect */}
        <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-panel to-transparent pointer-events-none" />
        <div className="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-panel to-transparent pointer-events-none" />
      </div>
    </div>
  );
}

// ─── Sidebar Component ───────────────────────────────────────────────────────

interface SidebarProps {
  active: string;
  setActive: (id: string) => void;
  alertCount: number;
}

function Sidebar({ active, setActive, alertCount }: SidebarProps) {
  const navItems: NavItem[] = [
    { id: "overview", icon: "📊", label: "Overview", badge: null },
    { id: "heatmap", icon: "🗺️", label: "Demand Heatmap", badge: null },
    { id: "forecast", icon: "📈", label: "Demand Forecast", badge: null },
    { id: "vpp", icon: "⚡", label: "VPP Optimizer", badge: null },
    { id: "sites", icon: "🏫", label: "Site Planner", badge: null },
    { id: "alerts", icon: "📢", label: "Alert Center", badge: alertCount },
    { id: "agents", icon: "🤖", label: "Agent Console", badge: null },
  ];

  const statusItems: StatusItem[] = [
    { label: "TFT Forecast", status: "online", col: "#10B981" },
    { label: "LangGraph Agents", status: "3/3 active", col: "#10B981" },
    { label: "Mistral 7B VPC", status: "online", col: "#10B981" },
    { label: "TimescaleDB", status: "online", col: "#10B981" },
  ];

  return (
    <div className="w-[220px] bg-panel border-r border-border flex flex-col flex-shrink-0 h-full overflow-y-auto">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-border flex justify-center">
        <Lockup S={40} scale={0.7} live={false} />
      </div>

      {/* Navigation */}
      <div className="px-2 py-3 flex-1">
        <div className="text-white/40 text-[11px] font-black font-mono tracking-[0.3em] px-3 mb-4 mt-2 uppercase border-b border-white/5 pb-2">
          COMMAND CENTER
        </div>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${active === item.id ? "active" : ""}`}
            onClick={() => setActive(item.id)}
          >
            <span className="text-[14px] flex-shrink-0">{item.icon}</span>
            <span className="flex-1">{item.label}</span>
            {item.badge && (
              <span className="bg-danger text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full font-mono">
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Status */}
      <div className="px-3 py-3 border-t border-border flex flex-col gap-2">
        {statusItems.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <div className="pulse-dot w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: s.col }} />
            <span className="text-sub text-[10px] flex-1">{s.label}</span>
            <span className="font-mono text-[9px]" style={{ color: s.col }}>
              {s.status}
            </span>
          </div>
        ))}
        <div className="mt-1 px-2.5 py-2 bg-glass rounded-lg border border-border">
          <div className="text-sub text-[9px]">Decision Support Layer</div>
          <div className="text-primary text-[9px] font-mono font-bold mt-0.5">
            Zero BESCOM Modifications
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── TopBar Component ─────────────────────────────────────────────────────────

interface TopBarProps {
  view: string;
  viewTitle: string;
}

function TopBar({ view, viewTitle }: TopBarProps) {
  const [time, setTime] = useState(new Date());
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="bg-panel border-b border-border px-6 flex items-center justify-between h-[52px] flex-shrink-0 z-50">
      <div className="flex items-center gap-4">
        <Lockup S={28} scale={0.55} live={false} />
        <div className="w-px h-5 bg-border" />
        <div className="text-sub text-[11px]">{viewTitle}</div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex gap-2">
          <span className="tag bg-teal/18 text-teal border-teal/33">
            Decision Support Layer
          </span>
          <span className="tag bg-primary/18 text-primary border-primary/33">
            Zero BESCOM Modifications
          </span>
        </div>
        <div className="w-px h-5 bg-border" />
        <div className="font-mono text-[11px] text-sub">
          {mounted
            ? time.toLocaleString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              day: "2-digit",
              month: "short",
            })
            : ""}
        </div>
        <div className="w-2 h-2 rounded-full bg-success shadow-[0_0_8px_#10B981] pulse-dot" />
      </div>
    </div>
  );
}

// ─── Dashboard Layout Component ───────────────────────────────────────────────

interface DashboardLayoutProps {
  children: React.ReactNode;
  view: string;
  setView: (view: string) => void;
}

const VIEW_TITLES: Record<string, string> = {
  overview: "Command Center Overview",
  heatmap: "Demand Heatmap — Zone Intelligence",
  forecast: "Demand Forecast — TFT Model",
  vpp: "VPP Optimizer — Load Shifting",
  sites: "Site Planner — MCDA Ranking",
  alerts: "Alert Center",
  agents: "Agent Console — LangGraph",
};

export default function DashboardLayout({ children, view, setView }: DashboardLayoutProps) {
  const activeAlerts = ALERTS.filter((a) => !a.ack).length;

  return (
    <div className="flex flex-col h-screen bg-bg overflow-hidden">
      {/* Top Bar */}
      <TopBar view={view} viewTitle={VIEW_TITLES[view] || ""} />

      {/* Live Ticker */}
      <LiveTicker />

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={view} setActive={setView} alertCount={activeAlerts} />
        <main className="flex-1 overflow-y-auto p-6 flex flex-col gap-0 scrollbar-thin">
          {children}
        </main>
      </div>
    </div>
  );
}
