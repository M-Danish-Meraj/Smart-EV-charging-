"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/format";

export interface TabItem<T extends string> {
  id: T;
  label: string;
  hint?: string;
}

/** Segmented control. layoutId gives the sliding highlight. */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  layoutId,
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  layoutId: string;
}) {
  return (
    <div
      role="tablist"
      className="inline-flex max-w-full flex-wrap gap-1 rounded-xl border border-slate-800 bg-slate-950/60 p-1"
    >
      {items.map((t) => {
        const active = t.id === value;
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={active}
            title={t.hint}
            onClick={() => onChange(t.id)}
            className={cn(
              "relative rounded-lg px-3 py-1.5 font-mono text-xs transition-colors focus-visible:outline-2 focus-visible:outline-cyan-neon",
              active ? "text-slate-950" : "text-slate-400 hover:text-slate-100",
            )}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-lg bg-cyan-neon"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative">{t.label}</span>
          </button>
        );
      })}
    </div>
  );
}
