"use client";

import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { results, siteName } from "@/data/results";
import { STATION_COLOR } from "@/lib/format";
import { componentColor, type RoadStatus, type Scenario, scenarioView } from "./scenario";

const W = 900;
const H = 560;
const PAD = { left: 60, right: 170, top: 40, bottom: 40 };

const ROAD_STYLE: Record<RoadStatus, { stroke: string; width: number; dash?: string; opacity: number }> = {
  forest: { stroke: "#00F0FF", width: 3, opacity: 1 },
  replacement: { stroke: "#10B981", width: 4, opacity: 1 },
  idle: { stroke: "#475569", width: 1.2, dash: "5 5", opacity: 0.7 },
  unavailable: { stroke: "#EF4444", width: 1.5, dash: "2 6", opacity: 0.75 },
  failed: { stroke: "#EF4444", width: 2.5, dash: "9 5", opacity: 1 },
  removed: { stroke: "#334155", width: 1, dash: "2 6", opacity: 0.35 },
};

export const ROAD_LEGEND: { status: RoadStatus; label: string }[] = [
  { status: "forest", label: "Selected (forest) road" },
  { status: "replacement", label: "Replacement road (E2)" },
  { status: "idle", label: "Available, not selected" },
  { status: "unavailable", label: "Unavailable road" },
  { status: "failed", label: "Failed road (E2)" },
  { status: "removed", label: "Removed with site (E3)" },
];

const STATUS_TEXT: Record<RoadStatus, string> = {
  forest: "in the spanning forest",
  replacement: "replacement added by repair",
  idle: "available, not selected (cycle or dearer)",
  unavailable: "unavailable: filtered before sorting",
  failed: "failed in E2",
  removed: "removed with its site in E3",
};

type Hover = { kind: "site"; id: string } | { kind: "road"; id: string } | null;

export function NetworkTopologyCanvas({ scenario }: { scenario: Scenario }) {
  const view = useMemo(() => scenarioView(scenario), [scenario]);
  const [hover, setHover] = useState<Hover>(null);

  // Project lon/lat into the SVG box (north up).
  const pos = useMemo(() => {
    const lons = results.sites.map((s) => s.lon);
    const lats = results.sites.map((s) => s.lat);
    const [x0, x1, y0, y1] = [Math.min(...lons), Math.max(...lons), Math.min(...lats), Math.max(...lats)];
    const sx = (W - PAD.left - PAD.right) / (x1 - x0);
    const sy = (H - PAD.top - PAD.bottom) / (y1 - y0);
    return new Map(
      results.sites.map((s) => [
        s.id,
        { x: PAD.left + (s.lon - x0) * sx, y: H - PAD.bottom - (s.lat - y0) * sy },
      ]),
    );
  }, []);

  const stationAt = new Map(results.stations.map((st) => [st.site, st]));
  const tip = tooltip(hover, view, pos);

  return (
    <div className="scrollbar-thin overflow-x-auto">
    <div className="relative min-w-[640px]">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full rounded-xl border border-slate-800 bg-slate-950/60"
        role="img"
        aria-label={`Road network, scenario ${scenario.toUpperCase()}: forest cost ${view.cost}`}
      >
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* roads: idle and filtered first, forest on top */}
        {[...view.roads]
          .sort((a, b) => order(a.status) - order(b.status))
          .map(({ road, status }) => {
            const a = pos.get(road.u)!;
            const b = pos.get(road.v)!;
            const st = ROAD_STYLE[status];
            const lit = hover?.kind === "road" && hover.id === road.id;
            const strong = status === "forest" || status === "replacement";
            return (
              <g
                key={`${scenario}-${road.id}`}
                onMouseEnter={() => setHover({ kind: "road", id: road.id })}
                onMouseLeave={() => setHover(null)}
                className="cursor-pointer"
              >
                {/* fat invisible hit target */}
                <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="transparent" strokeWidth={14} />
                <motion.line
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={st.stroke}
                  strokeWidth={lit ? st.width + 2 : st.width}
                  strokeDasharray={st.dash}
                  strokeLinecap="round"
                  opacity={st.opacity}
                  filter={strong ? "url(#glow)" : undefined}
                  initial={strong ? { pathLength: 0 } : { opacity: 0 }}
                  animate={strong ? { pathLength: 1 } : { opacity: st.opacity }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                />
                {status === "failed" && (
                  <text
                    x={(a.x + b.x) / 2}
                    y={(a.y + b.y) / 2 + 5}
                    textAnchor="middle"
                    className="fill-[#EF4444] font-mono text-[16px] font-bold"
                  >
                    ✕
                  </text>
                )}
                {strong && (
                  <g>
                    <rect
                      x={(a.x + b.x) / 2 - 10}
                      y={(a.y + b.y) / 2 - 9}
                      width={20}
                      height={16}
                      rx={4}
                      fill="#0B0F17"
                      stroke={st.stroke}
                      strokeOpacity={0.5}
                    />
                    <text
                      x={(a.x + b.x) / 2}
                      y={(a.y + b.y) / 2 + 3}
                      textAnchor="middle"
                      className="fill-slate-100 font-mono text-[11px]"
                    >
                      {road.cost}
                    </text>
                  </g>
                )}
              </g>
            );
          })}

        {/* sites */}
        {results.sites.map((s) => {
          const p = pos.get(s.id)!;
          const removed = view.removedSites.has(s.id);
          const st = stationAt.get(s.id);
          const stationOn = st && view.activeStations.has(st.id);
          const color = removed ? "#475569" : componentColor(view.components, view.componentOf.get(s.id) ?? -1);
          const lit = hover?.kind === "site" && hover.id === s.id;
          return (
            <g
              key={s.id}
              tabIndex={0}
              onMouseEnter={() => setHover({ kind: "site", id: s.id })}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover({ kind: "site", id: s.id })}
              onBlur={() => setHover(null)}
              className="cursor-pointer outline-none"
              opacity={removed ? 0.45 : 1}
            >
              {lit && <circle cx={p.x} cy={p.y} r={20} fill={color} opacity={0.15} />}
              {stationOn ? (
                <rect
                  x={p.x - 10}
                  y={p.y - 10}
                  width={20}
                  height={20}
                  rx={5}
                  fill="#0B0F17"
                  stroke={STATION_COLOR[st.id]}
                  strokeWidth={2.5}
                />
              ) : (
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={s.is_hub ? 11 : 8}
                  fill="#0B0F17"
                  stroke={color}
                  strokeWidth={2.5}
                  strokeDasharray={removed ? "3 3" : undefined}
                />
              )}
              <circle cx={p.x} cy={p.y} r={s.is_hub ? 4 : 3} fill={removed ? "#475569" : color} />
              <text x={p.x + 15} y={p.y - 6} className="fill-slate-200 text-[12px] font-medium">
                {s.name}
                {removed ? " (removed)" : ""}
              </text>
              <text x={p.x + 15} y={p.y + 9} className="fill-slate-500 font-mono text-[10px]">
                {s.id} · sev {s.severity}
                {s.is_hub ? " · HUB" : ""}
                {stationOn ? ` · ${st.id} ${st.capacity_units}u` : ""}
              </text>
            </g>
          );
        })}
      </svg>

      {tip && (
        <div
          className="pointer-events-none absolute z-10 max-w-[260px] rounded-lg border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-xl"
          style={{
            left: `${Math.min(tip.x / W, 0.72) * 100}%`,
            top: `${(tip.y / H) * 100}%`,
            transform: "translate(12px, 12px)",
          }}
        >
          {tip.lines.map((l, i) => (
            <div key={i} className={i === 0 ? "font-semibold text-slate-100" : "font-mono text-slate-400"}>
              {l}
            </div>
          ))}
        </div>
      )}
    </div>
    </div>
  );
}

function order(s: RoadStatus) {
  return { removed: 0, idle: 1, unavailable: 2, failed: 3, forest: 4, replacement: 5 }[s];
}

function tooltip(
  hover: Hover,
  view: ReturnType<typeof scenarioView>,
  pos: Map<string, { x: number; y: number }>,
): { x: number; y: number; lines: string[] } | null {
  if (!hover) return null;
  if (hover.kind === "site") {
    const s = results.sites.find((x) => x.id === hover.id)!;
    const p = pos.get(s.id)!;
    const st = results.stations.find((x) => x.site === s.id);
    const ci = view.componentOf.get(s.id);
    const comp = ci === undefined ? null : view.components[ci];
    return {
      x: p.x,
      y: p.y,
      lines: [
        `${s.name} (${s.id})`,
        `severity ${s.severity}${s.is_hub ? " · hub" : ""}`,
        st
          ? `${st.id}: ${st.capacity_kwh} kWh = ${st.capacity_units} units${view.activeStations.has(st.id) ? "" : " (inactive)"}`
          : "no station",
        view.removedSites.has(s.id)
          ? "removed in E3"
          : comp
            ? `component ${comp.label} · ${comp.sites.length} site${comp.sites.length > 1 ? "s" : ""}`
            : "",
      ].filter(Boolean),
    };
  }
  const r = view.roads.find((x) => x.road.id === hover.id)!;
  const a = pos.get(r.road.u)!;
  const b = pos.get(r.road.v)!;
  return {
    x: (a.x + b.x) / 2,
    y: (a.y + b.y) / 2,
    lines: [
      `${r.road.id}: ${siteName(r.road.u)} – ${siteName(r.road.v)}`,
      `cost ${r.road.cost}`,
      STATUS_TEXT[r.status],
    ],
  };
}

export function RoadLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[11px] text-slate-400">
      {ROAD_LEGEND.map(({ status, label }) => {
        const st = ROAD_STYLE[status];
        return (
          <li key={status} className="flex items-center gap-1.5">
            <svg width="26" height="8" aria-hidden>
              <line
                x1="1"
                y1="4"
                x2="25"
                y2="4"
                stroke={st.stroke}
                strokeWidth={Math.min(st.width, 3)}
                strokeDasharray={st.dash}
                opacity={Math.max(st.opacity, 0.6)}
                strokeLinecap="round"
              />
            </svg>
            {label}
          </li>
        );
      })}
      <li className="flex items-center gap-1.5">
        <svg width="12" height="12" aria-hidden>
          <rect x="1" y="1" width="10" height="10" rx="2.5" fill="none" stroke="#00F0FF" strokeWidth="2" />
        </svg>
        Active station
      </li>
    </ul>
  );
}
