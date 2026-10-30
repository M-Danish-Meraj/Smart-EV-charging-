"""Active-graph construction: keep only available roads between active sites.

Also defines the single edge order used by Kruskal AND by incremental repair,
so both always rank roads the same way.
"""

from collections import deque
from dataclasses import dataclass


def edge_key(road, severity):
    """Kruskal order (smaller key = earlier):
        1. cost ascending                  (the only thing that affects total cost)
        2. s(u) + s(v) descending          (severity only breaks cost ties)
        3. min(u, v) ascending, 4. max(u, v) ascending   (stable final tie-break)
    """
    a, b = sorted((road.u, road.v))
    return (road.cost, -(severity[road.u] + severity[road.v]), a, b)


@dataclass
class ActiveGraph:
    sites: list        # active site IDs, sorted (n of them)
    edges: list        # available roads between active sites (m_active of them)
    dropped: list      # roads filtered out, with the reason
    severity: dict
    names: dict
    hub: str = None


def build_active_graph(ds):
    """O(n + m). A road is dropped if it is unavailable or touches an inactive site."""
    active = {l.location_id for l in ds.locations if l.active}
    edges, dropped = [], []
    for r in ds.roads:
        if not r.available:
            dropped.append((r, "unavailable"))
        elif r.u not in active or r.v not in active:
            dropped.append((r, "endpoint removed"))
        else:
            edges.append(r)
    return ActiveGraph(sorted(active), edges, dropped, ds.severity, ds.names,
                       ds.hub if ds.hub in active else None)


def adjacency(sites, edges):
    adj = {s: [] for s in sites}
    for r in edges:
        adj[r.u].append((r.v, r))
        adj[r.v].append((r.u, r))
    return adj


def reachable(start, adj):
    """BFS: set of sites reachable from start. O(n + m) over the given adjacency."""
    seen = {start}
    queue = deque([start])
    while queue:
        x = queue.popleft()
        for y, _ in adj[x]:
            if y not in seen:
                seen.add(y)
                queue.append(y)
    return seen


def connected_components(sites, edges):
    """Components by BFS (independent of DSU; the validators use this)."""
    adj = adjacency(sites, edges)
    seen, comps = set(), []
    for s in sorted(sites):
        if s not in seen:
            comp = reachable(s, adj)
            seen |= comp
            comps.append(sorted(comp))
    return comps
