import { COLORS } from "@/lib/mapLayers";
import { ReactNode } from "react";

interface MonoProps {
  children: ReactNode;
  color?: string;
  size?: number;
}

export function Mono({ children, color = COLORS.primary, size = 13 }: MonoProps) {
  return (
    <span
      style={{
        fontFamily: "var(--font-mono), 'JetBrains Mono', monospace",
        fontWeight: 700,
        color,
        fontSize: size,
      }}
    >
      {children}
    </span>
  );
}
