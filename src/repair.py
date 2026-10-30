"""Incremental repair of a minimum spanning forest after road failures.

INCREMENTAL-DELETE-EDGES(F, E_active, failed):
    remove every failed road from E_active
    for each failed road e = (u, v):
        if e not in F: continue                      # forest still valid
        remove e from F
        C1 <- sites reachable from u in F, C2 <- from v    (BFS, O(n))
        candidates <- surviving roads with one end in C1, the other in C2  (O(m))
        if candidates: add the lowest-ranked one (same edge_key as Kruskal)
        else: keep the split (the component really broke in two)
Time O(r (n + m)) for r failures; r = 3 here, so O(n + m).

Why the result is a minimum spanning forest: removing e splits its tree into
C1 and C2. Any spanning forest of the new graph must cross that cut with one
road if a crossing road exists, and by the cut property the cheapest crossing
road is safe; all other forest roads stay optimal because they lie inside C1
or C2. Other failed tree roads never cross this cut (they are inside C1 or C2
too), so excluding them from the candidates up front changes nothing.

This is a simple repair, not a dynamic-MST data structure. It is NOT assumed
to be faster than full Kruskal; run_all.py measures both.
"""

from dataclasses import dataclass

from src.graph import adjacency, edge_key, reachable


@dataclass
class RepairAction:
    failed: object         # the failed Road
    action: str            # "not_in_forest" | "replaced" | "split"
    replacement: object = None


@dataclass
class RepairResult:
    forest: list
    total_cost: int
    actions: list
    surviving: list        # active roads after the failures


def repair_forest(sites, forest, active_edges, failed_ids, severity):
    failed_ids = list(failed_ids)
    failed_set = set(failed_ids)
    surviving = [r for r in active_edges if r.edge_id not in failed_set]
    by_id = {r.edge_id: r for r in active_edges}

    current = {r.edge_id: r for r in forest}       # F as a dict for O(1) membership
    actions = []
    for fid in failed_ids:
        road = by_id[fid]
        if fid not in current:
            actions.append(RepairAction(road, "not_in_forest"))
            continue
        del current[fid]                           # delete e from F
        adj = adjacency(sites, current.values())
        side_u = reachable(road.u, adj)            # C1
        side_v = reachable(road.v, adj)            # C2 (other components excluded)
        best = None
        for r in surviving:                        # scan for the cheapest crossing road
            crosses = ((r.u in side_u and r.v in side_v) or
                       (r.v in side_u and r.u in side_v))
            if crosses and (best is None or edge_key(r, severity) < edge_key(best, severity)):
                best = r
        if best is None:
            actions.append(RepairAction(road, "split"))
        else:
            current[best.edge_id] = best
            actions.append(RepairAction(road, "replaced", best))

    new_forest = list(current.values())
    return RepairResult(new_forest, sum(r.cost for r in new_forest), actions, surviving)
