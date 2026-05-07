import { COLORS } from "@/lib/mapLayers";
import { ReactNode } from "react";

interface SectionLabelProps {
  children: ReactNode;
  color?: string;
}

export function SectionLabel({ children, color = COLORS.primary }: SectionLabelProps) {
  return (
    <div
      style={{
        color,
        fontSize: 9,
        fontFamily: "var(--font-mono), 'JetBrains Mono', monospace",
        fontWeight: 800,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        marginBottom: 14,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <div style={{ width: 14, height: 1, background: color }} />
      {children}
      <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg,${color}44,transparent)` }} />
    </div>
  );
}
