"use client";

import { useState, useEffect, useRef } from "react";
import { GlassCard, SectionLabel, Tag, Mono } from "@/components/ui/card";
import { COLORS } from "@/lib/mapLayers";

export default function AgentsView() {
  const [running, setRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [typedText, setTypedText] = useState("");
  const [showCursor, setShowCursor] = useState(true);

  const rationaleRef = useRef<string>(
    "Based on current MCDA weights and grid headroom analysis, Zone 7 Whitefield requires immediate VPP intervention. The demand forecast indicates a 385 MW peak at 20:00 under unmanaged EV charging, exceeding the N-1 limit by 85 MW. Recommended action: Apply 70% compliance rate schedule to shift 340 kWh to off-peak hours (00:00-04:00), achieving 18% PLI reduction with 0 constraint violations. Confidence: 84%."
  );

  const agentSteps = [
    { id: "forecast", label: "Demand Forecast Agent", status: "pending", icon: "📊" },
    { id: "vpp", label: "VPP Schedule Agent", status: "pending", icon: "⚡" },
    { id: "planning", label: "Site Planning Agent", status: "pending", icon: "📍" },
    { id: "mistral", label: "Mistral 7B", status: "pending", icon: "🤖" },
  ];

  const [steps, setSteps] = useState(agentSteps);

  // Typing animation effect
  useEffect(() => {
    if (currentStep === 3 && !completed) {
      let index = 0;
      const interval = setInterval(() => {
        if (index < rationaleRef.current.length) {
          setTypedText((prev) => prev + rationaleRef.current[index]);
          index++;
        } else {
          clearInterval(interval);
          setCompleted(true);
          setRunning(false);
        }
      }, 15);
      return () => clearInterval(interval);
    }
  }, [currentStep, completed]);

  // Cursor blink effect
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 500);
    return () => clearInterval(cursorInterval);
  }, []);

  const handleRun = () => {
    if (running || completed) return;
    setRunning(true);
    setCurrentStep(0);
    setTypedText("");
    setCompleted(false);

    // Simulate step-by-step execution
    const delays = [800, 1200, 1000, 0];
    let stepIndex = 0;

    const executeStep = () => {
      if (stepIndex < steps.length) {
        setSteps((prev) =>
          prev.map((s, i) =>
            i === stepIndex ? { ...s, status: "running" } : i < stepIndex ? { ...s, status: "completed" } : s
          )
        );
        setCurrentStep(stepIndex);

        setTimeout(() => {
          setSteps((prev) =>
            prev.map((s, i) =>
              i === stepIndex ? { ...s, status: "completed" } : s
            )
          );
          stepIndex++;
          if (stepIndex < steps.length) {
            executeStep();
          }
        }, delays[stepIndex]);
      }
    };

    executeStep();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return COLORS.success;
      case "running": return COLORS.warn;
      default: return COLORS.dim;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return "✓";
      case "running": return "⟳";
      default: return "○";
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Header Card */}
      <GlassCard style={{ padding: "16px 22px" }}>
        <div className="flex items-center gap-5 flex-wrap">
          <div>
            <div className="text-primary text-[9px] font-mono font-bold mb-1">AI AGENT PIPELINE · LANGGRAPH</div>
            <div className="text-text text-xs">
              Multi-agent orchestration for demand forecasting, VPP scheduling, and site planning with Mistral 7B reasoning
            </div>
          </div>
          <div className="ml-auto flex gap-2.5">
            <Tag text="LangGraph v0.2" color={COLORS.primary} />
            <Tag text="Mistral 7B" color={COLORS.purple} />
            <Tag text="Fallback Chain" color={COLORS.teal} />
          </div>
        </div>
      </GlassCard>

      {/* Main Content */}
      <div className="grid grid-cols-[1fr_1.2fr] gap-5">
        {/* Left Column - Agent Execution Graph */}
        <div className="flex flex-col gap-3.5">
          {/* Agent Steps */}
          <GlassCard style={{ padding: "20px" }}>
            <SectionLabel>Agent Execution Graph</SectionLabel>
            <div className="flex flex-col gap-3">
              {steps.map((step, idx) => (
                <div
                  key={step.id}
                  className="flex items-center gap-3 p-3 rounded-lg transition-all"
                  style={{
                    background: step.status === "running" ? `${COLORS.warn}0A` : step.status === "completed" ? `${COLORS.success}0A` : "",
                    border: `1px solid ${step.status === "running" ? COLORS.warn + "33" : step.status === "completed" ? COLORS.success + "33" : COLORS.border}`,
                  }}
                >
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                    style={{
                      background: step.status === "running" ? COLORS.warn + "18" : step.status === "completed" ? COLORS.success + "18" : COLORS.card2,
                      color: getStatusColor(step.status),
                    }}
                  >
                    {step.status === "running" ? (
                      <div className="spin w-4 h-4 rounded-full border-2 border-t-2" style={{ borderColor: "#F59E0B33", borderTopColor: "#F59E0B" }} />
                    ) : (
                      getStatusIcon(step.status)
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="text-text text-xs font-semibold">{step.label}</div>
                    <div className="text-dim text-[9px]">
                      {step.status === "running" ? "Processing..." : step.status === "completed" ? "Completed" : "Pending"}
                    </div>
                  </div>
                  <span className="text-lg">{step.icon}</span>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Configuration Cards */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { title: "LangGraph", desc: "Orchestrates multi-agent workflows with state management", color: COLORS.primary },
              { title: "Fallback Chain", desc: "Graceful degradation when primary model fails", color: COLORS.teal },
              { title: "Compliance", desc: "Ensures all recommendations meet N-1 constraints", color: COLORS.warn },
            ].map((cfg) => (
              <GlassCard key={cfg.title} style={{ padding: "14px" }}>
                <div className="text-sub text-[9px] font-mono mb-1">{cfg.title}</div>
                <div className="text-text text-[10px] leading-snug">{cfg.desc}</div>
              </GlassCard>
            ))}
          </div>

          {/* Run Button */}
          <GlassCard style={{ padding: "16px" }}>
            <button
              onClick={handleRun}
              disabled={running || completed}
              className="w-full py-3 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-all"
              style={{
                background: completed ? COLORS.success + "18" : running ? COLORS.warn + "18" : COLORS.primary + "18",
                border: `1px solid ${completed ? COLORS.success : running ? COLORS.warn : COLORS.primary}55`,
                color: completed ? COLORS.success : running ? COLORS.warn : COLORS.primary,
              }}
            >
              {running && (
                <div className="spin w-3 h-3 rounded-full border-2 border-t-2" style={{ borderColor: "#F59E0B33", borderTopColor: "#F59E0B" }} />
              )}
              {running ? "Running pipeline..." : completed ? "✓ Pipeline Complete" : "Run Agent Pipeline"}
            </button>
          </GlassCard>
        </div>

        {/* Right Column - Mistral 7B Output */}
        <GlassCard style={{ padding: "22px" }}>
          <SectionLabel color={COLORS.purple}>Mistral 7B — Agent Reasoning Output</SectionLabel>
          <div
            className="bg-card2 rounded-lg p-4 min-h-[280px] font-mono text-xs leading-relaxed"
            style={{
              border: `1px solid ${COLORS.border}`,
              color: COLORS.sub,
            }}
          >
            {typedText || (
              <span className="text-dim italic">
                {running && currentStep < 3
                  ? "Waiting for agent execution to complete..."
                  : "Click 'Run Agent Pipeline' to execute the multi-agent workflow and generate reasoning output."}
              </span>
            )}
            {currentStep === 3 && !completed && (
              <span
                className="inline-block w-2 h-4 ml-1"
                style={{
                  background: showCursor ? COLORS.primary : "transparent",
                  animation: showCursor ? "blink 1s step-end infinite" : "none",
                }}
              />
            )}
          </div>
          {completed && (
            <div className="mt-3 p-2.5 rounded-lg" style={{ background: "rgba(2,195,154,0.11)", border: "1px solid rgba(2,195,154,0.2)" }}>
              <div className="flex justify-between items-center">
                <div className="text-success text-[10px] font-bold">✓ Reasoning complete</div>
                <Tag text="Confidence: 84%" color={COLORS.success} />
              </div>
              <div className="text-sub text-[10px] mt-1">0 constraint violations · Auditable · Reproducible</div>
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
