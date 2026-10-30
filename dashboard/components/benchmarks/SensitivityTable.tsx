import { results, siteName } from "@/data/results";
import { pct } from "@/lib/format";

export function SensitivityTable() {
  const base = results.e4.scenarios[0];
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full min-w-[640px] text-[11px]">
        <thead className="bg-slate-900 text-slate-500">
          <tr>
            {["Scenario", "Capacities", "Served", "Energy", "Used", "Benefit", "Lost to competition"].map((h) => (
              <th key={h} className="px-3 py-2 text-left font-normal">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-mono">
          {results.e4.scenarios.map((s) => {
            const delta = s.benefit - base.benefit;
            return (
              <tr key={s.label} className="border-t border-slate-800/70 align-top">
                <td className="px-3 py-1.5 font-sans text-slate-200">{s.label}</td>
                <td className="px-3 py-1.5 text-slate-400">
                  {Object.entries(s.capacities)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(" ")}
                </td>
                <td className="px-3 py-1.5 text-slate-200">
                  {s.served}/{s.requests}
                </td>
                <td className="px-3 py-1.5 text-slate-300">
                  {s.units}/{s.capacity} units
                </td>
                <td className="px-3 py-1.5 text-amber-400">{pct(s.units, s.capacity)}</td>
                <td className="px-3 py-1.5 text-slate-100">
                  {s.benefit}{" "}
                  {s !== base && (
                    <span className={delta >= 0 ? "text-emerald-400" : "text-red-400"}>
                      ({delta >= 0 ? "+" : ""}
                      {delta})
                    </span>
                  )}
                </td>
                <td className="max-w-[260px] px-3 py-1.5 text-slate-500">{s.lost.join(", ")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="border-t border-slate-800 px-3 py-2 text-[11px] text-slate-500">
        E4a cuts every station by {results.e4.cut_percent}% of its kWh, then rounds down. E4b adds{" "}
        {results.e4.new_requests.length} requests (
        {results.e4.new_requests.map((r) => `${r.id} @ ${siteName(r.origin)}`).join(", ")}).
      </p>
    </div>
  );
}
