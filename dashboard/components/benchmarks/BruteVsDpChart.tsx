"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { results } from "@/data/results";
import { COLOR, fmtInt, fmtMs } from "@/lib/format";
import { ChartTooltip, LegendDot, axisProps } from "./chartTheme";

/** Brute force (k+1)^q blow-up vs the DP, log scale. */
export function BruteVsDpChart() {
  const data = results.e5.brute.map((r) => ({ ...r, label: String(r.q) }));
  const all = data.flatMap((d) => [d.brute_ms, d.dp_ms]);
  const lo = 10 ** Math.floor(Math.log10(Math.min(...all)));
  const hi = 10 ** Math.ceil(Math.log10(Math.max(...all)));
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-4">
        <LegendDot color={COLOR.red} label="Brute force" />
        <LegendDot color={COLOR.cyan} label="Exact DP" />
      </div>
      <div className="h-56 w-full">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 8 }}>
            <CartesianGrid stroke={COLOR.grid} vertical={false} />
            <XAxis dataKey="label" {...axisProps} label={{ value: "q requests", position: "insideBottomRight", offset: -2, fill: COLOR.muted, fontSize: 10 }} />
            <YAxis scale="log" domain={[lo, hi]} allowDataOverflow tickFormatter={(v: number) => fmtMs(v)} width={72} {...axisProps} />
            <Tooltip
              cursor={{ stroke: "#475569" }}
              content={
                <ChartTooltip
                  render={(p: (typeof data)[number]) => [
                    `q = ${p.q}, k = 3`,
                    `brute force ${fmtMs(p.brute_ms)} (${fmtInt(p.checked)} checks)`,
                    `DP ${fmtMs(p.dp_ms)}`,
                  ]}
                />
              }
            />
            <Line dataKey="brute_ms" stroke={COLOR.red} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
            <Line dataKey="dp_ms" stroke={COLOR.cyan} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
