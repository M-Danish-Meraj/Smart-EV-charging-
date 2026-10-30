"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

export function KpiCard({
  label,
  value,
  unit,
  detail,
  icon: Icon,
  accent = "#00F0FF",
  index = 0,
}: {
  label: string;
  value: string;
  unit?: string;
  detail?: string;
  icon: LucideIcon;
  accent?: string;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.04 * index, duration: 0.35 }}
      whileHover={{ y: -2 }}
      className="glass group relative overflow-hidden p-4"
    >
      <div
        className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-20 blur-2xl transition-opacity group-hover:opacity-40"
        style={{ background: accent }}
      />
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</span>
        <Icon className="h-4 w-4" style={{ color: accent }} aria-hidden />
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="font-mono text-2xl font-semibold text-slate-50">{value}</span>
        {unit && <span className="font-mono text-xs text-slate-400">{unit}</span>}
      </div>
      {detail && <p className="mt-1 font-mono text-[11px] text-slate-500">{detail}</p>}
    </motion.div>
  );
}
