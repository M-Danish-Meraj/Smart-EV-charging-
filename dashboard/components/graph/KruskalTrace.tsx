import { Check, X } from "lucide-react";
import { results, road, roadName } from "@/data/results";

/** The sorted edge order Kruskal scanned, with accept / reject (cycle). */
export function KruskalTrace() {
  const sev = new Map(results.sites.map((s) => [s.id, s.severity]));
  return (
    <div className="scrollbar-thin max-h-72 overflow-y-auto rounded-xl border border-slate-800">
      <table className="w-full font-mono text-[11px]">
        <thead className="sticky top-0 bg-slate-900 text-slate-500">
          <tr>
            <th className="px-2 py-1.5 text-left font-normal">#</th>
            <th className="px-2 py-1.5 text-left font-normal">road</th>
            <th className="px-2 py-1.5 text-right font-normal">cost</th>
            <th className="px-2 py-1.5 text-right font-normal">s(u)+s(v)</th>
            <th className="px-2 py-1.5 text-right font-normal">result</th>
          </tr>
        </thead>
        <tbody>
          {results.e1.trace.map((t, i) => {
            const r = road(t.road);
            return (
              <tr key={t.road} className="border-t border-slate-800/70">
                <td className="px-2 py-1 text-slate-500">{i + 1}</td>
                <td className="px-2 py-1 text-slate-300">
                  {t.road}
                  <div className="max-w-[140px] truncate text-[10px] text-slate-500" title={roadName(t.road)}>
                    {roadName(t.road)}
                  </div>
                </td>
                <td className="px-2 py-1 text-right text-slate-200">{r.cost}</td>
                <td className="px-2 py-1 text-right text-slate-400">{sev.get(r.u)! + sev.get(r.v)!}</td>
                <td className="px-2 py-1 text-right">
                  {t.accepted ? (
                    <span className="inline-flex items-center gap-1 text-emerald-400">
                      <Check className="h-3 w-3" aria-hidden /> accept
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-slate-500">
                      <X className="h-3 w-3" aria-hidden /> cycle
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
