"use client";

import { motion } from "framer-motion";
import {
  BatteryCharging,
  Coins,
  Cpu,
  FlaskConical,
  Gauge,
  MapPin,
  Network,
  PlugZap,
  Route,
  ShieldCheck,
  SlidersHorizontal,
  Timer,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";
import { BruteVsDpChart } from "@/components/benchmarks/BruteVsDpChart";
import { DpScalingTable } from "@/components/benchmarks/DpScalingTable";
import { BruteVsDpTable, KruskalVsRepairTable } from "@/components/benchmarks/KruskalVsRepairTable";
import { ScalingChart } from "@/components/benchmarks/ScalingChart";
import { SensitivityChart } from "@/components/benchmarks/SensitivityChart";
import { SensitivityTable } from "@/components/benchmarks/SensitivityTable";
import { AllocationSection } from "@/components/dp/AllocationSection";
import { StateMemoryChart } from "@/components/dp/StateMemoryChart";
import { EdgeCasesPanel } from "@/components/edge/EdgeCasesPanel";
import { NetworkSection } from "@/components/graph/NetworkSection";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/ui/Card";
import { KpiCard } from "@/components/ui/KpiCard";
import { Modal } from "@/components/ui/Modal";
import { results } from "@/data/results";
import { COLOR, fmtMs, pct } from "@/lib/format";

function Section({ id, title, eyebrow, children }: { id: string; title: string; eyebrow: string; children: React.ReactNode }) {
  return (
    <motion.section
      id={id}
      className="scroll-mt-20 space-y-4"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.4 }}
    >
      <div>
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-cyan-neon/80">{eyebrow}</div>
        <h2 className="mt-1 text-xl font-semibold text-slate-50">{title}</h2>
      </div>
      {children}
    </motion.section>
  );
}

export default function Dashboard() {
  const [edgeOpen, setEdgeOpen] = useState(false);
  const { e1, verification: ver } = results;
  const a = e1.allocation;
  const available = results.roads.filter((r) => r.available).length;
  const activeStations = results.stations.filter((s) => s.active).length;

  const kpis = [
    { label: "Sites", value: String(results.sites.length), detail: `${e1.components.length} components`, icon: MapPin, accent: COLOR.cyan },
    { label: "Roads", value: `${available} / ${results.roads.length}`, unit: "available", detail: `${results.roads.length - available} filtered`, icon: Route, accent: COLOR.cyan },
    { label: "Forest cost", value: String(e1.cost), detail: `${e1.forest.length} roads selected`, icon: Network, accent: COLOR.cyan },
    { label: "Active stations", value: String(activeStations), detail: `${a.capacity} units total capacity`, icon: PlugZap, accent: COLOR.amber },
    { label: "Requests served", value: `${a.served} / ${a.requests_total}`, detail: `${a.units}/${a.capacity} units · ${pct(a.units, a.capacity)} used`, icon: BatteryCharging, accent: COLOR.emerald },
    { label: "Total benefit", value: String(a.benefit), detail: `${a.kwh} kWh requested by served EVs`, icon: Coins, accent: COLOR.emerald },
    { label: "Kruskal runtime", value: fmtMs(e1.runtime_ms.kruskal).replace(" ms", ""), unit: "ms", detail: `median of ${results.meta.timing_runs} runs`, icon: Timer, accent: COLOR.cyan },
    { label: "DP allocation", value: fmtMs(e1.runtime_ms.allocation).replace(" ms", ""), unit: "ms", detail: `${a.dp.states_per_layer.toLocaleString("en-US")} states / layer`, icon: Cpu, accent: COLOR.cyan },
  ];

  return (
    <div className="grid-backdrop min-h-screen">
      <Sidebar onEdgeCases={() => setEdgeOpen(true)} />

      <main className="mx-auto max-w-[1400px] space-y-12 px-4 py-6 sm:px-6 lg:ml-60 lg:px-8 lg:py-8">
        {/* header */}
        <header id="overview" className="scroll-mt-20 space-y-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-cyan-neon/80">
                CT-363 Design &amp; Analysis of Algorithms · NED University
              </div>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
                Smart EV Charging: network planning &amp; energy allocation
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-400">
                Greedy Kruskal + Union-Find builds a minimum spanning forest. An exact multi-knapsack DP then
                assigns requests to stations in the same component. Dataset{" "}
                <span className="font-mono text-slate-300">{results.meta.dataset}</span> is{" "}
                <span className="text-amber-400">synthetic</span>; 1 unit = {results.meta.kwh_per_unit} kWh.
              </p>
            </div>
            <Button icon={ShieldCheck} variant="solid" onClick={() => setEdgeOpen(true)}>
              CEP edge cases
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {kpis.map((k, i) => (
              <KpiCard key={k.label} index={i} {...k} />
            ))}
          </div>
        </header>

        <Section id="network" eyebrow="Part A · Greedy" title="Spanning forest, failures and site removal">
          <NetworkSection />
        </Section>

        <Section id="allocation" eyebrow="Part B · Dynamic Programming" title="Request allocation and DP state space">
          <AllocationSection />
        </Section>

        <Section id="sensitivity" eyebrow="E4 · Sensitivity" title="Capacity cut and extra demand">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
            <Card title="Total benefit per scenario" subtitle="Cyan = baseline, amber = lower, emerald = higher" icon={SlidersHorizontal}>
              <SensitivityChart />
            </Card>
            <Card title="Scenario details" icon={TrendingUp}>
              <SensitivityTable />
            </Card>
          </div>
        </Section>

        <Section id="scaling" eyebrow="E5 · Scaling" title="Benchmarks on random synthetic instances">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="Incremental repair vs full Kruskal" subtitle="Median runtime, log scale. The repair is measured, not assumed faster." icon={Gauge}>
              <ScalingChart />
              <div className="mt-4">
                <KruskalVsRepairTable />
              </div>
            </Card>
            <Card title="DP memory vs capacity" subtitle="q = 24, k = 3. Pseudo-polynomial: S = ∏(C_j+1) grows with capacity. Log scale." icon={Cpu}>
              <StateMemoryChart />
              <div className="mt-4">
                <DpScalingTable />
              </div>
            </Card>
            <Card title="Exact DP vs brute force" subtitle="Brute force checks (k+1)^q assignments. Log scale." icon={FlaskConical}>
              <BruteVsDpChart />
              <div className="mt-4">
                <BruteVsDpTable />
              </div>
            </Card>
            <Card title="Verification and greedy baseline" icon={ShieldCheck}>
              <div className="grid grid-cols-2 gap-2">
                <Stat label="DP = brute force" value={`${ver.agree} / ${ver.instances}`} tone={ver.agree === ver.instances ? COLOR.emerald : COLOR.red} />
                <Stat label="Greedy on dataset" value={`${ver.greedy.dataset_greedy} vs ${ver.greedy.dataset_dp}`} tone={COLOR.amber} />
                <Stat label="Mean greedy gap" value={`${ver.greedy.mean_gap_pct.toFixed(1)}%`} />
                <Stat label="Max greedy gap" value={`${ver.greedy.max_gap_pct.toFixed(1)}%`} tone={COLOR.red} />
              </div>
              <p className="mt-3 text-xs leading-relaxed text-slate-400">
                The DP matched brute force on (benefit, requests served) for {ver.agree} of {ver.instances} random
                instances (q ≤ 9, k ≤ 3). The benefit-per-unit greedy was optimal in {ver.greedy.optimal_count} of{" "}
                {ver.greedy.random_count} instances. No approximation ratio is claimed.
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Timings come from one machine and vary between runs. Re-run <span className="font-mono">run_all.py</span>{" "}
                to refresh them.
              </p>
            </Card>
          </div>
        </Section>

        <footer className="border-t border-slate-800 pt-6 text-xs text-slate-500">
          Sarim Khan (CT-24266) · Muhammad Saraib (CT-24255) · Danish Meraj (CT-24268) · Muhammad Maaz Ali (CT-24265)
          · Instructor: Miss Tooba Shaikh
        </footer>
      </main>

      <Modal open={edgeOpen} onClose={() => setEdgeOpen(false)} title="CT-363 CEP edge cases">
        <EdgeCasesPanel />
      </Modal>
    </div>
  );
}
