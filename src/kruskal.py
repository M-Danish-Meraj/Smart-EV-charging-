"""Part A (Greedy): Kruskal's minimum spanning forest with DSU.

KRUSKAL-MSF(V, E):
    A <- available edges of E                       O(m)
    sort A by edge_key                              O(m log m)
    MAKE-SET(v) for every v; F <- empty             O(n)
    for each (u, v, cost) in A:                     m iterations
        if FIND(u) != FIND(v):                      O(alpha(n)) amortized
            add (u, v, cost) to F; UNION(u, v)
    return F and the DSU components
Total O(n + m log m + m alpha(n)) = O(m log m) time, O(n + m) space.
"""

from dataclasses import dataclass

from src.dsu import DSU
from src.graph import edge_key


@dataclass
class TraceStep:
    road: object
    accepted: bool
    note: str


@dataclass
class MSF:
    forest: list          # selected roads, in the order Kruskal accepted them
    total_cost: int
    trace: list           # every road considered, accepted or rejected
    components: list      # list of sorted site lists, ordered by first site
    component_of: dict    # site -> component label (its smallest site ID)


def kruskal_msf(sites, edges, severity):
    # Step 1: keep only available roads (the caller usually filtered already;
    # repeating it here makes "unavailable is never selected" a local fact).
    candidates = [r for r in edges if r.available]

    # Step 2: one global order. Ties in cost are broken by severity, then IDs,
    # so the output is deterministic whatever order the input arrives in.
    candidates.sort(key=lambda r: edge_key(r, severity))

    dsu = DSU(sites)
    forest, trace, total = [], [], 0
    # Invariant: forest is acyclic, and every DSU set is exactly the vertex
    # set of one tree of forest (singletons count as trees).
    for r in candidates:
        if dsu.union(r.u, r.v):               # endpoints in different trees
            forest.append(r)
            total += r.cost
            trace.append(TraceStep(r, True, "joins two components"))
        else:                                 # same tree: would close a cycle
            trace.append(TraceStep(r, False, "rejected: would form a cycle"))

    comps = dsu.groups()
    component_of = {s: comp[0] for comp in comps for s in comp}
    return MSF(forest, total, trace, comps, component_of)


def describe_components(msf, names, hub=None):
    """Components with site NAMES; marks the hub's component and isolated sites."""
    out = []
    for comp in msf.components:
        out.append({
            "label": comp[0],
            "sites": comp,
            "names": [names[s] for s in comp],
            "has_hub": hub in comp,
            "isolated": len(comp) == 1,
        })
    return out
