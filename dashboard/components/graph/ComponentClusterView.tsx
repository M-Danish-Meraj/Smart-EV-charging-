import { type Component, siteName } from "@/data/results";
import { componentColor } from "./scenario";

export function ComponentClusterView({ components }: { components: Component[] }) {
  return (
    <ul className="space-y-2">
      {components.map((c, i) => {
        const color = componentColor(components, i);
        return (
          <li key={c.label} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2 font-mono text-xs text-slate-200">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
                Component {c.label}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wide text-slate-500">
                {c.has_hub ? "hub" : c.isolated ? "isolated" : `${c.sites.length} sites`}
              </span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
              {c.sites.map(siteName).join(", ")}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
