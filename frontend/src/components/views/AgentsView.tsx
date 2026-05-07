"use client";

import { useState, useEffect, useRef } from "react";
import { GlassCard, SectionLabel, Tag } from "@/components/ui/card";
import { COLORS } from "@/lib/mapLayers";

/* ─── Sub-Component: AgentRow (Refactored from Claude's logic) ─── */
interface AgentRowProps {
  label: string;
  icon: string;
  tech: string;
  desc: string;
  status: "pending" | "running" | "completed";
}

function AgentRow({ label, icon, tech, desc, status }: AgentRowProps) {
  const isActive = status === "running";
  const isDone = status === "completed";
  const col = isActive ? COLORS.warn : isDone ? COLORS.success : COLORS.dim;

  return (
    <div
      className={`p-4 rounded-xl border transition-all duration-500 ${isActive ? 'scale-[1.02] shadow-[0_0_20px_rgba(245,158,11,0.1)]' : ''}`}
      style={{
        background: isActive ? `${COLORS.warn}0A` : isDone ? `${COLORS.success}05` : "rgba(255,255,255,0.02)",
        borderColor: isActive ? `${COLORS.warn}66` : isDone ? `${COLORS.success}33` : "rgba(255,255,255,0.05)",
      }}
    >
      <div className="grid grid-cols-[48px_1fr_auto_50px] gap-4 items-center">
        {/* Icon / Status Circle */}
        <div className="relative w-10 h-10 rounded-full flex items-center justify-center text-lg bg-card2 border-2"
          style={{ borderColor: isActive || isDone ? col : "rgba(255,255,255,0.1)" }}>
          {isActive && <div className="absolute inset-0 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: col }} />}
          {isDone ? <span style={{ color: col }}>✓</span> : <span>{icon}</span>}
        </div>

        {/* Info */}
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-text font-bold text-sm tracking-tight">{label}</span>
            <Tag text={tech} color={col} />
          </div>
          <div className="text-[10px] font-mono text-sub truncate">
            {isActive ? desc : isDone ? "Execution successful — context updated" : "Waiting for upstream agent..."}
          </div>
        </div>

        {/* Status Badge */}
        <Tag
          text={isActive ? "RUNNING" : isDone ? "DONE" : "QUEUED"}
          color={col}
        />

        {/* Time */}
        <div className="text-right font-mono text-[10px] text-dim">
          {isDone ? "~1.2s" : isActive ? "..." : "--"}
        </div>
      </div>
    </div>
  );
}

/* ─── Main View Component ─── */
export default function AgentsView() {
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState(-1);
  const [done, setDone] = useState(false);
  const [typedText, setTypedText] = useState("");

  const rationale = "Zone 7 (Whitefield) analysis complete. Shifting 340 kWh of EV charging load from the 18:00–22:00 peak window to the 00:00–04:00 off-peak window is projected to reduce transformer T-07 peak stress by 18.3%, with 84% confidence. This recommendation is fully compliant with BESCOM N-1 contingency safety standards. Zero constraint violations detected.";

  const steps = [
    { id: "f", label: "Demand Forecast Agent", tech: "TFT • PyTorch", icon: "📊", desc: "Fetching 72-hr zone predictions..." },
    { id: "v", label: "VPP Schedule Agent", tech: "OR-Tools LP", icon: "⚡", desc: "Solving N-1 load constraints..." },
    { id: "p", label: "Site Planning Agent", tech: "MCDA Engine", icon: "◎", desc: "Scoring candidate locations..." },
    { id: "m", label: "Mistral 7B (VPC)", tech: "RAG + ChromaDB", icon: "✦", desc: "Synthesizing rationale..." },
  ];

  const handleRun = () => {
    if (running) return;
    setRunning(true);
    setStep(0);
    setDone(false);
    setTypedText("");

    // Step progression logic
    steps.forEach((_, i) => {
      setTimeout(() => setStep(i), i * 1600);
    });

    // Completion and typewriter start
    setTimeout(() => {
      setDone(true);
      setRunning(false);
      let i = 0;
      const tick = setInterval(() => {
        setTypedText(rationale.slice(0, i));
        i += 3;
        if (i > rationale.length) {
          setTypedText(rationale);
          clearInterval(tick);
        }
      }, 15);
    }, steps.length * 1600);
  };

  return (
    <div className="flex flex-col gap-6">

      {/* 1. Header with Run Button */}
      <GlassCard className="p-6">
        <div className="flex justify-between items-center">
          <div>
            <div className="text-primary text-[10px] font-mono font-bold uppercase tracking-[0.2em] mb-1">
              LangGraph Agentic Pipeline · Cyclic Reasoning
            </div>
            <h1 className="text-3xl font-black text-white tracking-tight font-display">Multi-Agent Reasoning Console</h1>
          </div>
          <button
            onClick={handleRun}
            disabled={running}
            className={`px-8 py-3 rounded-xl border font-bold transition-all ${running ? 'opacity-50' : 'hover:scale-105 active:scale-95'}`}
            style={{
              background: running ? 'rgba(255,255,255,0.05)' : `${COLORS.primary}18`,
              borderColor: running ? "rgba(255,255,255,0.1)" : `${COLORS.primary}55`,
              color: running ? COLORS.sub : COLORS.primary
            }}
          >
            {running ? "Pipeline Running..." : "▶ Run Agent Pipeline"}
          </button>
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-6">

        {/* 2. Execution Graph */}
        <div className="flex flex-col gap-3">
          <SectionLabel>Agent Execution Graph</SectionLabel>
          {steps.map((s, i) => (
            <AgentRow
              key={s.id}
              {...s}
              status={done ? "completed" : running && step === i ? "running" : running && step > i ? "completed" : "pending"}
            />
          ))}
        </div>

        {/* 3. Reasoning Output */}
        <div className="flex flex-col gap-3">
          <SectionLabel color={COLORS.purple}>Mistral 7B — Agent Reasoning Output</SectionLabel>
          <GlassCard className="flex-1 p-0 overflow-hidden flex flex-col">
            <div className="p-3 bg-white/[0.03] border-b border-white/5 flex gap-2">
              <Tag text="✦ PLAIN-LANGUAGE BRIEFING" color={COLORS.primary} />
              <Tag text="PRIVATE VPC" color={COLORS.purple} />
            </div>
            <div className="p-6 flex-1 font-mono text-[13px] leading-relaxed italic text-text/80">
              {typedText || <span className="text-dim opacity-40">Awaiting execution pipeline...</span>}
              {!done && running && step === 3 && <span className="animate-pulse text-primary ml-1">|</span>}
            </div>
            {done && (
              <div className="p-4 bg-black/20 border-t border-white/5 flex flex-wrap gap-2">
                <Tag text="Confidence: 84%" color={COLORS.success} dot />
                <Tag text="0 Violations" color={COLORS.success} />
                <Tag text="RAG-Enhanced" color={COLORS.purple} />
                <Tag text="N-1 Compliant" color={COLORS.primary} />
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* 4. Bottom Architecture Panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { t: "LangGraph Configuration", i: ["Cyclic reasoning graph", "Max 3 revision cycles", "Cross-agent validation"] },
          { t: "Fallback Chain", i: ["Tier 1: Full AI pipeline", "Tier 2: Template rationale", "Tier 3: Static defaults"] },
          { t: "Compliance", i: ["Mistral 7B · Private VPC", "Masked data transmission", "Full audit trail logged"] },
        ].map(card => (
          <GlassCard key={card.t} className="p-5">
            <div className="text-primary text-[10px] font-mono font-black uppercase mb-3">{card.t}</div>
            <ul className="space-y-2">
              {card.i.map(item => (
                <li key={item} className="text-[11px] text-sub flex items-center gap-2 border-b border-white/5 pb-2 last:border-0">
                  <div className="w-1 h-1 rounded-full bg-primary" /> {item}
                </li>
              ))}
            </ul>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}