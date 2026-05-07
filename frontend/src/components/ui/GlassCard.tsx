import { COLORS } from "@/lib/mapLayers";
import { CSSProperties, ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  style?: CSSProperties;
  glow?: boolean;
  glowColor?: string;
  className?: string;
}

export function GlassCard({
  children,
  style = {},
  glow = false,
  glowColor = COLORS.primary,
  className = "",
}: GlassCardProps) {
  return (
    <div
      className={className}
      style={{
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        border: `1px solid ${glow ? glowColor + "44" : COLORS.border}`,
        borderRadius: 14,
        boxShadow: glow
          ? `0 0 30px ${glowColor}18, 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)`
          : `0 4px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
