"use client";

import { CheckCircle2, Scale, Unplug, Weight } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { results, road, roadName, siteName, station } from "@/data/results";
import { COLOR } from "@/lib/format";

const BLOCKED = new Set(["too_large_for_any_eligible_station", "no_eligible_station", "origin_site_removed"]);

/** The three CEP-mandatory edge cases, rebuilt from results.json, plus the raw log. */
export function EdgeCasesPanel() {
  const { e1 } = results;
  const alloc = e1.allocation;
  const forest = new Set(e1.forest);
  const droppedSelected = e1.dropped.filter((d) => forest.has(d.road));
  const [showLog, setShowLog] = useState(false);

  const perComponent = e1.components
    .map((c) => {
      const sites = new Set(c.sites);
      const demand = alloc.requests
        .filter((r) => sites.has(r.origin) && !BLOCKED.has(r.reason ?? ""))
        .reduce((a, r) => a + r.units, 0);
      const capacity = Object.entries(alloc.loads)
        .filter(([id]) => sites.has(station(id).site))
        .reduce((a, [, l]) => a + l.capacity, 0);
      return { c, demand, capacity };
    })
    .filter((x) => x.demand || x.capacity);

  const lost = alloc.requests.filter((r) => r.reason === "lost_to_capacity_competition");
  const heavy = alloc.requests.filter((r) => r.reason === "too_large_for_any_eligible_station");
  const noStation = alloc.requests.filter((r) => r.reason === "no_eligible_station");

  return (
    <div className="space-y-5 text-sm">
      <p className="text-xs text-slate-400">
        CT-363 CEP requires these three cases to run in the submitted code with actual output. Everything
        below is read from <code className="font-mono text-slate-300">results.json</code>.
      </p>

      <Case n={1} title="Disconnected graph" icon={Unplug} ok={droppedSelected.length === 0}>
        <p>
          Unavailable roads are filtered before sorting:{" "}
          {e1.dropped.map((d) => (
            <span key={d.road} className="mr-1.5 inline-block">
              <Badge color={COLOR.red}>
                {d.road} {roadName(d.road)} · {road(d.road).cost}
              </Badge>
            </span>
          ))}
        </p>
        <p>
          Kruskal returns a forest of {e1.forest.length} roads (cost {e1.cost}) over {e1.components.length}{" "}
          components. None of the filtered roads is selected, so no connection is invented.
        </p>
        <ul className="space-y-1 font-mono text-xs">
          {e1.components.map((c) => (
            <li key={c.label} className="text-slate-300">
              {c.label}: {c.sites.map(siteName).join(", ")}
              {c.has_hub ? <span className="text-cyan-neon"> [hub]</span> : null}
              {c.isolated ? <span className="text-slate-500"> [isolated]</span> : null}
            </li>
          ))}
        </ul>
      </Case>

      <Case n={2} title="Over-demand" icon={Scale} ok={Object.values(alloc.loads).every((l) => l.load <= l.capacity)}>
        <ul className="space-y-1 font-mono text-xs">
          {perComponent.map(({ c, demand, capacity }) => (
            <li key={c.label} className="text-slate-300">
              component {c.label} ({siteName(c.label)}…): feasible demand{" "}
              <span className="text-amber-400">{demand} units</span> vs capacity{" "}
              <span className="text-cyan-neon">{capacity} units</span>
            </li>
          ))}
        </ul>
        <p>
          Every station stays within capacity (
          {Object.entries(alloc.loads)
            .map(([id, l]) => `${id} ${l.load}/${l.capacity}`)
            .join(", ")}
          ). The DP serves {alloc.served} requests for a benefit of {alloc.benefit}. These{" "}
          {lost.length} feasible requests lose to capacity competition: {lost.map((r) => r.id).join(", ")}.
        </p>
      </Case>

      <Case n={3} title="Too-heavy request" icon={Weight} ok={heavy.length > 0}>
        <ul className="space-y-1 font-mono text-xs">
          {heavy.map((r) => (
            <li key={r.id} className="text-slate-300">
              {r.id} at {siteName(r.origin)} needs <span className="text-red-400">{r.units} units</span> ({r.kwh}{" "}
              kWh); eligible: {r.eligible.map((s) => `${s}=${alloc.loads[s]?.capacity}`).join(", ")} units → not
              assigned
            </li>
          ))}
        </ul>
        <p>
          These requests are labelled <code className="font-mono">too_large_for_any_eligible_station</code>{" "}
          before the DP runs. Separately, {noStation.map((r) => `${r.id} (${siteName(r.origin)})`).join(", ")}{" "}
          has no reachable station.
        </p>
      </Case>

      <div>
        <button
          onClick={() => setShowLog((v) => !v)}
          className="font-mono text-xs text-cyan-neon hover:underline"
          aria-expanded={showLog}
        >
          {showLog ? "Hide" : "Show"} raw edge_cases.log
        </button>
        {showLog && (
          <pre className="scrollbar-thin mt-2 max-h-96 overflow-auto rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-[11px] leading-relaxed text-slate-300">
            {results.edge_cases_log}
          </pre>
        )}
      </div>
    </div>
  );
}

function Case({
  n,
  title,
  icon: Icon,
  ok,
  children,
}: {
  n: number;
  title: string;
  icon: typeof Unplug;
  ok: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-xs leading-relaxed text-slate-400">
      <header className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
          <Icon className="h-4 w-4 text-cyan-neon" aria-hidden />
          Case {n}: {title}
        </h3>
        <Badge color={ok ? COLOR.emerald : COLOR.red}>
          <CheckCircle2 className="h-3 w-3" aria-hidden /> {ok ? "PASS" : "FAIL"}
        </Badge>
      </header>
      {children}
    </section>
  );
}
