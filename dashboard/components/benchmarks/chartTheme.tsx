import { COLOR } from "@/lib/format";

/** Shared, recessive axis styling for every Recharts chart. */
export const axisProps = {
  stroke: COLOR.grid,
  tick: { fill: COLOR.muted, fontSize: 11, fontFamily: "var(--font-jetbrains)" },
  tickLine: false,
  axisLine: { stroke: "#334155" },
};

/** Dark tooltip; `render` turns the hovered row into text lines (first line = title). */
export function ChartTooltip<T>({
  active,
  payload,
  render,
}: {
  active?: boolean;
  payload?: { payload: T }[];
  render: (row: T) => string[];
}) {
  if (!active || !payload?.length) return null;
  const lines = render(payload[0].payload);
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-xl">
      {lines.map((l, i) => (
        <div key={i} className={i === 0 ? "font-semibold text-slate-100" : "font-mono text-slate-400"}>
          {l}
        </div>
      ))}
    </div>
  );
}

export function LegendDot({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-slate-400">
      <svg width="18" height="8" aria-hidden>
        <line x1="1" y1="4" x2="17" y2="4" stroke={color} strokeWidth="2.5" strokeDasharray={dashed ? "4 3" : undefined} strokeLinecap="round" />
      </svg>
      {label}
    </span>
  );
}
