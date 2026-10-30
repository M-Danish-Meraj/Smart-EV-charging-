import { Check, X } from "lucide-react";
import { results } from "@/data/results";
import { fmtInt, fmtMs } from "@/lib/format";

export function KruskalVsRepairTable() {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full min-w-[520px] font-mono text-[11px]">
        <thead className="bg-slate-900 text-slate-500">
          <tr>
            {["n", "m", "full Kruskal", "repair", "repair / full", "cost equal"].map((h) => (
              <th key={h} className="px-3 py-2 text-right font-normal first:text-left">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.e5.network.map((r) => (
            <tr key={r.n} className="border-t border-slate-800/70">
              <td className="px-3 py-1.5 text-slate-200">{r.n}</td>
              <td className="px-3 py-1.5 text-right text-slate-400">{fmtInt(r.m)}</td>
              <td className="px-3 py-1.5 text-right text-slate-200">{fmtMs(r.full_ms)}</td>
              <td className="px-3 py-1.5 text-right text-emerald-400">{fmtMs(r.repair_ms)}</td>
              <td className="px-3 py-1.5 text-right text-slate-300">{(r.repair_ms / r.full_ms).toFixed(2)}×</td>
              <td className="px-3 py-1.5 text-right">
                {r.costs_equal ? (
                  <Check className="ml-auto h-3.5 w-3.5 text-emerald-400" aria-label="yes" />
                ) : (
                  <X className="ml-auto h-3.5 w-3.5 text-red-400" aria-label="no" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BruteVsDpTable() {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full min-w-[460px] font-mono text-[11px]">
        <thead className="bg-slate-900 text-slate-500">
          <tr>
            {["q", "assignments checked", "brute force", "exact DP", "speed-up", "same optimum"].map((h) => (
              <th key={h} className="px-3 py-2 text-right font-normal first:text-left">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.e5.brute.map((r) => (
            <tr key={r.q} className="border-t border-slate-800/70">
              <td className="px-3 py-1.5 text-slate-200">{r.q}</td>
              <td className="px-3 py-1.5 text-right text-slate-400">{fmtInt(r.checked)}</td>
              <td className="px-3 py-1.5 text-right text-red-400">{fmtMs(r.brute_ms)}</td>
              <td className="px-3 py-1.5 text-right text-cyan-neon">{fmtMs(r.dp_ms)}</td>
              <td className="px-3 py-1.5 text-right text-slate-300">{fmtInt(Math.round(r.brute_ms / r.dp_ms))}×</td>
              <td className="px-3 py-1.5 text-right">
                {r.same ? (
                  <Check className="ml-auto h-3.5 w-3.5 text-emerald-400" aria-label="yes" />
                ) : (
                  <X className="ml-auto h-3.5 w-3.5 text-red-400" aria-label="no" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
