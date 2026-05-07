"use client";

import { useState, useRef, useEffect, useCallback } from "react";

/* ── Types ───────────────────────────────────────────────────────────────── */
interface DemandNodeData {
  x: number; y: number; load: number;
  type: "peak" | "high" | "opt"; ms: number;
}

interface HeatmapZone {
  id: string; name: string; zoneId: string;
  points: string; vbZoom: [number, number, number, number];
  cx: number; cy: number;
  load: number; headroom: number; evDensity: number; growth: string;
  risk: "CRITICAL" | "HIGH" | "MODERATE" | "LOW"; rCol: string; score: number;
  nodes: DemandNodeData[];
  rec: string;
}

interface ViewBox { x: number; y: number; w: number; h: number; }

/* ── Design Tokens ───────────────────────────────────────────────────────── */
const T = {
  bg: "#0B0D14", card: "#141B2D", card2: "#1A2340",
  border: "rgba(255,255,255,0.07)", primary: "#02C39A",
  teal: "#0891B2", cyan: "#00E5FF", text: "#F0F6FC",
  sub: "#8B949E", dim: "#30363D", warn: "#F59E0B",
  danger: "#F43F5E", purple: "#A78BFA", success: "#10B981",
};

/* ── Zone Data ───────────────────────────────────────────────────────────── */
const ZONES: HeatmapZone[] = [
  {
    id: "whitefield", name: "Whitefield", zoneId: "Z7",
    points: "582,192 690,200 748,244 745,310 706,350 638,372 576,350 543,300 551,240",
    vbZoom: [510, 168, 268, 232], cx: 648, cy: 282,
    load: 92, headroom: 8, evDensity: 94, growth: "+28%",
    risk: "CRITICAL", rCol: "#F43F5E", score: 94,
    nodes: [
      { x: 610, y: 228, load: 95, type: "peak", ms: 0 },
      { x: 671, y: 250, load: 88, type: "peak", ms: 380 },
      { x: 703, y: 300, load: 76, type: "high", ms: 180 },
      { x: 648, y: 338, load: 82, type: "peak", ms: 560 },
      { x: 578, y: 298, load: 60, type: "opt", ms: 760 },
      { x: 627, y: 274, load: 90, type: "peak", ms: 140 },
    ],
    rec: "Shift 340 kWh · 20:00–22:00 → 00:00–02:00 · Peak reduction: 18.3% · 0 constraint violations",
  },
  {
    id: "hsr", name: "HSR Layout", zoneId: "Z3",
    points: "352,450 450,440 498,455 514,504 490,545 440,558 390,546 352,516 340,474",
    vbZoom: [308, 418, 232, 175], cx: 428, cy: 498,
    load: 78, headroom: 22, evDensity: 76, growth: "+22%",
    risk: "HIGH", rCol: "#F59E0B", score: 81,
    nodes: [
      { x: 368, y: 470, load: 78, type: "peak", ms: 0 },
      { x: 432, y: 460, load: 70, type: "high", ms: 300 },
      { x: 476, y: 490, load: 62, type: "high", ms: 500 },
      { x: 460, y: 530, load: 52, type: "opt", ms: 700 },
      { x: 396, y: 530, load: 58, type: "opt", ms: 200 },
    ],
    rec: "Defer 220 kWh · 23:00–01:00 window · 12% PLI reduction at 70% compliance",
  },
  {
    id: "indiranagar", name: "Indiranagar", zoneId: "Z1",
    points: "386,210 474,200 512,224 508,242 484,252 480,318 436,328 390,316 368,276",
    vbZoom: [344, 180, 200, 175], cx: 440, cy: 264,
    load: 71, headroom: 29, evDensity: 68, growth: "+18%",
    risk: "MODERATE", rCol: "#0891B2", score: 75,
    nodes: [
      { x: 406, y: 230, load: 71, type: "high", ms: 0 },
      { x: 464, y: 220, load: 62, type: "high", ms: 400 },
      { x: 490, y: 270, load: 50, type: "opt", ms: 200 },
      { x: 445, y: 308, load: 55, type: "opt", ms: 600 },
    ],
    rec: "Partial shift · 180 kWh to 22:00–00:00 · 9% PLI reduction achievable",
  },
  {
    id: "koramangala", name: "Koramangala", zoneId: "Z9",
    points: "368,325 436,328 480,318 498,360 482,400 448,420 394,420 346,400 336,360",
    vbZoom: [304, 300, 222, 156], cx: 416, cy: 370,
    load: 65, headroom: 35, evDensity: 58, growth: "+15%",
    risk: "MODERATE", rCol: "#0891B2", score: 68,
    nodes: [
      { x: 386, y: 346, load: 65, type: "high", ms: 0 },
      { x: 448, y: 340, load: 55, type: "opt", ms: 500 },
      { x: 464, y: 388, load: 48, type: "opt", ms: 300 },
      { x: 414, y: 408, load: 44, type: "opt", ms: 700 },
    ],
    rec: "Headroom sufficient · Off-peak opportunity charging 22:00–05:00 recommended",
  },
  {
    id: "electronic-city", name: "Electronic City", zoneId: "Z11",
    points: "370,550 440,558 490,545 514,504 530,574 522,628 478,650 428,644 380,610 364,570",
    vbZoom: [332, 480, 228, 202], cx: 444, cy: 582,
    load: 58, headroom: 42, evDensity: 52, growth: "+31%",
    risk: "LOW", rCol: "#10B981", score: 71,
    nodes: [
      { x: 394, y: 570, load: 58, type: "opt", ms: 0 },
      { x: 452, y: 560, load: 48, type: "opt", ms: 400 },
      { x: 490, y: 520, load: 42, type: "opt", ms: 200 },
      { x: 468, y: 614, load: 35, type: "opt", ms: 600 },
    ],
    rec: "Highest growth +31% · Proactive fast-charger deployment at SEZ Phase II · Priority site",
  },
  {
    id: "marathahalli", name: "Marathahalli", zoneId: "Z5",
    points: "486,240 556,234 582,252 578,350 548,370 496,356 466,320 470,260",
    vbZoom: [444, 212, 176, 185], cx: 524, cy: 300,
    load: 52, headroom: 48, evDensity: 44, growth: "+19%",
    risk: "LOW", rCol: "#10B981", score: 63,
    nodes: [
      { x: 506, y: 260, load: 52, type: "opt", ms: 0 },
      { x: 550, y: 270, load: 44, type: "opt", ms: 300 },
      { x: 556, y: 316, load: 38, type: "opt", ms: 500 },
      { x: 510, y: 340, load: 34, type: "opt", ms: 200 },
    ],
    rec: "Adequate headroom · Mixed AC/DC station at ORR junction · MCDA score 63/100",
  },
];

const VB_FULL: ViewBox = { x: 295, y: 162, w: 515, h: 530 };

/* ── Helpers ─────────────────────────────────────────────────────────────── */
const nodeColor = (t: DemandNodeData["type"]) =>
  t === "peak" ? "#F43F5E" : t === "high" ? "#F59E0B" : "#02C39A";
const nodeR = (l: number) => 3.5 + (l / 100) * 4.5;

function easeInOutCubic(t: number) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/* ── CSS (keyframes injected once) ───────────────────────────────────────── */
const HEATMAP_CSS = `
  @keyframes hmRippleOut  { 0%{transform:scale(1);opacity:.55} 100%{transform:scale(3.2);opacity:0} }
  @keyframes hmInnerBeat  { 0%,100%{transform:scale(1);opacity:.95} 50%{transform:scale(1.35);opacity:1} }
  @keyframes hmFlowMove   { to{stroke-dashoffset:-22} }
  @keyframes hmDrawPerim  { from{stroke-dashoffset:3200} to{stroke-dashoffset:0} }
  @keyframes hmPerimGlow  {
    0%,100%{ filter:drop-shadow(0 0 5px #00E5FF) drop-shadow(0 0 12px rgba(0,229,255,.5)) }
    50%    { filter:drop-shadow(0 0 12px #00E5FF) drop-shadow(0 0 28px rgba(0,229,255,.8)) }
  }
  @keyframes hmSlideInR   { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }
  @keyframes hmLiveBlink  { 0%,100%{opacity:1} 50%{opacity:.3} }
  @keyframes hmTickerMove { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
  @keyframes hmFadeUp     { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }

  .hm-ripple    { transform-box:fill-box; transform-origin:center; animation:hmRippleOut 2s ease-out infinite; }
  .hm-beat      { transform-box:fill-box; transform-origin:center; animation:hmInnerBeat 1.6s ease-in-out infinite; }
  .hm-flow      { stroke-dasharray:8 6; animation:hmFlowMove 1.2s linear infinite; }
  .hm-draw-perim{
    stroke-dasharray:3200;
    animation:hmDrawPerim 1.4s cubic-bezier(.4,0,.2,1) forwards,
              hmPerimGlow 2.8s ease-in-out 1.4s infinite;
  }
  .hm-slide-inR { animation:hmSlideInR .4s cubic-bezier(.4,0,.2,1) forwards; }
  .hm-live-blink{ animation:hmLiveBlink 2s ease-in-out infinite; }
  .hm-fade-up   { animation:hmFadeUp .45s cubic-bezier(.4,0,.2,1) forwards; }
`;

/* ── Sub-component: Demand Node ──────────────────────────────────────────── */
function DemandNode({ x, y, load, type, ms, zoomed }: DemandNodeData & { zoomed: boolean }) {
  const col = nodeColor(type);
  const r = nodeR(load) * (zoomed ? 1 : 0.7);
  const rOut = r * 2.6;
  return (
    <g>
      <circle cx={x} cy={y} r={rOut} fill="none" stroke={col} strokeWidth={0.7}
        className="hm-ripple" style={{ animationDelay: `${ms}ms`, opacity: 0.45 }} />
      <circle cx={x} cy={y} r={r} fill={col}
        className="hm-beat" style={{ animationDelay: `${ms}ms` }} />
      {zoomed && load >= 75 && (
        <text x={x} y={y - r - 4} textAnchor="middle"
          style={{ fontSize: 7, fontFamily: "'JetBrains Mono',monospace", fill: col, fontWeight: 700 }}>
          {load}%
        </text>
      )}
    </g>
  );
}

/* ── Sub-component: Stats Panel ──────────────────────────────────────────── */
function StatsPanel({ zone, onClose }: { zone: HeatmapZone; onClose: () => void }) {
  const peakNodes = zone.nodes.filter(n => n.type === "peak").length;
  const highNodes = zone.nodes.filter(n => n.type === "high").length;
  const optNodes = zone.nodes.filter(n => n.type === "opt").length;

  return (
    <div className="hm-slide-inR" style={{
      width: 268, flexShrink: 0,
      background: T.card, border: `1px solid ${T.border}`,
      borderRadius: 14, display: "flex", flexDirection: "column",
      overflow: "hidden",
      boxShadow: `0 0 40px rgba(0,229,255,.08), 0 8px 32px rgba(0,0,0,.5)`,
    }}>
      {/* Header */}
      <div style={{
        padding: "14px 16px 12px",
        background: `linear-gradient(135deg,${zone.rCol}18,transparent)`,
        borderBottom: `1px solid ${T.border}`,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fontWeight: 700, color: zone.rCol, letterSpacing: "0.12em", marginBottom: 4 }}>
              {zone.zoneId} · {zone.risk}
            </div>
            <div style={{ fontFamily: "'Syne',sans-serif", fontSize: 18, fontWeight: 800, color: T.text }}>{zone.name}</div>
          </div>
          <button onClick={onClose} style={{
            background: "rgba(255,255,255,.06)", border: `1px solid ${T.border}`,
            color: T.sub, width: 26, height: 26, borderRadius: 6, fontSize: 12,
            display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
          }}>✕</button>
        </div>
        <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
          <span style={{ background: zone.rCol + "22", color: zone.rCol, border: `1px solid ${zone.rCol}44`, padding: "2px 8px", borderRadius: 99, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", fontWeight: 700 }}>{zone.risk}</span>
          <span style={{ background: "rgba(0,229,255,.12)", color: T.cyan, border: "1px solid rgba(0,229,255,.3)", padding: "2px 8px", borderRadius: 99, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", fontWeight: 700 }}>MCDA {zone.score}/100</span>
        </div>
      </div>

      <div style={{ padding: "14px 16px", overflowY: "auto", flex: 1 }}>
        {/* Load bar */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
            <span style={{ color: T.sub, fontSize: 10 }}>Current Load</span>
            <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 14, fontWeight: 800, color: zone.rCol }}>{zone.load}%</span>
          </div>
          <div style={{ background: T.card2, borderRadius: 99, height: 6, overflow: "hidden" }}>
            <div style={{ width: `${zone.load}%`, height: "100%", borderRadius: 99, background: `linear-gradient(90deg,${zone.rCol},${zone.rCol}88)`, boxShadow: `0 0 8px ${zone.rCol}66` }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
            <span style={{ color: T.dim, fontSize: 9, fontFamily: "'JetBrains Mono',monospace" }}>0%</span>
            <span style={{ color: zone.headroom < 15 ? T.danger : T.sub, fontSize: 9, fontFamily: "'JetBrains Mono',monospace" }}>Headroom {zone.headroom}%</span>
          </div>
        </div>

        {/* KPI grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
          {[
            { l: "EV Density", v: zone.evDensity + "/100", c: T.purple },
            { l: "Growth", v: zone.growth, c: T.success },
            { l: "Score", v: zone.score + "/100", c: T.primary },
            { l: "Headroom", v: zone.headroom + "%", c: zone.headroom < 15 ? T.danger : T.teal },
          ].map(k => (
            <div key={k.l} style={{ background: T.card2, borderRadius: 8, padding: "8px 10px", border: `1px solid ${T.border}` }}>
              <div style={{ color: T.sub, fontSize: 9, marginBottom: 3 }}>{k.l}</div>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 15, fontWeight: 800, color: k.c }}>{k.v}</div>
            </div>
          ))}
        </div>

        {/* Node summary */}
        <div style={{ marginBottom: 14, padding: "10px 12px", background: T.card2, borderRadius: 10, border: `1px solid ${T.border}` }}>
          <div style={{ color: T.sub, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 8 }}>DEMAND NODES</div>
          <div style={{ display: "flex", gap: 10 }}>
            {[
              { col: T.danger, label: "Peak", count: peakNodes },
              { col: T.warn, label: "High", count: highNodes },
              { col: T.primary, label: "Optimal", count: optNodes },
            ].map(n => (
              <div key={n.label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: n.col, boxShadow: `0 0 6px ${n.col}` }} />
                <span style={{ color: T.text, fontSize: 11, fontWeight: 600 }}>{n.count}</span>
                <span style={{ color: T.sub, fontSize: 10 }}>{n.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* VPP recommendation */}
        <div style={{ padding: "12px", background: "rgba(2,195,154,.06)", border: "1px solid rgba(2,195,154,.2)", borderRadius: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 7 }}>
            <div className="hm-live-blink" style={{ width: 6, height: 6, borderRadius: "50%", background: T.primary }} />
            <span style={{ color: T.primary, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", fontWeight: 800 }}>MISTRAL 7B · VPP RECOMMENDATION</span>
          </div>
          <div style={{ color: T.text, fontSize: 11, lineHeight: 1.7, fontStyle: "italic" }}>"{zone.rec}"</div>
          <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["0 Violations", "Confidence 84%"].map(t => (
              <span key={t} style={{ background: "rgba(2,195,154,.12)", color: T.primary, border: "1px solid rgba(2,195,154,.25)", padding: "2px 8px", borderRadius: 99, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", fontWeight: 700 }}>{t}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
════════════════════════════════════════════════════════════════════════════ */
export default function HeatmapView() {
  const [selected, setSelected] = useState<string | null>(null);
  const [perimKey, setPerimKey] = useState(0);
  const [hovered, setHovered] = useState<string | null>(null);

  const svgRef = useRef<SVGSVGElement>(null);
  const animRef = useRef<number | null>(null);
  const vbRef = useRef<ViewBox>({ ...VB_FULL });

  /* ── Smooth viewBox camera swoop ───────────────────────────────────────── */
  const animateVB = useCallback((target: ViewBox, duration = 1000) => {
    if (animRef.current) cancelAnimationFrame(animRef.current);
    const start = { ...vbRef.current };
    const t0 = performance.now();

    function tick(now: number) {
      const p = Math.min((now - t0) / duration, 1);
      const ease = easeInOutCubic(p);
      const cur: ViewBox = {
        x: start.x + (target.x - start.x) * ease,
        y: start.y + (target.y - start.y) * ease,
        w: start.w + (target.w - start.w) * ease,
        h: start.h + (target.h - start.h) * ease,
      };
      vbRef.current = cur;
      svgRef.current?.setAttribute("viewBox", `${cur.x} ${cur.y} ${cur.w} ${cur.h}`);
      if (p < 1) animRef.current = requestAnimationFrame(tick);
    }
    animRef.current = requestAnimationFrame(tick);
  }, []);

  /* ── Zone select / deselect ────────────────────────────────────────────── */
  const handleSelect = useCallback((id: string) => {
    if (id === selected) {
      setSelected(null);
      animateVB(VB_FULL);
    } else {
      const z = ZONES.find(z => z.id === id);
      if (!z) return;
      setSelected(id);
      setPerimKey(k => k + 1);
      animateVB({ x: z.vbZoom[0], y: z.vbZoom[1], w: z.vbZoom[2], h: z.vbZoom[3] });
    }
  }, [selected, animateVB]);

  /* ── Cleanup ───────────────────────────────────────────────────────────── */
  useEffect(() => () => { if (animRef.current) cancelAnimationFrame(animRef.current); }, []);

  const selZone = selected ? ZONES.find(z => z.id === selected) ?? null : null;
  const hovZone = hovered ? ZONES.find(z => z.id === hovered) ?? null : null;

  return (
    <>
      {/* Inject keyframes once */}
      <style dangerouslySetInnerHTML={{ __html: HEATMAP_CSS }} />

      <div style={{
        display: "flex", flexDirection: "column",
        height: "calc(100vh - 84px)", /* adjust to match your shell height */
        minHeight: 600,
        background: T.bg, borderRadius: 14,
        border: `1px solid ${T.border}`, overflow: "hidden",
      }}>

        {/* ── Zone Selector Bar ────────────────────────────────────────────── */}
        <div style={{
          background: "rgba(11,13,20,.95)", borderBottom: `1px solid ${T.border}`,
          padding: "10px 20px", display: "flex", gap: 8,
          flexWrap: "wrap", flexShrink: 0, alignItems: "center",
        }}>
          {/* Live indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: 8 }}>
            <div className="hm-live-blink" style={{ width: 6, height: 6, borderRadius: "50%", background: T.primary }} />
            <span style={{ color: T.primary, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", fontWeight: 700 }}>
              LIVE · {ZONES.length} ZONES
            </span>
          </div>

          {/* All Zones */}
          <button
            onClick={() => { setSelected(null); animateVB(VB_FULL); }}
            style={{
              background: !selected ? "rgba(2,195,154,.12)" : "rgba(255,255,255,.04)",
              border: `1px solid ${!selected ? "rgba(2,195,154,.4)" : T.border}`,
              color: !selected ? T.primary : T.sub,
              padding: "5px 12px", borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: "pointer",
            }}>
            All Zones
          </button>

          {/* Per-zone buttons */}
          {ZONES.map(z => (
            <button key={z.id} onClick={() => handleSelect(z.id)} style={{
              background: selected === z.id ? z.rCol + "22" : "rgba(255,255,255,.04)",
              border: `1px solid ${selected === z.id ? z.rCol + "66" : T.border}`,
              color: selected === z.id ? z.rCol : T.sub,
              padding: "5px 12px", borderRadius: 8, fontSize: 11, fontWeight: 600,
              display: "flex", alignItems: "center", gap: 6, cursor: "pointer",
            }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: z.rCol, boxShadow: selected === z.id ? `0 0 6px ${z.rCol}` : "none" }} />
              {z.name}
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fontWeight: 700 }}>{z.load}%</span>
            </button>
          ))}

          {/* Back to full city */}
          {selected && (
            <button onClick={() => handleSelect(selected)} style={{
              background: "rgba(255,255,255,.05)", border: `1px solid ${T.border}`,
              color: T.sub, padding: "5px 12px", borderRadius: 7, fontSize: 11,
              cursor: "pointer", marginLeft: "auto",
            }}>← Full City View</button>
          )}
        </div>

        {/* ── Main Map + Stats ─────────────────────────────────────────────── */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

          {/* SVG Map */}
          <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
            <svg
              ref={svgRef}
              width="100%" height="100%"
              viewBox={`${VB_FULL.x} ${VB_FULL.y} ${VB_FULL.w} ${VB_FULL.h}`}
              style={{ display: "block" }}
            >
              <defs>
                <pattern id="hmRoads" width="28" height="28" patternUnits="userSpaceOnUse">
                  <path d="M 28 0 L 0 0 0 28" fill="none" stroke="rgba(255,255,255,.025)" strokeWidth="0.4" />
                </pattern>
                <radialGradient id="hmCityGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="rgba(28,114,147,.15)" />
                  <stop offset="100%" stopColor="rgba(11,13,20,0)" />
                </radialGradient>
                <filter id="hmCyanGlow" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
                <filter id="hmZoneGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              </defs>

              {/* Background */}
              <rect x="0" y="0" width="900" height="800" fill={T.bg} />
              <rect x="0" y="0" width="900" height="800" fill="url(#hmRoads)" />
              <ellipse cx="540" cy="390" rx="300" ry="270" fill="url(#hmCityGlow)" opacity={0.7} />
              <polygon
                points="320,155 510,142 680,165 780,225 810,350 790,490 720,590 600,660 480,678 370,660 280,580 245,450 260,320 290,215"
                fill="rgba(28,35,64,.4)" stroke="rgba(28,114,147,.12)" strokeWidth="0.5"
              />

              {/* Inter-zone flow lines */}
              {!selected && ZONES.slice(0, -1).map((z, i) => {
                const next = ZONES[i + 1];
                const mx = (z.cx + next.cx) / 2, my = (z.cy + next.cy) / 2;
                const col = z.load > 80 ? T.danger : z.load > 65 ? T.warn : T.teal;
                return (
                  <g key={`flow-${z.id}`}>
                    <line x1={z.cx} y1={z.cy} x2={next.cx} y2={next.cy}
                      stroke={col} strokeWidth={1.2} opacity={0.3}
                      className="hm-flow" style={{ animationDelay: `${i * 0.2}s` }} />
                    <circle cx={mx} cy={my} r={2.5} fill={col} opacity={0.5} />
                  </g>
                );
              })}

              {/* Zone polygons */}
              {ZONES.map(z => {
                const isSel = selected === z.id;
                const isFaded = !!selected && !isSel;
                const isHov = hovered === z.id && !selected;
                const fillOp = isFaded ? 0.04 : isSel ? 0.16 : isHov ? 0.2 : 0.11;
                const strokeCol = isFaded ? "rgba(255,255,255,.06)" : (isSel || isHov) ? z.rCol : z.rCol + "77";
                const strokeW = isSel ? 1.8 : isHov ? 1.4 : 1.0;

                return (
                  <g key={z.id} style={{ cursor: "pointer" }}
                    onClick={() => handleSelect(z.id)}
                    onMouseEnter={() => !selected && setHovered(z.id)}
                    onMouseLeave={() => setHovered(null)}>

                    <polygon points={z.points} fill={z.rCol} fillOpacity={fillOp}
                      stroke={strokeCol} strokeWidth={strokeW} strokeLinejoin="round"
                      filter={isSel ? "url(#hmZoneGlow)" : undefined}
                      style={{ transition: "fill-opacity .5s ease, stroke .4s ease" }} />

                    {/* Animated cyan perimeter when selected */}
                    {isSel && (
                      <polygon key={`cp-${z.id}-${perimKey}`} points={z.points}
                        fill="none" stroke={T.cyan} strokeWidth={2.2} strokeLinejoin="round"
                        className="hm-draw-perim" filter="url(#hmCyanGlow)" />
                    )}

                    {/* Hover highlight */}
                    {isHov && <polygon points={z.points} fill={z.rCol} fillOpacity={0.08} stroke="none" />}

                    {/* Zone label pill */}
                    {!isFaded && (
                      <g>
                        <rect x={z.cx - 28} y={z.cy - 8} width={56} height={16} rx={8}
                          fill={isSel ? "rgba(0,229,255,.12)" : "rgba(11,13,20,.75)"}
                          stroke={isSel ? T.cyan : z.rCol + "44"} strokeWidth={0.8} />
                        <text x={z.cx} y={z.cy + 4} textAnchor="middle" style={{
                          fontSize: isSel ? 9.5 : 8.5, fontFamily: "'JetBrains Mono',monospace",
                          fontWeight: 700, fill: isSel ? T.cyan : z.rCol, pointerEvents: "none",
                        }}>
                          {z.name.split(" ")[0]}
                        </text>
                      </g>
                    )}

                    {/* Load % badge (full city view only) */}
                    {!selected && !isFaded && (
                      <g>
                        <circle cx={z.cx + 18} cy={z.cy - 14} r={10} fill={z.rCol + "22"} stroke={z.rCol} strokeWidth={0.8} />
                        <text x={z.cx + 18} y={z.cy - 10} textAnchor="middle" style={{
                          fontSize: 6.5, fontFamily: "'JetBrains Mono',monospace", fontWeight: 700, fill: z.rCol,
                        }}>
                          {z.load}%
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* Demand nodes */}
              {ZONES.map(z => {
                const isSel = selected === z.id;
                const isFaded = !!selected && !isSel;
                if (isFaded) return null;
                const nodes = isSel ? z.nodes : z.nodes.slice(0, 2);
                return (
                  <g key={`nd-${z.id}`} opacity={isSel ? 1 : 0.75}>
                    {nodes.map((n, i) => <DemandNode key={i} {...n} zoomed={isSel} />)}
                  </g>
                );
              })}

              {/* Compass rose */}
              {!selected && (
                <g transform="translate(355,198)" opacity={0.4}>
                  <circle cx={0} cy={0} r={12} fill="none" stroke={T.cyan} strokeWidth={0.5} />
                  <line x1={0} y1={-12} x2={0} y2={12} stroke={T.sub} strokeWidth={0.5} />
                  <line x1={-12} y1={0} x2={12} y2={0} stroke={T.sub} strokeWidth={0.5} />
                  <text x={0} y={-14} textAnchor="middle" style={{ fontSize: 6, fill: T.sub, fontFamily: "'JetBrains Mono',monospace" }}>N</text>
                </g>
              )}

              {/* City label */}
              {!selected && (
                <text x={420} y={175} textAnchor="middle" style={{ fontSize: 8, fill: T.dim, fontFamily: "'JetBrains Mono',monospace", letterSpacing: "0.14em" }}>
                  BENGALURU · BESCOM DISTRIBUTION ZONE
                </text>
              )}

              {/* Zoom bounding box overlay */}
              {selected && selZone && (
                <rect
                  x={selZone.vbZoom[0] + 2} y={selZone.vbZoom[1] + 2}
                  width={selZone.vbZoom[2] - 4} height={selZone.vbZoom[3] - 4}
                  fill="none" stroke={T.cyan} strokeWidth={0.5}
                  strokeDasharray="4 4" rx={2} opacity={0.5}
                />
              )}
            </svg>

            {/* Hover tooltip */}
            {hovZone && !selected && (
              <div style={{
                position: "absolute", top: 80, left: 24,
                background: T.card2, border: `1px solid ${hovZone.rCol}55`,
                borderRadius: 10, padding: "10px 14px", pointerEvents: "none",
                boxShadow: "0 4px 20px rgba(0,0,0,.4)",
              }}>
                <div style={{ color: hovZone.rCol, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", fontWeight: 800, marginBottom: 4 }}>
                  {hovZone.zoneId} · {hovZone.risk}
                </div>
                <div style={{ color: T.text, fontSize: 14, fontWeight: 700, marginBottom: 6 }}>{hovZone.name}</div>
                <div style={{ display: "flex", gap: 12 }}>
                  <div>
                    <div style={{ color: hovZone.rCol, fontSize: 20, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace" }}>{hovZone.load}%</div>
                    <div style={{ color: T.sub, fontSize: 9 }}>Load</div>
                  </div>
                  <div>
                    <div style={{ color: T.teal, fontSize: 20, fontWeight: 800, fontFamily: "'JetBrains Mono',monospace" }}>{hovZone.headroom}%</div>
                    <div style={{ color: T.sub, fontSize: 9 }}>Headroom</div>
                  </div>
                </div>
                <div style={{ marginTop: 8, color: T.sub, fontSize: 10, fontStyle: "italic" }}>Click to zoom in →</div>
              </div>
            )}
          </div>

          {/* Stats Panel — slides in on zone select */}
          {selZone && (
            <div style={{ padding: "14px 14px 14px 0", display: "flex", alignItems: "flex-start", flexShrink: 0 }}>
              <StatsPanel zone={selZone} onClose={() => handleSelect(selected!)} />
            </div>
          )}
        </div>

        {/* ── Legend + Live Ticker ──────────────────────────────────────────── */}
        <div style={{
          background: T.card, borderTop: `1px solid ${T.border}`,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 20px", height: 38, flexShrink: 0,
        }}>
          <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
            {[
              { col: T.danger, label: "Peak demand (>80%)" },
              { col: T.warn, label: "High demand (60–80%)" },
              { col: T.primary, label: "Optimized (<60%)" },
              { col: T.cyan, label: "Selected zone perimeter" },
            ].map(l => (
              <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: l.col, boxShadow: `0 0 5px ${l.col}` }} />
                <span style={{ color: T.sub, fontSize: 10 }}>{l.label}</span>
              </div>
            ))}
          </div>

          {/* Ticker */}
          <div style={{ overflow: "hidden", width: 300, flexShrink: 0 }}>
            <div style={{ display: "flex", gap: 32, animation: "hmTickerMove 14s linear infinite", width: "max-content" }}>
              {[...Array(2)].flatMap(() =>
                ["Z7 Load 92% CRITICAL", "VPP 340kWh shifted", "Z3 Peak risk HIGH", "Site #1 Score 94", "0 violations", "MAPE 9.4%"]
              ).map((t, i) => (
                <span key={i} style={{ color: T.dim, fontSize: 9, fontFamily: "'JetBrains Mono',monospace", whiteSpace: "nowrap" }}>
                  <span style={{ color: T.primary, marginRight: 6 }}>◆</span>{t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}