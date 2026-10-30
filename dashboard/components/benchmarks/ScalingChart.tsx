"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { results } from "@/data/results";
import { COLOR, fmtMs } from "@/lib/format";
import { ChartTooltip, LegendDot, axisProps } from "./chartTheme";

/** E5 network: median runtime of full Kruskal vs incremental repair, log scale. */
export function ScalingChart() {
  const data = results.e5.network.map((r) => ({ ...r, label: String(r.n) }));
  const all = data.flatMap((d) => [d.kruskal_ms, d.repair_ms, d.full_ms]);
  const lo = 10 ** Math.floor(Math.log10(Math.min(...all)));
  const hi = 10 ** Math.ceil(Math.log10(Math.max(...all)));
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-4">
        <LegendDot color={COLOR.cyan} label="Full Kruskal (after failures)" />
        <LegendDot color={COLOR.emerald} label="Incremental repair (3 failures)" />
        <LegendDot color={COLOR.muted} label="Kruskal on original graph" dashed />
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 8 }}>
            <CartesianGrid stroke={COLOR.grid} vertical={false} />
            <XAxis dataKey="label" {...axisProps} label={{ value: "n sites", position: "insideBottomRight", offset: -2, fill: COLOR.muted, fontSize: 10 }} />
            <YAxis scale="log" domain={[lo, hi]} allowDataOverflow tickFormatter={(v: number) => `${v} ms`} width={64} {...axisProps} />
            <Tooltip
              cursor={{ stroke: "#475569" }}
              content={
                <ChartTooltip
                  render={(p: (typeof data)[number]) => [
                    `n = ${p.n} sites, m = ${p.m} active roads`,
                    `full Kruskal ${fmtMs(p.full_ms)}`,
                    `repair ${fmtMs(p.repair_ms)} (${(p.repair_ms / p.full_ms).toFixed(2)}× full)`,
                    `original Kruskal ${fmtMs(p.kruskal_ms)}`,
                    p.costs_equal ? "costs equal ✓" : "COSTS DIFFER",
                  ]}
                />
              }
            />
            <Line dataKey="kruskal_ms" stroke={COLOR.muted} strokeDasharray="5 4" strokeWidth={2} dot={{ r: 3 }} />
            <Line dataKey="full_ms" stroke={COLOR.cyan} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
            <Line dataKey="repair_ms" stroke={COLOR.emerald} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
