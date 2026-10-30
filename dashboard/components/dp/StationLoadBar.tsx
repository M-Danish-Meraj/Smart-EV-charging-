"use client";

import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import { siteName, station } from "@/data/results";
import { COLOR, STATION_COLOR, pct } from "@/lib/format";

export function StationLoadBar({ id, load, capacity }: { id: string; load: number; capacity: number }) {
  const st = station(id);
  const share = capacity ? load / capacity : 0;
  const full = capacity > 0 && load >= capacity;
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="flex items-center gap-2 font-mono text-slate-200">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: STATION_COLOR[id] }} />
          {id} · {siteName(st.site)}
        </span>
        <span className="font-mono text-slate-400">
          {load}/{capacity} units · {pct(load, capacity)}
        </span>
      </div>
      <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          className="h-full rounded-full"
          style={{ background: STATION_COLOR[id] }}
          initial={{ width: 0 }}
          animate={{ width: `${share * 100}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      <div className="mt-1.5 flex items-center justify-between font-mono text-[10px] text-slate-500">
        <span>
          {st.capacity_kwh} kWh → {st.capacity_units} units (floor)
        </span>
        {full && (
          <span className="flex items-center gap-1" style={{ color: COLOR.amber }}>
            <AlertTriangle className="h-3 w-3" aria-hidden /> at capacity
          </span>
        )}
      </div>
    </div>
  );
}
