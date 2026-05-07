"use client";
import { useState, useEffect } from "react";
import { COLORS } from "@/lib/mapLayers";
import { GlassCard } from "./GlassCard";

interface KPICardProps {
  label: string;
  value: string | number;
  sub: string;
  color?: string;
  trend?: string;
  icon?: string;
  delay?: number;
}

export function KPICard({
  label,
  value,
  sub,
  color = COLORS.primary,
  trend,
  icon,
  delay = 0,
}: KPICardProps) {
  const [displayed, setDisplayed] = useState(0);
  const numeric = parseFloat(String(value).replace(/[^0-9.]/g, ""));
  const suffix = String(value).replace(/[0-9.]/g, "");

  useEffect(() => {
    const timer = setTimeout(() => {
      const dur = 1200;
      const start = performance.now();
      const tick = (now: number) => {
        const p = Math.min((now - start) / dur, 1);
        const ease = 1 - Math.pow(1 - p, 4);
        setDisplayed(Math.round(ease * numeric * 10) / 10);
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, delay);
    return () => clearTimeout(timer);
  }, [numeric, delay]);

  return (
    <GlassCard
      className="card-hover fade-up"
      style={{
        padding: "18px 20px",
        borderTop: `2px solid ${color}`,
        animationDelay: `${delay}ms`,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div style={{ color: COLORS.sub, fontSize: 10, letterSpacing: "0.05em" }}>{label}</div>
        {icon && <div style={{ fontSize: 16 }}>{icon}</div>}
      </div>
      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: 32,
          fontWeight: 800,
          color,
          lineHeight: 1,
          marginBottom: 6,
        }}
      >
        {displayed}{suffix}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ color: COLORS.sub, fontSize: 11 }}>{sub}</div>
        {trend && (
          <span
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: 10,
              color: trend.startsWith("+") ? COLORS.success : COLORS.danger,
              fontWeight: 700,
            }}
          >
            {trend}
          </span>
        )}
      </div>
    </GlassCard>
  );
}
