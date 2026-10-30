"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { results } from "@/data/results";
import { COLOR, pct } from "@/lib/format";
import { ChartTooltip, axisProps } from "./chartTheme";

/** E4: benefit per scenario (one measure, one axis). Served count is in the label and table. */
export function SensitivityChart() {
  const data = results.e4.scenarios.map((s) => ({
    ...s,
    short: s.label.split(" ")[0],
    used: pct(s.units, s.capacity),
  }));
  const base = data[0]?.benefit ?? 0;
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 28, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={COLOR.grid} vertical={false} />
          <XAxis dataKey="short" {...axisProps} />
          <YAxis width={44} {...axisProps} />
          <Tooltip
            cursor={{ fill: "rgba(148,163,184,0.08)" }}
            content={
              <ChartTooltip
                render={(p: (typeof data)[number]) => [
                  p.label,
                  `benefit ${p.benefit} (${p.benefit >= base ? "+" : ""}${p.benefit - base} vs E1)`,
                  `served ${p.served} of ${p.requests}`,
                  `energy ${p.units}/${p.capacity} units (${p.used})`,
                ]}
              />
            }
          />
          <Bar dataKey="benefit" radius={[4, 4, 0, 0]} maxBarSize={64}>
            {data.map((d, i) => (
              <Cell key={d.label} fill={i === 0 ? COLOR.cyan : d.benefit < base ? COLOR.amber : COLOR.emerald} />
            ))}
            <LabelList
              dataKey="benefit"
              position="top"
              className="fill-slate-200 font-mono text-[11px]"
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
