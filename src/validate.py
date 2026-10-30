"""Result validators, run by every experiment (brief section 7).

Each check recomputes what it verifies from scratch instead of trusting the
algorithm's own bookkeeping, and raises ValidationError on the first failure.
"""

from src.dsu import DSU
from src.graph import connected_components


class ValidationError(AssertionError):
    pass


def check_forest(sites, active_edges, forest, claimed_cost=None):
    """Network checks:
    1. every selected road is available and belongs to the active graph;
    2. the selected roads are acyclic;
    3. the forest spans every component of the active graph
       (same vertex partition as BFS on the active graph);
    4. total cost recomputed (and equal to claimed_cost if given).
    Returns the recomputed cost.
    """
    active_ids = {r.edge_id for r in active_edges}
    for r in forest:
        if not r.available:
            raise ValidationError(f"unavailable road {r.edge_id} selected")
        if r.edge_id not in active_ids:
            raise ValidationError(f"road {r.edge_id} is not in the active graph")

    dsu = DSU(sites)
    for r in forest:
        if not dsu.union(r.u, r.v):
            raise ValidationError(f"cycle: road {r.edge_id} joins one tree")

    if dsu.groups() != connected_components(sites, active_edges):
        raise ValidationError("forest does not span every component of the active graph")

    cost = sum(r.cost for r in forest)
    if claimed_cost is not None and cost != claimed_cost:
        raise ValidationError(f"claimed cost {claimed_cost} != recomputed {cost}")
    return cost


def check_allocation(assignments, requests, capacities, eligible, claimed_benefit=None):
    """Allocation checks:
    assignments: list of (request_id, station_id) pairs (a list, not a dict, so
                 a duplicated request would be visible here);
    requests:    request_id -> (units, benefit);
    capacities:  station_id -> capacity units;
    eligible:    request_id -> list of eligible station IDs.
    1. each request assigned at most once; 2. station load <= capacity;
    3. every assignment is eligible; 4. benefit recomputed (== claimed_benefit).
    Returns (benefit, loads).
    """
    seen = set()
    loads = {s: 0 for s in capacities}
    benefit = 0
    for rid, sid in assignments:
        if rid in seen:
            raise ValidationError(f"request {rid} assigned more than once")
        seen.add(rid)
        if sid not in capacities:
            raise ValidationError(f"{rid} assigned to unknown/inactive station {sid}")
        if sid not in eligible.get(rid, []):
            raise ValidationError(f"{rid} is not eligible for {sid}")
        units, b = requests[rid]
        loads[sid] += units
        benefit += b
    for sid, load in loads.items():
        if load > capacities[sid]:
            raise ValidationError(f"station {sid} load {load} > capacity {capacities[sid]}")
    if claimed_benefit is not None and benefit != claimed_benefit:
        raise ValidationError(f"reconstructed benefit {benefit} != DP value {claimed_benefit}")
    return benefit, loads
