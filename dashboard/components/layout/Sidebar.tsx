"use client";

import { BatteryCharging, Gauge, LayoutDashboard, Network, ShieldCheck, SlidersHorizontal, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/format";

export const NAV = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "network", label: "Network (E1–E3)", icon: Network },
  { id: "allocation", label: "Allocation (DP)", icon: BatteryCharging },
  { id: "sensitivity", label: "Sensitivity (E4)", icon: SlidersHorizontal },
  { id: "scaling", label: "Scaling (E5)", icon: Gauge },
] as const;

/** Tracks which section is on screen so the nav can highlight it. */
function useActiveSection() {
  const [active, setActive] = useState<string>(NAV[0].id);
  useEffect(() => {
    // active = the last section whose top has passed 35% of the viewport height
    const onScroll = () => {
      const line = window.innerHeight * 0.35;
      let current: string = NAV[0].id;
      for (const n of NAV) {
        const el = document.getElementById(n.id);
        if (el && el.getBoundingClientRect().top <= line) current = n.id;
      }
      setActive(current);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return active;
}

export function Sidebar({ onEdgeCases }: { onEdgeCases: () => void }) {
  const active = useActiveSection();
  return (
    <>
      {/* desktop */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-slate-800 bg-[#0b0f17]/90 backdrop-blur-md lg:flex">
        <div className="flex items-center gap-2 px-5 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-neon/15 ring-1 ring-cyan-neon/40">
            <Zap className="h-4 w-4 text-cyan-neon" aria-hidden />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-100">Karachi-EV-12</div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">CT-363 · DAA</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3" aria-label="Sections">
          {NAV.map(({ id, label, icon: Icon }) => (
            <a
              key={id}
              href={`#${id}`}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active === id
                  ? "bg-cyan-neon/10 text-cyan-neon ring-1 ring-cyan-neon/30"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </a>
          ))}
          <button
            onClick={onEdgeCases}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-slate-800/60 hover:text-slate-100"
          >
            <ShieldCheck className="h-4 w-4" aria-hidden />
            CEP edge cases
          </button>
        </nav>
        <p className="px-5 pb-5 text-[11px] leading-relaxed text-slate-500">
          Synthetic data. Every number is read from <span className="font-mono">results.json</span>, which{" "}
          <span className="font-mono">run_all.py</span> generates.
        </p>
      </aside>

      {/* mobile / tablet */}
      <nav
        className="scrollbar-thin sticky top-0 z-30 flex gap-1 overflow-x-auto border-b border-slate-800 bg-[#0b0f17]/90 px-4 py-2 backdrop-blur-md lg:hidden"
        aria-label="Sections"
      >
        {NAV.map(({ id, label, icon: Icon }) => (
          <a
            key={id}
            href={`#${id}`}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs",
              active === id ? "bg-cyan-neon/10 text-cyan-neon" : "text-slate-400",
            )}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {label.split(" ")[0]}
          </a>
        ))}
        <button onClick={onEdgeCases} className="flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-slate-400">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden /> Edge cases
        </button>
      </nav>
    </>
  );
}
