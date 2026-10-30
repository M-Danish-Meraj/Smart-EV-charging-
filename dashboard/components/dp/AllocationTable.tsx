"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { ReasonBadge, StationBadge } from "@/components/ui/Badge";
import { type Reason, type RequestOutcome, siteName } from "@/data/results";
import { cn } from "@/lib/format";

type Filter = "all" | "served" | Reason;

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "served", label: "Served" },
  { id: "lost_to_capacity_competition", label: "Capacity competition" },
  { id: "too_large_for_any_eligible_station", label: "Too large" },
  { id: "no_eligible_station", label: "No eligible station" },
  { id: "origin_site_removed", label: "Origin removed" },
];

export function AllocationTable({ requests }: { requests: RequestOutcome[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const count = (f: Filter) =>
    f === "all" ? requests.length : f === "served" ? requests.filter((r) => r.station).length : requests.filter((r) => r.reason === f).length;
  const rows = requests.filter((r) =>
    filter === "all" ? true : filter === "served" ? !!r.station : r.reason === filter,
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter requests">
        {FILTERS.filter((f) => f.id === "all" || count(f.id) > 0).map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            aria-pressed={filter === f.id}
            className={cn(
              "rounded-full border px-2.5 py-1 font-mono text-[11px] transition-colors",
              filter === f.id
                ? "border-cyan-neon bg-cyan-neon/15 text-cyan-neon"
                : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200",
            )}
          >
            {f.label} <span className="opacity-60">{count(f.id)}</span>
          </button>
        ))}
      </div>

      <div className="scrollbar-thin max-h-[440px] overflow-auto rounded-xl border border-slate-800">
        <table className="w-full min-w-[640px] text-xs">
          <thead className="sticky top-0 z-10 bg-slate-900 text-[11px] text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left font-normal">Request</th>
              <th className="px-3 py-2 text-left font-normal">Origin</th>
              <th className="px-3 py-2 text-right font-normal">Energy</th>
              <th className="px-3 py-2 text-right font-normal">Units</th>
              <th className="px-3 py-2 text-right font-normal">Benefit</th>
              <th className="px-3 py-2 text-left font-normal">Eligible</th>
              <th className="px-3 py-2 text-left font-normal">Outcome</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {rows.map((r) => (
                <motion.tr
                  key={r.id}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="border-t border-slate-800/70 hover:bg-slate-800/30"
                >
                  <td className="px-3 py-1.5 font-mono text-slate-200">{r.id}</td>
                  <td className="px-3 py-1.5 text-slate-300">{siteName(r.origin)}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-slate-400">{r.kwh} kWh</td>
                  <td className="px-3 py-1.5 text-right font-mono text-slate-200">{r.units}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-slate-200">{r.benefit}</td>
                  <td className="px-3 py-1.5 font-mono text-slate-500">{r.eligible.join(" ") || "–"}</td>
                  <td className="px-3 py-1.5">
                    {r.station ? <StationBadge id={r.station} /> : r.reason && <ReasonBadge reason={r.reason} />}
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  );
}
