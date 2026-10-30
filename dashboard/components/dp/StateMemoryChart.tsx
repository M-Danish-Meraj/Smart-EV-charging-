"use client";

import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { results } from "@/data/results";
import { COLOR, fmtBytes, fmtInt, fmtMs } from "@/lib/format";
import { ChartTooltip, axisProps } from "@/components/benchmarks/chartTheme";

/** DP table memory vs capacity factor (q = 24, k = 3): pseudo-polynomial growth. Log scale. */
export function StateMemoryChart() {
  const data = results.e5.capacity.map((r) => ({
    label: `${r.factor}×`,
    bytes: r.table_bytes,
    states: r.states_per_layer,
    ms: r.dp_ms,
    caps: r.capacities.join(", "),
  }));
  // log axis needs a positive floor: whole decades around the data
  const lo = 10 ** Math.floor(Math.log10(Math.min(...data.map((d) => d.bytes))));
  const hi = 10 ** Math.ceil(Math.log10(Math.max(...data.map((d) => d.bytes))));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 24, right: 8, bottom: 4, left: 8 }}>
          <CartesianGrid stroke={COLOR.grid} vertical={false} />
          <XAxis dataKey="label" {...axisProps} />
          <YAxis
            scale="log"
            domain={[lo, hi]}
            allowDataOverflow
            tickFormatter={(v: number) => fmtBytes(v)}
            width={64}
            {...axisProps}
          />
          <Tooltip
            cursor={{ fill: "rgba(148,163,184,0.08)" }}
            content={
              <ChartTooltip
                render={(p: (typeof data)[number]) => [
                  `capacity ×${p.label.replace("×", "")}: [${p.caps}]`,
                  `S = ${fmtInt(p.states)} states / layer`,
                  `memory ${fmtBytes(p.bytes)}`,
                  `DP time ${fmtMs(p.ms)}`,
                ]}
              />
            }
          />
          <Bar dataKey="bytes" fill={COLOR.cyan} radius={[4, 4, 0, 0]} maxBarSize={56}>
            <LabelList
              dataKey="bytes"
              position="top"
              formatter={(v: unknown) => fmtBytes(Number(v))}
              className="fill-slate-300 font-mono text-[11px]"
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
