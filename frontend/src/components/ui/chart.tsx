import { COLORS } from "@/lib/mapLayers";

interface ChartTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

export default function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div
      className="rounded-lg p-2 text-xs"
      style={{
        background: COLORS.card2,
        border: `1px solid ${COLORS.border}`,
        color: COLORS.text,
      }}
    >
      {label && (
        <div className="font-mono mb-1" style={{ color: COLORS.sub }}>
          {label}
        </div>
      )}
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: entry.color }}
          />
          <span className="text-sub">{entry.name}:</span>
          <span className="font-mono font-semibold">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}
