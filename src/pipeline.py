"""Glue: run Part A then Part B on a Dataset, plus the dataset edits the
experiments need. Every run is checked by the validators before it returns.
"""

import time
from dataclasses import dataclass, replace

from src.dp import DPItem, solve_multi_knapsack
from src.eligibility import LOST, build_eligibility
from src.graph import build_active_graph
from src.io_validate import station_units
from src.kruskal import kruskal_msf
from src.validate import check_allocation, check_forest


@dataclass
class NetworkRun:
    graph: object        # ActiveGraph
    msf: object          # MSF
    runtime_s: float


@dataclass
class AllocationRun:
    eligibility: object
    dp: object                # DPResult
    assignment: dict          # request_id -> station_id
    unserved: dict            # request_id -> reason
    capacities: dict          # station_id -> units (stations used by the DP)
    loads: dict               # station_id -> units used
    total_units: int
    total_benefit: int
    runtime_s: float


def run_network(ds):
    t0 = time.perf_counter()
    g = build_active_graph(ds)
    msf = kruskal_msf(g.sites, g.edges, g.severity)
    runtime = time.perf_counter() - t0
    check_forest(g.sites, g.edges, msf.forest, msf.total_cost)
    return NetworkRun(g, msf, runtime)


def run_allocation(ds, network):
    t0 = time.perf_counter()
    el = build_eligibility(ds.requests, ds.stations, network.msf.component_of)
    index = {s.station_id: j for j, s in enumerate(el.stations)}
    items = [DPItem(r.request_id, r.units, r.benefit, [index[s] for s in el.eligible[r.request_id]])
             for r in el.dp_requests]
    capacities = [s.capacity_units for s in el.stations]
    dp = solve_multi_knapsack(items, capacities)
    runtime = time.perf_counter() - t0

    assignment = {rid: el.stations[j].station_id for rid, j in dp.assignment.items()}
    unserved = dict(el.reasons)
    for r in el.dp_requests:                     # feasible alone, lost in the DP
        if r.request_id not in assignment:
            unserved[r.request_id] = LOST

    by_id = {r.request_id: r for r in ds.requests}
    caps = {s.station_id: s.capacity_units for s in el.stations}
    benefit, loads = check_allocation(
        sorted(assignment.items()),
        {rid: (r.units, r.benefit) for rid, r in by_id.items()},
        caps, el.eligible, dp.total_benefit)
    total_units = sum(by_id[rid].units for rid in assignment)
    return AllocationRun(el, dp, assignment, unserved, caps, loads, total_units, benefit, runtime)


# ---------- dataset edits used by the experiments ----------

def fail_roads(ds, edge_ids):
    ids = set(edge_ids)
    return replace(ds, roads=[replace(r, available=False) if r.edge_id in ids else r
                              for r in ds.roads])


def remove_sites(ds, site_ids):
    """Deactivate sites, drop their incident roads and deactivate their stations."""
    ids = set(site_ids)
    return replace(
        ds,
        locations=[replace(l, active=False) if l.location_id in ids else l for l in ds.locations],
        roads=[r for r in ds.roads if r.u not in ids and r.v not in ids],
        stations=[replace(s, active=False) if s.location_id in ids else s for s in ds.stations])


def top_severity_sites(ds, count=2):
    ranked = sorted((l for l in ds.locations if l.active), key=lambda l: (-l.severity, l.location_id))
    return [l.location_id for l in ranked[:count]]


def scale_capacities(ds, percent_cut):
    """Cut every station's kWh capacity by percent_cut %, then round down to units."""
    out = []
    for s in ds.stations:
        kwh = s.capacity_kwh * (100 - percent_cut) // 100
        out.append(replace(s, capacity_kwh=kwh, capacity_units=station_units(kwh)))
    return replace(ds, stations=out)


def activate_station(ds, station_id):
    return replace(ds, stations=[replace(s, active=True) if s.station_id == station_id else s
                                 for s in ds.stations])


def add_requests(ds, new_requests):
    existing = {r.request_id for r in ds.requests}
    clash = existing & {r.request_id for r in new_requests}
    if clash:
        raise ValueError(f"request IDs already used: {sorted(clash)}")
    return replace(ds, requests=list(ds.requests) + list(new_requests))
