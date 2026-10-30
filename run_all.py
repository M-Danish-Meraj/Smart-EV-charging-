"""Run every experiment (E1-E5), the edge-case log and the figures.

    python run_all.py            # full run (about a minute)
    python run_all.py --quick    # fewer timing repeats, for tests

Writes to output/:
    E1_baseline.md ... E5_scaling.md   one file per experiment
    verification.md                    DP vs brute force, heuristic gap
    edge_cases.log                     the CEP-mandatory edge cases
    results_summary.md                 everything above in one file
    results.json                       the same results as data, for the dashboard
    figures/*.png
Every number in the report must come from these files.
"""

import argparse
import csv
import json
import random
import statistics
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.brute import brute_force  # noqa: E402
from src.dp import DPItem, solve_multi_knapsack  # noqa: E402
from src.eligibility import LOST  # noqa: E402
from src.graph import build_active_graph, edge_key  # noqa: E402
from src.heuristic import greedy_allocate  # noqa: E402
from src.io_validate import KWH_PER_UNIT, Request, load_dataset, request_units  # noqa: E402
from src.kruskal import describe_components, kruskal_msf  # noqa: E402
from src.pipeline import (activate_station, add_requests, fail_roads, remove_sites,  # noqa: E402
                          run_allocation, run_network, scale_capacities, top_severity_sites)
from src.random_instances import random_graph, random_knapsack  # noqa: E402
from src.repair import repair_forest  # noqa: E402
from src.validate import check_forest  # noqa: E402

ROOT = Path(__file__).resolve().parent
CAPACITY_CUT_PERCENT = 25          # E4
E4_NEW_REQUESTS = 6                # E4
E5_SIZES = [20, 50, 100, 200]      # E5

# chart colours: reference categorical slots 1-3, status "critical" for unavailable
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRAY, RED, INK, INK2 = "#9a9993", "#d03b3b", "#0b0b0b", "#52514e"


# ---------- small helpers ----------

def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def median_time(fn, runs):
    """Median wall time (seconds) of fn() over `runs` runs, plus fn's last result."""
    times, result = [], None
    for _ in range(runs):
        t0 = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - t0)
    return statistics.median(times), result


def ms(seconds):
    return f"{seconds * 1000:.3f}"


def road_label(r, names):
    return f"{r.edge_id} {names[r.u]} - {names[r.v]}"


def site_list(sites, names):
    return ", ".join(names[s] for s in sites)


def reason_counts(alloc):
    counts = {}
    for why in alloc.unserved.values():
        counts[why] = counts.get(why, 0) + 1
    return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "none"


def utilization(alloc):
    cap = sum(alloc.capacities.values())
    return f"{100 * alloc.total_units / cap:.1f}%" if cap else "n/a"


# ---------- JSON export (dashboard reads output/results.json) ----------

def ms_num(seconds):
    return round(seconds * 1000, 4)


def components_json(components, hub):
    return [{"label": c[0], "sites": c, "has_hub": hub in c, "isolated": len(c) == 1}
            for c in components]


def alloc_json(ds, alloc):
    by_id = {r.request_id: r for r in ds.requests}
    counts = {}
    for why in alloc.unserved.values():
        counts[why] = counts.get(why, 0) + 1
    return {
        "served": len(alloc.assignment),
        "requests_total": len(ds.requests),
        "benefit": alloc.total_benefit,
        "units": alloc.total_units,
        "kwh": sum(by_id[r].energy_kwh for r in alloc.assignment),
        "capacity": sum(alloc.capacities.values()),
        "loads": {sid: {"capacity": c, "load": alloc.loads[sid]} for sid, c in alloc.capacities.items()},
        "unserved_counts": dict(sorted(counts.items())),
        "dp": {"states_per_layer": alloc.dp.states_per_layer, "total_states": alloc.dp.total_states,
               "table_bytes": alloc.dp.table_bytes},
        "requests": [{"id": r.request_id, "origin": r.origin_id, "kwh": r.energy_kwh, "units": r.units,
                      "benefit": r.benefit, "eligible": alloc.eligibility.eligible.get(r.request_id, []),
                      "station": alloc.assignment.get(r.request_id),
                      "reason": alloc.unserved.get(r.request_id)}
                     for r in sorted(ds.requests, key=lambda r: r.request_id)],
    }


def alloc_items(alloc):
    el = alloc.eligibility
    index = {s.station_id: j for j, s in enumerate(el.stations)}
    items = [DPItem(r.request_id, r.units, r.benefit, [index[s] for s in el.eligible[r.request_id]])
             for r in el.dp_requests]
    return items, [s.capacity_units for s in el.stations]


# ---------- figures ----------

def draw_network(ds, graph, forest, path, title, highlight=None):
    pos = {l.location_id: (l.longitude, l.latitude) for l in ds.locations if l.active}
    forest_ids = {r.edge_id for r in forest}
    fig, ax = plt.subplots(figsize=(8, 6.2), dpi=150)
    ax.set_facecolor("#fcfcfb")
    drawn = set()
    for r in ds.roads:
        if r.u not in pos or r.v not in pos:
            continue
        (x1, y1), (x2, y2) = pos[r.u], pos[r.v]
        if not r.available:
            style = dict(color=RED, lw=1.4, ls=":", label="unavailable road", zorder=1)
        elif highlight and r.edge_id in highlight:
            style = dict(color=ORANGE, lw=3, label="replacement road", zorder=3)
        elif r.edge_id in forest_ids:
            style = dict(color=BLUE, lw=2.4, label="selected (forest) road", zorder=2)
        else:
            style = dict(color=GRAY, lw=1, ls="--", label="available, not selected", zorder=1)
        if style["label"] in drawn:
            style.pop("label")
        else:
            drawn.add(style["label"])
        ax.plot([x1, x2], [y1, y2], **style)
        if r.edge_id in forest_ids or (highlight and r.edge_id in highlight):
            ax.text((x1 + x2) / 2, (y1 + y2) / 2, str(r.cost), fontsize=7, color=INK2,
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none"))
    stations = {s.location_id: s.station_id for s in ds.stations if s.active}
    for sid, (x, y) in pos.items():
        marker = "*" if sid == graph.hub else ("s" if sid in stations else "o")
        ax.scatter([x], [y], s=150 if marker == "*" else 60, marker=marker, color=INK,
                   edgecolors="#fcfcfb", linewidths=1.5, zorder=4)
        label = ds.names[sid] + (f" ({stations[sid]})" if sid in stations else "")
        ax.annotate(label, (x, y), xytext=(6, 5), textcoords="offset points", fontsize=8, color=INK)
    ax.scatter([], [], marker="*", s=100, color=INK, label="hub")
    ax.scatter([], [], marker="s", s=40, color=INK, label="active station site")
    ax.legend(loc="upper right", fontsize=7, frameon=False)
    ax.set_title(title, fontsize=11, color=INK, loc="left")
    ax.set_xlabel("longitude (approx., synthetic layout)", fontsize=8, color=INK2)
    ax.set_ylabel("latitude", fontsize=8, color=INK2)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(labelsize=7, colors=INK2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def style_axes(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=11, color=INK, loc="left")
    ax.set_xlabel(xlabel, fontsize=9, color=INK2)
    ax.set_ylabel(ylabel, fontsize=9, color=INK2)
    ax.grid(axis="y", color="#e6e5e0", lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=8, colors=INK2)


# ---------- experiments ----------

def e1_baseline(ds, runs, figdir):
    names = ds.names
    net = run_network(ds)
    alloc = run_allocation(ds, net)
    g, msf = net.graph, net.msf
    kruskal_t, _ = median_time(lambda: kruskal_msf(g.sites, g.edges, g.severity), runs)
    alloc_t, _ = median_time(lambda: run_allocation(ds, net), runs)
    by_id = {r.request_id: r for r in ds.requests}

    s = [f"# E1 Baseline (Karachi-EV-12, synthetic)\n",
         f"n = {len(ds.locations)} sites, m = {len(ds.roads)} roads "
         f"({len(g.edges)} available, {len(g.dropped)} filtered before sorting), "
         f"k = {len(alloc.capacities)} active stations, q = {len(ds.requests)} requests.\n",
         "## Roads filtered out before Kruskal\n",
         md_table(["road", "cost", "reason"],
                  [(road_label(r, names), r.cost, why) for r, why in g.dropped]),
         "\n## Kruskal trace (sorted edge order)\n",
         "Key: cost asc, s(u)+s(v) desc, min(u,v) asc, max(u,v) asc.\n",
         md_table(["#", "road", "cost", "s(u)+s(v)", "decision"],
                  [(i, road_label(t.road, names), t.road.cost,
                    g.severity[t.road.u] + g.severity[t.road.v],
                    "ACCEPT" if t.accepted else "reject (cycle)")
                   for i, t in enumerate(msf.trace, 1)]),
         f"\n## Minimum spanning forest: {len(msf.forest)} roads, total cost {msf.total_cost}\n",
         md_table(["road", "cost"], [(road_label(r, names), r.cost) for r in msf.forest]),
         f"\n## Components ({len(msf.components)})\n",
         md_table(["component", "sites", "hub?", "isolated?"],
                  [(c["label"], ", ".join(c["names"]), "yes" if c["has_hub"] else "",
                    "yes" if c["isolated"] else "")
                   for c in describe_components(msf, names, g.hub)]),
         "\n## Allocation (exact DP)\n",
         md_table(["request", "origin", "kWh", "units", "benefit", "eligible", "result"],
                  [(r.request_id, names[r.origin_id], r.energy_kwh, r.units, r.benefit,
                    " ".join(alloc.eligibility.eligible[r.request_id]) or "-",
                    alloc.assignment.get(r.request_id, "UNSERVED: " + alloc.unserved.get(r.request_id, "")))
                   for r in sorted(ds.requests, key=lambda r: r.request_id)]),
         "\n## Station loads\n",
         md_table(["station", "site", "capacity (units)", "load (units)", "used"],
                  [(s.station_id, names[s.location_id], alloc.capacities[s.station_id],
                    alloc.loads[s.station_id],
                    f"{100 * alloc.loads[s.station_id] / alloc.capacities[s.station_id]:.0f}%")
                   for s in alloc.eligibility.stations]),
         "\n## Totals\n",
         md_table(["metric", "value"], [
             ("requests served", f"{len(alloc.assignment)} of {len(ds.requests)}"),
             ("unserved by reason", reason_counts(alloc)),
             ("energy assigned", f"{alloc.total_units} units "
                                 f"({sum(by_id[r].energy_kwh for r in alloc.assignment)} kWh requested)"),
             ("capacity used", utilization(alloc)),
             ("total benefit", alloc.total_benefit),
             ("DP states per layer S", alloc.dp.states_per_layer),
             ("DP total states (q_dp+1) S", alloc.dp.total_states),
             ("DP table memory", f"{alloc.dp.table_bytes:,} bytes"),
             (f"Kruskal runtime (median of {runs})", f"{ms(kruskal_t)} ms"),
             (f"allocation runtime: eligibility + DP (median of {runs})", f"{ms(alloc_t)} ms"),
         ])]

    # stress run k = 4
    ds4 = activate_station(ds, "ST4")
    net4 = run_network(ds4)
    alloc4 = run_allocation(ds4, net4)
    t4, _ = median_time(lambda: run_allocation(ds4, net4), runs)
    s += ["\n## Stress run: k = 4 (ST4 Korangi activated)\n",
          md_table(["metric", "k = 3", "k = 4"], [
              ("states per layer S", alloc.dp.states_per_layer, alloc4.dp.states_per_layer),
              ("total states", alloc.dp.total_states, alloc4.dp.total_states),
              ("table memory (bytes)", f"{alloc.dp.table_bytes:,}", f"{alloc4.dp.table_bytes:,}"),
              ("requests served", len(alloc.assignment), len(alloc4.assignment)),
              ("total benefit", alloc.total_benefit, alloc4.total_benefit),
              (f"allocation runtime ms (median of {runs})", ms(alloc_t), ms(t4)),
          ])]

    draw_network(ds, g, msf.forest, figdir / "fig_network_baseline.png",
                 f"E1 baseline minimum spanning forest (cost {msf.total_cost})")
    data = {"forest": [r.edge_id for r in msf.forest], "cost": msf.total_cost,
            "trace": [{"road": t.road.edge_id, "accepted": t.accepted} for t in msf.trace],
            "dropped": [{"road": r.edge_id, "reason": why} for r, why in g.dropped],
            "components": components_json(msf.components, g.hub),
            "allocation": alloc_json(ds, alloc),
            "runtime_ms": {"kruskal": ms_num(kruskal_t), "allocation": ms_num(alloc_t)},
            "stress": {"station": "ST4", "allocation": alloc_json(ds4, alloc4),
                       "runtime_ms": ms_num(t4)}}
    return "\n".join(s), net, alloc, data


def e2_failures(ds, base_net, base_alloc, runs, figdir):
    names = ds.names
    g, msf = base_net.graph, base_net.msf
    with open(ROOT / "data" / "e2_failures.csv", newline="") as f:
        planned = list(csv.DictReader(f))
    failed = [p["edge_id"] for p in planned]

    rep = repair_forest(g.sites, msf.forest, g.edges, failed, g.severity)
    full = kruskal_msf(g.sites, rep.surviving, g.severity)
    check_forest(g.sites, rep.surviving, rep.forest, rep.total_cost)
    check_forest(g.sites, rep.surviving, full.forest, full.total_cost)

    rep_t, _ = median_time(lambda: repair_forest(g.sites, msf.forest, g.edges, failed, g.severity), runs)
    full_t, _ = median_time(lambda: kruskal_msf(g.sites, rep.surviving, g.severity), runs)
    rep_ids, full_ids = {r.edge_id for r in rep.forest}, {r.edge_id for r in full.forest}
    by_id = {r.edge_id: r for r in ds.roads}

    ds2 = fail_roads(ds, failed)
    alloc2 = run_allocation(ds2, run_network(ds2))
    comps = kruskal_msf(g.sites, rep.forest, g.severity).components

    s = ["# E2 Three-road failure: incremental repair vs full Kruskal\n",
         "Failure roads were chosen before the experiment (data/e2_failures.csv).\n",
         md_table(["failed road", "cost", "planned role", "repair action", "replacement"],
                  [(road_label(a.failed, names), a.failed.cost, p["role"], a.action,
                    road_label(a.replacement, names) + f" (cost {a.replacement.cost})"
                    if a.replacement else "-")
                   for a, p in zip(rep.actions, planned)]),
         "\n## Comparison\n",
         md_table(["metric", "incremental repair", "full Kruskal on modified graph"], [
             ("valid forest (validator)", "yes", "yes"),
             ("total cost", rep.total_cost, full.total_cost),
             ("roads in forest", len(rep.forest), len(full.forest)),
             (f"runtime ms (median of {runs})", ms(rep_t), ms(full_t)),
         ]),
         f"\nCost before failures: {msf.total_cost}. Costs equal: "
         f"{'yes' if rep.total_cost == full.total_cost else 'NO'}.",
         f"Edge-set difference (repair vs full): only in repair "
         f"{sorted(rep_ids - full_ids) or 'none'}, only in full {sorted(full_ids - rep_ids) or 'none'}.",
         "\n## Components after the failures\n",
         md_table(["component", "sites"], [(c[0], site_list(c, names)) for c in comps]),
         "\n## Allocation impact (DP rerun on the modified graph)\n",
         md_table(["metric", "baseline", "after failures"], [
             ("components", len(base_net.msf.components), len(comps)),
             ("requests served", len(base_alloc.assignment), len(alloc2.assignment)),
             ("unserved by reason", reason_counts(base_alloc), reason_counts(alloc2)),
             ("total benefit", base_alloc.total_benefit, alloc2.total_benefit),
         ]),
         "\nNote: runtime on a 12-site graph is microseconds; see E5 for larger graphs. "
         "The repair is not assumed to be faster."]

    replaced = {a.replacement.edge_id for a in rep.actions if a.replacement}
    draw_network(ds2, g, rep.forest, figdir / "fig_network_e2.png",
                 f"E2 forest after 3 road failures, repaired (cost {rep.total_cost})", replaced)
    data = {"cost_before": msf.total_cost,
            "failed": [{"road": a.failed.edge_id, "role": p["role"], "action": a.action,
                        "replacement": a.replacement.edge_id if a.replacement else None}
                       for a, p in zip(rep.actions, planned)],
            "repair_cost": rep.total_cost, "full_cost": full.total_cost,
            "forest": [r.edge_id for r in rep.forest],
            "full_forest": [r.edge_id for r in full.forest],
            "components": components_json(comps, g.hub),
            "runtime_ms": {"repair": ms_num(rep_t), "full": ms_num(full_t)},
            "allocation": alloc_json(ds2, alloc2)}
    return "\n".join(s), alloc2, data


def e3_remove_top2(ds, base_net, base_alloc, figdir):
    names = ds.names
    top2 = top_severity_sites(ds, 2)
    ds3 = remove_sites(ds, top2)
    net3 = run_network(ds3)
    alloc3 = run_allocation(ds3, net3)
    b, n3 = base_net.msf, net3.msf
    removed_roads = [r for r in ds.roads if r.u in top2 or r.v in top2]
    removed_stations = [s.station_id for s in ds.stations if s.location_id in top2 and s.active]

    s = ["# E3 Remove the two highest-severity sites\n",
         f"Removed sites: {site_list(top2, names)} "
         f"(severity {', '.join(str(ds.severity[x]) for x in top2)}). "
         f"Hub {names[ds.hub]} (severity {ds.severity[ds.hub]}) is not in the top 2.",
         f"Removed roads ({len(removed_roads)}): {', '.join(r.edge_id for r in removed_roads)}. "
         f"Deactivated stations: {', '.join(removed_stations) or 'none'}. Both stages rerun.\n",
         md_table(["metric", "baseline (E1)", "after removal (E3)"], [
             ("forest cost", b.total_cost, n3.total_cost),
             ("forest roads", len(b.forest), len(n3.forest)),
             ("components", len(b.components), len(n3.components)),
             ("active stations", " ".join(base_alloc.capacities), " ".join(alloc3.capacities)),
             ("total capacity (units)", sum(base_alloc.capacities.values()), sum(alloc3.capacities.values())),
             ("requests served", len(base_alloc.assignment), len(alloc3.assignment)),
             ("unserved by reason", reason_counts(base_alloc), reason_counts(alloc3)),
             ("energy assigned (units)", base_alloc.total_units, alloc3.total_units),
             ("total benefit", base_alloc.total_benefit, alloc3.total_benefit),
         ]),
         "\n## Components after removal\n",
         md_table(["component", "sites", "isolated?"],
                  [(c["label"], ", ".join(c["names"]), "yes" if c["isolated"] else "")
                   for c in describe_components(n3, names, ds3.hub)]),
         "\n## Forest after removal\n",
         md_table(["road", "cost"], [(road_label(r, names), r.cost) for r in n3.forest]),
         "\n## Requests whose outcome changed\n",
         md_table(["request", "origin", "eligible before", "eligible after", "before", "after"],
                  [(r.request_id, names[r.origin_id],
                    " ".join(base_alloc.eligibility.eligible[r.request_id]) or "-",
                    " ".join(alloc3.eligibility.eligible[r.request_id]) or "-",
                    base_alloc.assignment.get(r.request_id, base_alloc.unserved.get(r.request_id)),
                    alloc3.assignment.get(r.request_id, alloc3.unserved.get(r.request_id)))
                   for r in sorted(ds.requests, key=lambda r: r.request_id)
                   if base_alloc.assignment.get(r.request_id, base_alloc.unserved.get(r.request_id))
                   != alloc3.assignment.get(r.request_id, alloc3.unserved.get(r.request_id))]),
         "\nThese are model outputs only; no safety claim is made. Severity is only a "
         "tie-break in Kruskal, so Kruskal does not maximise severity coverage."]
    draw_network(ds3, net3.graph, n3.forest, figdir / "fig_network_e3.png",
                 f"E3 forest without {site_list(top2, names)} (cost {n3.total_cost})")
    data = {"removed_sites": top2, "removed_roads": [r.edge_id for r in removed_roads],
            "deactivated_stations": removed_stations, "cost": n3.total_cost,
            "forest": [r.edge_id for r in n3.forest],
            "components": components_json(n3.components, ds3.hub),
            "allocation": alloc_json(ds3, alloc3)}
    return "\n".join(s), alloc3, data


def e4_capacity_demand(ds, base_alloc):
    names = ds.names
    rng = random.Random(4)
    origins = ["S01", "S04", "S07", "S02", "S09", "S10", "S06", "S11"]
    start = len(ds.requests) + 1
    new = []
    for i in range(E4_NEW_REQUESTS):
        kwh = rng.randint(11, 30)
        new.append(Request(f"EV{start + i:02d}", origins[i % len(origins)], kwh,
                           request_units(kwh), rng.randint(10, 100)))

    scenarios = [("E1 baseline", ds),
                 (f"E4a capacity -{CAPACITY_CUT_PERCENT}%", scale_capacities(ds, CAPACITY_CUT_PERCENT)),
                 (f"E4b +{E4_NEW_REQUESTS} requests", add_requests(ds, new)),
                 ("E4c both", add_requests(scale_capacities(ds, CAPACITY_CUT_PERCENT), new))]
    rows, unserved_rows, results, scen_json = [], [], {}, []
    for label, d in scenarios:
        a = run_allocation(d, run_network(d))
        results[label] = a
        rows.append((label, " ".join(f"{k}={v}" for k, v in a.capacities.items()),
                     len(d.requests), len(a.assignment), len(a.unserved), a.total_units,
                     utilization(a), a.total_benefit))
        lost = sorted(r for r, why in a.unserved.items() if why == LOST)
        unserved_rows.append((label, ", ".join(lost) or "-"))
        scen_json.append({"label": label, "capacities": a.capacities, "requests": len(d.requests),
                          "served": len(a.assignment), "unserved": len(a.unserved),
                          "units": a.total_units, "capacity": sum(a.capacities.values()),
                          "benefit": a.total_benefit, "lost": lost})

    s = ["# E4 Capacity and demand sensitivity\n",
         f"E4a cuts every station's kWh capacity by {CAPACITY_CUT_PERCENT}% and rounds down to units. "
         f"E4b adds {E4_NEW_REQUESTS} requests with new IDs (seeded, 11-30 kWh, benefit 10-100). "
         "E4c applies both.\n",
         "## New requests (E4b, E4c)\n",
         md_table(["request", "origin", "kWh", "units", "benefit"],
                  [(r.request_id, names[r.origin_id], r.energy_kwh, r.units, r.benefit) for r in new]),
         "\n## Results\n",
         md_table(["scenario", "capacities (units)", "requests", "served", "unserved",
                   "energy (units)", "capacity used", "benefit"], rows),
         "\n## Requests lost to capacity competition\n",
         md_table(["scenario", "requests"], unserved_rows)]
    data = {"cut_percent": CAPACITY_CUT_PERCENT,
            "new_requests": [{"id": r.request_id, "origin": r.origin_id, "kwh": r.energy_kwh,
                              "units": r.units, "benefit": r.benefit} for r in new],
            "scenarios": scen_json}
    return "\n".join(s), results, data


def e5_scaling(runs, quick):
    rows_net = []
    for n in E5_SIZES:
        rnd = random_graph(n, seed=n)
        g = build_active_graph(rnd)
        msf = kruskal_msf(g.sites, g.edges, g.severity)
        rng = random.Random(n)
        tree = [r.edge_id for r in msf.forest]
        tree_set = set(tree)
        others = [r.edge_id for r in g.edges if r.edge_id not in tree_set]
        failed = rng.sample(tree, 2) + rng.sample(others, 1)
        kr_t, _ = median_time(lambda: kruskal_msf(g.sites, g.edges, g.severity), runs)
        rep_t, rep = median_time(lambda: repair_forest(g.sites, msf.forest, g.edges, failed, g.severity), runs)
        full_t, full = median_time(lambda: kruskal_msf(g.sites, rep.surviving, g.severity), runs)
        check_forest(g.sites, rep.surviving, rep.forest, rep.total_cost)
        rows_net.append((n, len(g.edges), len(msf.components), kr_t, rep_t, full_t,
                         rep.total_cost == full.total_cost))

    rows_dp = []
    for n in E5_SIZES:
        for caps in ([12, 9, 7], [12, 9, 7, 5]):
            q = n // 2
            rng = random.Random(n * 10 + len(caps))
            items = [DPItem(f"R{i:03d}", rng.randint(1, 4), rng.randint(10, 100),
                            sorted(rng.sample(range(len(caps)), rng.randint(1, len(caps)))))
                     for i in range(q)]
            t, res = median_time(lambda: solve_multi_knapsack(items, caps), max(3, runs // 4))
            rows_dp.append((n, q, len(caps), res.states_per_layer, res.total_states, t, res.table_bytes))

    rows_cap = []
    rng = random.Random(55)
    items = [DPItem(f"R{i:02d}", rng.randint(1, 6), rng.randint(10, 100), [0, 1, 2]) for i in range(24)]
    for f in ([1, 2, 4] if quick else [1, 2, 4, 8]):
        caps = [12 * f, 9 * f, 7 * f]
        t, res = median_time(lambda: solve_multi_knapsack(items, caps), 3)
        rows_cap.append((f, caps, res.states_per_layer, t, res.table_bytes))

    rows_bf = []
    for qq in ([4, 6, 8] if quick else [4, 6, 8, 10]):
        rng = random.Random(qq)
        caps = [8, 6, 5]
        items = [DPItem(f"R{i:02d}", rng.randint(1, 4), rng.randint(10, 100), [0, 1, 2]) for i in range(qq)]
        bf_t, bf = median_time(lambda: brute_force(items, caps), 1)
        dp_t, dp = median_time(lambda: solve_multi_knapsack(items, caps), 5)
        rows_bf.append((qq, bf.checked, bf_t, dp_t, bf.total_benefit == dp.total_benefit))

    s = ["# E5 Scaling (random synthetic graphs and instances)\n",
         f"Timings: time.perf_counter, median of {runs} runs (DP: median of {max(3, runs // 4)}), "
         "same machine and Python process.\n",
         "## Network: full Kruskal vs incremental repair (3 failures: 2 forest roads, 1 other)\n",
         md_table(["n sites", "m active roads", "components", "Kruskal ms", "repair ms",
                   "full Kruskal after failures ms", "repair/full", "costs equal"],
                  [(n, m, c, ms(a), ms(b), ms(f), f"{b / f:.2f}x", "yes" if eq else "NO")
                   for n, m, c, a, b, f, eq in rows_net]),
         "\n## DP: q = n/2 requests, k = 3 and 4 stations (capacities 12, 9, 7 [, 5])\n",
         md_table(["n", "q", "k", "S per layer", "total states", "DP ms", "table bytes"],
                  [(n, q, k, S, T, ms(t), f"{b:,}") for n, q, k, S, T, t, b in rows_dp]),
         "\n## DP: pseudo-polynomial growth with capacity (q = 24, k = 3)\n",
         md_table(["capacity factor", "capacities", "S per layer", "DP ms", "table bytes"],
                  [(f, caps, S, ms(t), f"{b:,}") for f, caps, S, t, b in rows_cap]),
         "\n## Brute force vs DP (k = 3)\n",
         md_table(["q", "assignments checked", "brute force ms", "DP ms", "same optimum"],
                  [(q, f"{c:,}", ms(b), ms(d), "yes" if eq else "NO") for q, c, b, d, eq in rows_bf])]
    return "\n".join(s), rows_net, rows_dp, rows_cap, rows_bf


def verification(base_alloc, instances):
    agree = 0
    for seed in range(instances):
        raw, caps = random_knapsack(10_000 + seed, q_max=9, k_max=3, cap_max=8)
        items = [DPItem(*x) for x in raw]
        dp = solve_multi_knapsack(items, caps)
        bf = brute_force(items, caps)
        agree += (dp.total_benefit, dp.served) == (bf.total_benefit, bf.served)

    items, caps = alloc_items(base_alloc)
    _, g_benefit = greedy_allocate(items, caps)
    gaps = []
    for seed in range(instances):
        raw, caps2 = random_knapsack(20_000 + seed, q_max=9, k_max=3, cap_max=8)
        it2 = [DPItem(*x) for x in raw]
        best = solve_multi_knapsack(it2, caps2).total_benefit
        _, gb = greedy_allocate(it2, caps2)
        if best:
            gaps.append(100 * (best - gb) / best)
    s = ["# Verification\n",
         f"DP vs brute force on {instances} random instances (q <= 9, k <= 3, capacities 0-8, "
         f"including zero-capacity stations and too-heavy items): "
         f"{agree} of {instances} agree on (benefit, served).\n",
         "## Optional greedy baseline (benefit per unit; no approximation ratio claimed)\n",
         md_table(["instance", "DP benefit", "greedy benefit", "gap"], [
             ("E1 dataset", base_alloc.total_benefit, g_benefit,
              f"{100 * (base_alloc.total_benefit - g_benefit) / base_alloc.total_benefit:.1f}%"),
             (f"{len(gaps)} random instances: mean gap", "", "", f"{statistics.mean(gaps):.1f}%"),
             (f"{len(gaps)} random instances: max gap", "", "", f"{max(gaps):.1f}%"),
             ("random instances where greedy was optimal", "", "",
              f"{sum(1 for x in gaps if x == 0)} of {len(gaps)}"),
         ])]
    data = {"instances": instances, "agree": agree,
            "greedy": {"dataset_dp": base_alloc.total_benefit, "dataset_greedy": g_benefit,
                       "random_count": len(gaps), "mean_gap_pct": round(statistics.mean(gaps), 2),
                       "max_gap_pct": round(max(gaps), 2),
                       "optimal_count": sum(1 for x in gaps if x == 0)}}
    return "\n".join(s), data


def edge_cases(ds, net, alloc):
    names = ds.names
    g, msf = net.graph, net.msf
    lines = ["CT-363 CEP mandatory edge cases (generated by run_all.py on Karachi-EV-12, synthetic)",
             "=" * 78, "",
             "CASE 1: DISCONNECTED GRAPH",
             "-" * 26,
             f"Unavailable roads filtered before sorting: "
             f"{', '.join(road_label(r, names) for r, _ in g.dropped)}"]
    lines.append(f"Kruskal returns a minimum spanning FOREST: {len(msf.forest)} roads, "
                 f"total cost {msf.total_cost}, {len(msf.components)} components.")
    for c in describe_components(msf, names, g.hub):
        tag = " [HUB component]" if c["has_hub"] else (" [ISOLATED]" if c["isolated"] else "")
        lines.append(f"  component {c['label']}: {', '.join(c['names'])}{tag}")
    selected = {r.edge_id for r in msf.forest}
    lines.append("No connection invented: none of the filtered roads is in the forest -> "
                 f"{'OK' if not selected & {r.edge_id for r, _ in g.dropped} else 'FAIL'}")

    lines += ["", "CASE 2: OVER-DEMAND", "-" * 19]
    by_id = {r.request_id: r for r in ds.requests}
    for comp in msf.components:
        caps = sum(alloc.capacities[s.station_id] for s in alloc.eligibility.stations
                   if msf.component_of[s.location_id] == comp[0])
        demand = sum(r.units for r in alloc.eligibility.dp_requests if msf.component_of[r.origin_id] == comp[0])
        if demand or caps:
            lines.append(f"  component {comp[0]} ({names[comp[0]]}...): feasible demand {demand} units "
                         f"vs capacity {caps} units")
    for s in alloc.eligibility.stations:
        lines.append(f"  {s.station_id} at {names[s.location_id]}: load {alloc.loads[s.station_id]} "
                     f"<= capacity {alloc.capacities[s.station_id]} -> "
                     f"{'OK' if alloc.loads[s.station_id] <= alloc.capacities[s.station_id] else 'FAIL'}")
    lost = sorted(r for r, why in alloc.unserved.items() if why == LOST)
    lines.append(f"  served {len(alloc.assignment)} requests, total benefit {alloc.total_benefit}")
    lines.append(f"  unserved (lost to capacity competition): {', '.join(lost)}")

    lines += ["", "CASE 3: TOO-HEAVY REQUEST", "-" * 25]
    for rid, why in sorted(alloc.unserved.items()):
        if why == "too_large_for_any_eligible_station":
            r = by_id[rid]
            el = alloc.eligibility.eligible[rid]
            lines.append(f"  {rid} at {names[r.origin_id]}: needs {r.units} units ({r.energy_kwh} kWh); "
                         f"eligible stations {', '.join(f'{s}={alloc.capacities[s]}' for s in el)} units "
                         f"-> not assigned, reason: {why}")
    lines.append(f"  (and {', '.join(r for r, w in alloc.unserved.items() if w == 'no_eligible_station')} "
                 "is unserved because no station is reachable: no_eligible_station)")

    lines += ["", "ADDITIONAL CASES", "-" * 16]
    tri = {t.road.edge_id: t for t in msf.trace}
    lines.append(f"  cycle prevention: R03 {names['S01']}-{names['S02']} -> "
                 f"{'rejected (cycle)' if not tri['R03'].accepted else 'ACCEPTED (FAIL)'}")
    order = [t.road.edge_id for t in msf.trace]
    lines.append(f"  equal-cost tie: cost-6 roads processed in order "
                 f"{[x for x in order if by_road(ds, x).cost == 6]}")
    dup = solve_multi_knapsack([DPItem("A", 3, 100, [0, 1]), DPItem("B", 3, 10, [0, 1])], [3, 3])
    lines.append(f"  duplicate-assignment guard: attractive request A fits both stations -> "
                 f"assignment {dup.assignment}, benefit {dup.total_benefit} (A counted once)")
    z1 = solve_multi_knapsack([], [5, 5])
    z2 = solve_multi_knapsack([DPItem("A", 1, 50, [0])], [0])
    lines.append(f"  zero requests: assignment {z1.assignment}, benefit {z1.total_benefit}")
    lines.append(f"  zero capacity: assignment {z2.assignment}, benefit {z2.total_benefit}")
    rep = repair_forest(g.sites, msf.forest, g.edges, ["R06", "R07"], g.severity)
    full = kruskal_msf(g.sites, rep.surviving, g.severity)
    lines.append(f"  incremental failure: R06 (in forest) -> {rep.actions[0].action} by "
                 f"{rep.actions[0].replacement.edge_id}; R07 (not in forest) -> {rep.actions[1].action}; "
                 f"repair cost {rep.total_cost} vs full Kruskal {full.total_cost}")
    return "\n".join(lines) + "\n"


def by_road(ds, edge_id):
    return next(r for r in ds.roads if r.edge_id == edge_id)


def figures(figdir, scenarios, rows_net, rows_cap, rows_bf):
    # total benefit per scenario (one series, so no legend; values labelled)
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    labels = [s for s, _ in scenarios]
    values = [a.total_benefit for _, a in scenarios]
    bars = ax.bar(range(len(values)), values, width=0.6, color=BLUE)
    for b, a in zip(bars, (a for _, a in scenarios)):
        ax.annotate(f"{a.total_benefit}\n{len(a.assignment)} served", (b.get_x() + b.get_width() / 2,
                    b.get_height()), xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylim(0, max(values) * 1.25)
    style_axes(ax, "Total benefit served by the exact DP, per scenario", "scenario", "total benefit")
    fig.tight_layout()
    fig.savefig(figdir / "fig_benefit_by_scenario.png")
    plt.close(fig)

    # network runtime
    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    ns = [r[0] for r in rows_net]
    ax.plot(ns, [r[3] * 1000 for r in rows_net], color=BLUE, lw=2, marker="o", ms=6,
            label="full Kruskal (original graph)")
    ax.plot(ns, [r[4] * 1000 for r in rows_net], color=ORANGE, lw=2, marker="o", ms=6,
            label="incremental repair (3 failures)")
    style_axes(ax, "E5 network: median runtime vs number of sites", "n sites", "milliseconds")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(figdir / "fig_e5_network_runtime.png")
    plt.close(fig)

    # DP growth with capacity
    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    ax.plot([r[2] for r in rows_cap], [r[3] * 1000 for r in rows_cap], color=BLUE, lw=2, marker="o", ms=6)
    for f, caps, S, t, _ in rows_cap:
        ax.annotate(f"x{f}", (S, t * 1000), xytext=(5, -12), textcoords="offset points", fontsize=8, color=INK2)
    style_axes(ax, "E5 DP: runtime grows with the state count S (q = 24, k = 3)",
               "states per layer S = prod(C_j + 1)", "milliseconds")
    fig.tight_layout()
    fig.savefig(figdir / "fig_e5_dp_states.png")
    plt.close(fig)

    # brute force vs DP
    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    qs = [r[0] for r in rows_bf]
    ax.plot(qs, [r[2] * 1000 for r in rows_bf], color=ORANGE, lw=2, marker="o", ms=6, label="brute force")
    ax.plot(qs, [r[3] * 1000 for r in rows_bf], color=BLUE, lw=2, marker="o", ms=6, label="exact DP")
    ax.set_yscale("log")
    style_axes(ax, "E5 brute force vs DP (k = 3), log scale", "q requests", "milliseconds (log)")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(figdir / "fig_e5_brute_vs_dp.png")
    plt.close(fig)


def main(out_dir="output", quick=False):
    out = Path(out_dir)
    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    runs = 5 if quick else 20
    ds = load_dataset(ROOT / "data")

    sections = {}
    sections["E1_baseline"], net, alloc, e1_json = e1_baseline(ds, runs, figdir)
    sections["E2_three_road_failure"], alloc2, e2_json = e2_failures(ds, net, alloc, runs, figdir)
    sections["E3_remove_top2"], alloc3, e3_json = e3_remove_top2(ds, net, alloc, figdir)
    sections["E4_capacity_demand"], e4, e4_json = e4_capacity_demand(ds, alloc)
    sections["E5_scaling"], rows_net, rows_dp, rows_cap, rows_bf = e5_scaling(runs, quick)
    sections["verification"], ver_json = verification(alloc, 40 if quick else 200)
    scenarios = [("E1", alloc), ("E2", alloc2), ("E3", alloc3)] + [
        (k.split()[0], v) for k, v in e4.items() if not k.startswith("E1")]
    figures(figdir, scenarios, rows_net, rows_cap, rows_bf)

    for name, text in sections.items():
        (out / f"{name}.md").write_text(text + "\n", encoding="utf-8")
    log = edge_cases(ds, net, alloc)
    (out / "edge_cases.log").write_text(log, encoding="utf-8")
    summary = ("# Results summary (generated by run_all.py; Karachi-EV-12 is SYNTHETIC)\n\n"
               + "\n\n".join(sections.values()) + "\n\n# Edge cases\n\n```\n" + log + "```\n")
    (out / "results_summary.md").write_text(summary, encoding="utf-8")

    results = {
        "meta": {"dataset": "Karachi-EV-12", "synthetic": True, "timing_runs": runs, "quick": quick,
                 "kwh_per_unit": KWH_PER_UNIT},
        "sites": [{"id": l.location_id, "name": l.name, "lat": l.latitude, "lon": l.longitude,
                   "severity": l.severity, "is_hub": l.is_hub} for l in ds.locations],
        "roads": [{"id": r.edge_id, "u": r.u, "v": r.v, "cost": r.cost, "available": r.available}
                  for r in ds.roads],
        "stations": [{"id": s.station_id, "site": s.location_id, "capacity_kwh": s.capacity_kwh,
                      "capacity_units": s.capacity_units, "active": s.active} for s in ds.stations],
        "e1": e1_json, "e2": e2_json, "e3": e3_json, "e4": e4_json,
        "e5": {
            "network": [{"n": n, "m": m, "components": c, "kruskal_ms": ms_num(a), "repair_ms": ms_num(b),
                         "full_ms": ms_num(f), "costs_equal": eq} for n, m, c, a, b, f, eq in rows_net],
            "dp": [{"n": n, "q": q, "k": k, "states_per_layer": S, "total_states": T, "dp_ms": ms_num(t),
                    "table_bytes": b} for n, q, k, S, T, t, b in rows_dp],
            "capacity": [{"factor": f, "capacities": caps, "states_per_layer": S, "dp_ms": ms_num(t),
                          "table_bytes": b} for f, caps, S, t, b in rows_cap],
            "brute": [{"q": q, "checked": c, "brute_ms": ms_num(b), "dp_ms": ms_num(d), "same": eq}
                      for q, c, b, d, eq in rows_bf],
        },
        "verification": ver_json,
        "edge_cases_log": log,
    }
    (out / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(summary)
    return sections


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true", help="fewer repeats (used by tests)")
    p.add_argument("--out", default=str(ROOT / "output"))
    a = p.parse_args()
    main(a.out, a.quick)
