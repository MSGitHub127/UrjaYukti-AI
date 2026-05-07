"use client";

export default function Legend() {
  const legendItems = [
    { col: "#F43F5E", label: "Peak demand node (>80%)" },
    { col: "#F59E0B", label: "High demand (60–80%)" },
    { col: "#02C39A", label: "Optimized (<60%)" },
    { col: "#00E5FF", label: "Selected zone perimeter" },
  ];

  const tickerItems = [
    "Z7 Load 92% CRITICAL",
    "VPP 340kWh shifted",
    "Z3 Peak risk HIGH",
    "Site #1 Score 94",
    "0 violations",
    "MAPE 9.4%",
  ];

  return (
    <div
      className="bg-card border-t border-border flex items-center justify-between px-5 h-9.5 flex-shrink-0"
    >
      {/* Legend Items */}
      <div className="flex gap-4.5 items-center">
        {legendItems.map((item) => (
          <div key={item.label} className="flex items-center gap-1">
            <div
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: item.col, boxShadow: `0 0 5px ${item.col}` }}
            />
            <span className="text-sub text-[10px]">{item.label}</span>
          </div>
        ))}
      </div>

      {/* Ticker */}
      <div className="overflow-hidden w-[300px] flex-shrink-0">
        <div
          className="flex gap-8 animate-ticker w-max"
          style={{ animationDuration: "14s" }}
        >
          {[...Array(2)].flatMap((_, outerIndex) =>
            tickerItems.map((t, innerIndex) => (
              <span
                key={`legend-${outerIndex}-${innerIndex}`}
                className="text-dim text-[9px] font-mono whitespace-nowrap"
              >
                <span className="text-primary mr-1.5">◆</span>
                {t}
              </span>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
