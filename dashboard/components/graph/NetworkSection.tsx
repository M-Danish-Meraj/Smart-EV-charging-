"use client";

import { AnimatePresence, motion } from "framer-motion";
import { GitBranch, Network, Split, Trash2, Wrench } from "lucide-react";
import { useState } from "react";
import { Card, Stat } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { results, roadName, siteName } from "@/data/results";
import { COLOR, fmtMs } from "@/lib/format";
import { ComponentClusterView } from "./ComponentClusterView";
import { KruskalTrace } from "./KruskalTrace";
import { NetworkTopologyCanvas, RoadLegend } from "./NetworkTopologyCanvas";
import { type Scenario, scenarioView } from "./scenario";

const TABS: { id: Scenario; label: string; hint: string }[] = [
  { id: "e1", label: "E1 · Baseline", hint: "Kruskal on the available roads" },
  { id: "e2", label: "E2 · 3-road failure", hint: "Incremental repair after 3 failures" },
  { id: "e3", label: "E3 · Top-2 removed", hint: "Remove the two highest-severity sites" },
];

export function NetworkSection() {
  const [scenario, setScenario] = useState<Scenario>("e1");
  const view = scenarioView(scenario);
  const forestRoads = view.roads.filter((r) => r.status === "forest" || r.status === "replacement").length;

  return (
    <Card
      title="Road network and minimum spanning forest"
      subtitle="Part A (Greedy): Kruskal + Union-Find. Hover a site or road for details."
      icon={Network}
      action={<Tabs items={TABS} value={scenario} onChange={setScenario} layoutId="network-tab" />}
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-3">
          <NetworkTopologyCanvas scenario={scenario} />
          <RoadLegend />
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={scenario}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={{ duration: 0.2 }}
            className="min-w-0 space-y-4"
          >
            <div className="grid grid-cols-3 gap-2">
              <Stat label="Forest cost" value={view.cost} tone={COLOR.cyan} />
              <Stat label="Forest roads" value={forestRoads} />
              <Stat label="Components" value={view.components.length} />
            </div>
            {scenario === "e1" && <BaselineDetail />}
            {scenario === "e2" && <FailureDetail />}
            {scenario === "e3" && <RemovalDetail />}
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Connected components
              </h4>
              <ComponentClusterView components={view.components} />
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </Card>
  );
}

function BaselineDetail() {
  const { e1 } = results;
  return (
    <div className="space-y-2">
      <p className="text-xs leading-relaxed text-slate-400">
        {e1.dropped.length} unavailable roads are filtered <em>before</em> sorting (
        {e1.dropped.map((d) => d.road).join(", ")}). Ties in cost are broken by s(u)+s(v), then by
        site ID. Severity never changes the total cost.
      </p>
      <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <GitBranch className="h-3.5 w-3.5" aria-hidden /> Kruskal trace (sorted order)
      </h4>
      <KruskalTrace />
    </div>
  );
}

function FailureDetail() {
  const { e2 } = results;
  const icon = { replaced: Wrench, split: Split, not_in_forest: GitBranch };
  const tone = { replaced: COLOR.emerald, split: COLOR.red, not_in_forest: COLOR.muted };
  const text = {
    replaced: (r: string | null) => `replaced by ${r} (${r ? roadName(r) : ""})`,
    split: () => "no road crosses the cut: component splits",
    not_in_forest: () => "not in the forest: nothing to repair",
  };
  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {e2.failed.map((f) => {
          const Icon = icon[f.action];
          return (
            <li key={f.road} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs">
              <div className="flex items-center gap-2 font-mono text-slate-200">
                <Icon className="h-3.5 w-3.5" style={{ color: tone[f.action] }} aria-hidden />
                {f.road} <span className="text-slate-500">{roadName(f.road)}</span>
              </div>
              <p className="mt-1 text-slate-400" style={{ color: tone[f.action] }}>
                {text[f.action](f.replacement)}
              </p>
            </li>
          );
        })}
      </ul>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Repair cost" value={e2.repair_cost} tone={COLOR.emerald} />
        <Stat label="Full Kruskal cost" value={e2.full_cost} />
        <Stat label="Repair time" value={fmtMs(e2.runtime_ms.repair)} />
        <Stat label="Full Kruskal time" value={fmtMs(e2.runtime_ms.full)} />
      </div>
      <p className="text-xs text-slate-400">
        Cost before failures: <span className="font-mono text-slate-200">{e2.cost_before}</span>.
        Repair {e2.repair_cost === e2.full_cost ? "matches" : "DOES NOT match"} full Kruskal on the same
        modified graph. On 12 sites both run in microseconds; E5 measures larger graphs.
      </p>
    </div>
  );
}

function RemovalDetail() {
  const { e1, e3 } = results;
  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs">
        <div className="flex items-center gap-2 font-mono text-slate-200">
          <Trash2 className="h-3.5 w-3.5 text-red-400" aria-hidden />
          Removed: {e3.removed_sites.map(siteName).join(", ")}
        </div>
        <p className="mt-1 text-slate-400">
          {e3.removed_roads.length} incident roads dropped; station
          {e3.deactivated_stations.length > 1 ? "s" : ""} {e3.deactivated_stations.join(", ")} deactivated.
          Both stages rerun.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Cost E1 → E3" value={`${e1.cost} → ${e3.cost}`} />
        <Stat
          label="Capacity (units)"
          value={`${e1.allocation.capacity} → ${e3.allocation.capacity}`}
          tone={COLOR.amber}
        />
        <Stat label="Served" value={`${e1.allocation.served} → ${e3.allocation.served}`} />
        <Stat label="Benefit" value={`${e1.allocation.benefit} → ${e3.allocation.benefit}`} />
      </div>
      <p className="text-xs text-slate-400">
        Severity is only a tie-break, so Kruskal does not maximise severity coverage. These are model
        outputs only, not a safety claim.
      </p>
    </div>
  );
}
