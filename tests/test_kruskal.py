"""Step 3: DSU, loader/validation, active graph and Kruskal MSF."""

import csv
import random
import shutil
from dataclasses import replace
from pathlib import Path

import networkx as nx
import pytest

from src.dsu import DSU
from src.graph import build_active_graph, connected_components, edge_key
from src.io_validate import DataError, Road, load_dataset
from src.kruskal import describe_components, kruskal_msf
from src.random_instances import random_graph

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ds():
    return load_dataset(ROOT / "data")


def run(ds):
    g = build_active_graph(ds)
    return g, kruskal_msf(g.sites, g.edges, g.severity)


def nx_cost(sites, roads):
    g = nx.Graph()
    g.add_nodes_from(sites)
    for r in roads:
        if r.available:
            g.add_edge(r.u, r.v, weight=r.cost)
    return nx.minimum_spanning_tree(g).size(weight="weight")


# ---------- DSU ----------

def test_dsu_union_find_and_groups():
    d = DSU("abcde")
    assert d.union("a", "b") and d.union("c", "d") and d.union("b", "d")
    assert not d.union("a", "c")                 # already one set
    assert d.connected("a", "d") and not d.connected("a", "e")
    assert d.groups() == [["a", "b", "c", "d"], ["e"]]


def test_dsu_path_compression_flattens():
    d = DSU(range(6))
    for i in range(5):
        d.union(i, i + 1)
    root = d.find(5)
    assert all(d.parent[i] == root for i in range(6))
    assert max(d.rank.values()) <= 2             # union by rank keeps trees shallow


# ---------- loading and validation ----------

def _copy_data(tmp_path):
    dst = tmp_path / "data"
    shutil.copytree(ROOT / "data", dst)
    return dst


def _edit(path, row_index, field, value):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows[row_index][field] = value
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


@pytest.mark.parametrize("file,row,field,value,msg", [
    ("roads.csv", 1, "edge_id", "R01", "duplicate road"),
    ("locations.csv", 1, "location_id", "S01", "duplicate location"),
    ("roads.csv", 0, "cost", "-3", "negative cost"),
    ("roads.csv", 0, "v", "S99", "invalid endpoint"),
    ("roads.csv", 0, "v", "S02", "self-loop"),
    ("stations.csv", 0, "capacity_kwh", "-5", "negative capacity"),
    ("stations.csv", 0, "capacity_units", "13", "floor"),
    ("requests.csv", 0, "units", "1", "ceil"),
    ("requests.csv", 0, "origin_id", "S77", "unknown origin"),
    ("roads.csv", 0, "available", "yes", "true/false"),
    ("roads.csv", 0, "cost", "abc", "integer"),
])
def test_validation_rejects_bad_input(tmp_path, file, row, field, value, msg):
    d = _copy_data(tmp_path)
    _edit(d / file, row, field, value)
    with pytest.raises(DataError, match=msg):
        load_dataset(d)


def test_dataset_loads_clean(ds):
    assert (len(ds.locations), len(ds.roads), len(ds.stations), len(ds.requests)) == (12, 24, 4, 24)
    assert ds.hub == "S01"


# ---------- active graph ----------

def test_unavailable_roads_dropped_before_sorting(ds):
    g = build_active_graph(ds)
    assert len(g.edges) == 20 and len(g.dropped) == 4
    assert all(r.available for r in g.edges)
    assert all(reason == "unavailable" for _, reason in g.dropped)


# ---------- Kruskal: mandatory cases ----------

def test_unavailable_edge_never_selected(ds):
    g, msf = run(ds)
    ids = {r.edge_id for r in msf.forest}
    assert not ids & {r.edge_id for r, _ in g.dropped}
    # even if passed straight to Kruskal, an unavailable road is skipped
    cheapest_down = min((r for r, _ in g.dropped), key=lambda r: r.cost)
    msf2 = kruskal_msf(g.sites, g.edges + [cheapest_down], g.severity)
    assert cheapest_down.edge_id not in {r.edge_id for r in msf2.forest}


def test_cycle_prevention_cheap_triangle(ds):
    _, msf = run(ds)
    step = {t.road.edge_id: t for t in msf.trace}
    # triangle Saddar-Clifton-DHA: R01 (2), R02 (3), R03 (3)
    assert step["R01"].accepted and step["R02"].accepted
    assert not step["R03"].accepted and "cycle" in step["R03"].note


def test_equal_cost_tiebreak_is_deterministic(ds):
    g, msf = run(ds)
    order = [t.road.edge_id for t in msf.trace]
    assert order.index("R02") < order.index("R03")     # S01-S03 (sum 15) before S01-S02 (14)
    assert order.index("R09") < order.index("R10")     # equal sum 16: S03 < S05
    for seed in range(20):                              # any input order -> same forest
        edges = g.edges[:]
        random.Random(seed).shuffle(edges)
        again = kruskal_msf(g.sites, edges, g.severity)
        assert [r.edge_id for r in again.forest] == [r.edge_id for r in msf.forest]


def test_disconnected_graph_components_by_name(ds):
    g, msf = run(ds)
    comps = describe_components(msf, g.names, g.hub)
    assert len(comps) == 3
    hub_comp = next(c for c in comps if c["has_hub"])
    assert sorted(hub_comp["names"]) == sorted(["Saddar", "Clifton", "DHA", "PECHS",
                                                "Gulshan-e-Iqbal", "Gulistan-e-Johar",
                                                "North Nazimabad", "Korangi"])
    assert [c["names"] for c in comps if c["isolated"]] == [["Surjani Town"]]
    assert len(msf.forest) == len(g.sites) - len(comps)     # a forest, not a tree


def test_cost_matches_networkx_on_dataset(ds):
    g, msf = run(ds)
    assert msf.total_cost == nx_cost(g.sites, g.edges)


@pytest.mark.parametrize("seed", range(40))
def test_cost_matches_networkx_on_random_graphs(seed):
    rnd = random_graph(n=10 + seed * 4, seed=seed, unavailable_share=0.15)
    g = build_active_graph(rnd)
    msf = kruskal_msf(g.sites, g.edges, g.severity)
    assert msf.total_cost == nx_cost(g.sites, g.edges)
    assert len(msf.components) == len(connected_components(g.sites, g.edges))


def test_edge_key_orders_cost_first():
    sev = {"A": 1, "B": 1, "C": 10, "D": 10}
    cheap = Road("x", "A", "B", 1, True)
    pricey_but_severe = Road("y", "C", "D", 2, True)
    assert edge_key(cheap, sev) < edge_key(pricey_but_severe, sev)


def test_empty_and_single_site_graph():
    assert kruskal_msf([], [], {}).total_cost == 0
    msf = kruskal_msf(["A"], [], {"A": 1})
    assert msf.forest == [] and msf.components == [["A"]]
