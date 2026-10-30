"use client";

import { BatteryCharging, Cpu, Info } from "lucide-react";
import { useState } from "react";
import { Card, Stat } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { results, siteName, station } from "@/data/results";
import { COLOR, fmtBytes, fmtInt, fmtMs, pct } from "@/lib/format";
import { AllocationTable } from "./AllocationTable";
import { StationLoadBar } from "./StationLoadBar";

type Mode = "k3" | "k4";

export function AllocationSection() {
  const [mode, setMode] = useState<Mode>("k3");
  const { e1 } = results;
  const base = e1.allocation;
  const alloc = mode === "k3" ? base : e1.stress.allocation;
  const runtime = mode === "k3" ? e1.runtime_ms.allocation : e1.stress.runtime_ms;
  const k = Object.keys(alloc.loads).length;
  const stressSite = siteName(station(e1.stress.station).site);

  return (
    <Card
      title="Energy allocation: exact multi-knapsack DP"
      subtitle="Part B (Dynamic Programming). Each request goes to at most one eligible station or is skipped."
      icon={BatteryCharging}
      action={
        <Tabs
          items={[
            { id: "k3", label: "k = 3 stations" },
            { id: "k4", label: `Stress k = 4 (+${e1.stress.station})` },
          ]}
          value={mode}
          onChange={setMode}
          layoutId="alloc-tab"
        />
      }
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="min-w-0 space-y-3">
          {Object.entries(alloc.loads).map(([id, l]) => (
            <StationLoadBar key={`${mode}-${id}`} id={id} load={l.load} capacity={l.capacity} />
          ))}

          <div className="grid grid-cols-2 gap-2">
            <Stat label="Served" value={`${alloc.served} / ${alloc.requests_total}`} tone={COLOR.emerald} />
            <Stat label="Total benefit" value={fmtInt(alloc.benefit)} tone={COLOR.cyan} />
            <Stat label="Energy" value={`${alloc.units} units`} />
            <Stat label="Capacity used" value={pct(alloc.units, alloc.capacity)} tone={COLOR.amber} />
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
            <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Cpu className="h-3.5 w-3.5" aria-hidden /> DP state space
            </h4>
            <dl className="grid grid-cols-2 gap-y-1 font-mono text-[11px]">
              <dt className="text-slate-500">S = ∏(C_j+1)</dt>
              <dd className="text-right text-slate-200">{fmtInt(alloc.dp.states_per_layer)}</dd>
              <dt className="text-slate-500">(q+1)·S states</dt>
              <dd className="text-right text-slate-200">{fmtInt(alloc.dp.total_states)}</dd>
              <dt className="text-slate-500">table memory</dt>
              <dd className="text-right text-slate-200">{fmtBytes(alloc.dp.table_bytes)}</dd>
              <dt className="text-slate-500">runtime (median)</dt>
              <dd className="text-right text-slate-200">{fmtMs(runtime)}</dd>
              <dt className="text-slate-500">k stations</dt>
              <dd className="text-right text-slate-200">{k}</dd>
            </dl>
          </div>

          {mode === "k4" && (
            <p className="flex gap-2 rounded-xl border border-cyan-neon/30 bg-cyan-neon/5 p-3 text-xs text-slate-300">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan-neon" aria-hidden />
              Activating {e1.stress.station} at {stressSite} raises served requests {base.served} →{" "}
              {alloc.served} and benefit {base.benefit} → {alloc.benefit}, while the state count grows{" "}
              {fmtInt(base.dp.states_per_layer)} → {fmtInt(alloc.dp.states_per_layer)} per layer.
            </p>
          )}
        </div>

        <AllocationTable key={mode} requests={alloc.requests} />
      </div>
    </Card>
  );
}
