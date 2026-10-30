import { results } from "@/data/results";
import { fmtBytes, fmtInt, fmtMs } from "@/lib/format";

/** E5 DP: q = n/2 requests with k = 3 and k = 4 stations. Time grows with q·k·S. */
export function DpScalingTable() {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full min-w-[460px] font-mono text-[11px]">
        <thead className="bg-slate-900 text-slate-500">
          <tr>
            {["q", "k", "S / layer", "total states", "DP time", "memory"].map((h) => (
              <th key={h} className="px-3 py-2 text-right font-normal first:text-left">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {results.e5.dp.map((r) => (
            <tr key={`${r.q}-${r.k}`} className="border-t border-slate-800/70">
              <td className="px-3 py-1.5 text-slate-200">{r.q}</td>
              <td className="px-3 py-1.5 text-right text-slate-400">{r.k}</td>
              <td className="px-3 py-1.5 text-right text-slate-300">{fmtInt(r.states_per_layer)}</td>
              <td className="px-3 py-1.5 text-right text-slate-300">{fmtInt(r.total_states)}</td>
              <td className="px-3 py-1.5 text-right text-cyan-neon">{fmtMs(r.dp_ms)}</td>
              <td className="px-3 py-1.5 text-right text-slate-400">{fmtBytes(r.table_bytes)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
