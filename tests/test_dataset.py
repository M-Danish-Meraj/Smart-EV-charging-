"""Assert every design property of the Karachi-EV-12 dataset (brief section 4).

networkx appears here ONLY as an independent cross-check (allowed in tests/).
"""

import csv
import filecmp
import math
import subprocess
import sys
from collections import Counter, deque
from itertools import combinations, product
from pathlib import Path

import networkx as nx
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

MAIN = {"S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"}
CUTOFF = {"S09", "S10", "S11"}
ISOLATED = {"S12"}


def read(name):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_true(s):
    assert s in ("true", "false"), s
    return s == "true"


@pytest.fixture(scope="module")
def ds():
    return {
        "loc": read("locations.csv"),
        "roads": read("roads.csv"),
        "st": read("stations.csv"),
        "req": read("requests.csv"),
        "fail": read("e2_failures.csv"),
    }


def available(ds):
    return [r for r in ds["roads"] if is_true(r["available"])]


def components(site_ids, edges):
    """Plain BFS over (u, v) pairs; returns a list of frozensets."""
    adj = {s: [] for s in site_ids}
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen, comps = set(), []
    for s in sorted(site_ids):
        if s in seen:
            continue
        comp, queue = set(), deque([s])
        seen.add(s)
        while queue:
            x = queue.popleft()
            comp.add(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    queue.append(y)
        comps.append(frozenset(comp))
    return comps


def nx_graph(ds, roads):
    sev = {l["location_id"]: int(l["severity"]) for l in ds["loc"]}
    g = nx.Graph()
    g.add_nodes_from(sev)
    for r in roads:
        g.add_edge(r["u"], r["v"], weight=int(r["cost"]), eid=r["edge_id"])
    return g


# ---------- schema / validity ----------

def test_counts(ds):
    assert len(ds["loc"]) == 12
    assert len(ds["roads"]) == 24
    assert len(ds["st"]) == 4
    assert len(ds["req"]) == 24


def test_unique_ids(ds):
    for rows, key in [(ds["loc"], "location_id"), (ds["roads"], "edge_id"),
                      (ds["st"], "station_id"), (ds["req"], "request_id")]:
        ids = [r[key] for r in rows]
        assert len(ids) == len(set(ids)), key


def test_valid_endpoints_and_nonnegative(ds):
    sites = {l["location_id"] for l in ds["loc"]}
    pairs = set()
    for r in ds["roads"]:
        assert r["u"] in sites and r["v"] in sites and r["u"] != r["v"]
        assert int(r["cost"]) >= 0
        pair = frozenset((r["u"], r["v"]))
        assert pair not in pairs, f"parallel road {r['edge_id']}"
        pairs.add(pair)
    for s in ds["st"]:
        assert s["location_id"] in sites
        assert int(s["capacity_kwh"]) >= 0
    for q in ds["req"]:
        assert q["origin_id"] in sites


def test_unit_rounding(ds):
    for s in ds["st"]:
        assert int(s["capacity_units"]) == int(s["capacity_kwh"]) // 10   # down
    for q in ds["req"]:
        assert int(q["units"]) == math.ceil(int(q["energy_kwh"]) / 10)    # up


def test_benefits_integer_in_range(ds):
    for q in ds["req"]:
        assert q["benefit"].isdigit()
        assert 10 <= int(q["benefit"]) <= 100


# ---------- severity and hub ----------

def test_hub_and_top2_severity(ds):
    hubs = [l for l in ds["loc"] if is_true(l["is_hub"])]
    assert [h["name"] for h in hubs] == ["Saddar"]
    sev = sorted((int(l["severity"]) for l in ds["loc"]), reverse=True)
    assert sev[1] > sev[2], "top-2 severity must be unambiguous"
    top2 = {l["name"] for l in ds["loc"] if int(l["severity"]) >= sev[1]}
    assert top2 == {"Gulshan-e-Iqbal", "DHA"}
    assert hubs[0]["name"] not in top2


# ---------- roads and components ----------

def test_unavailable_roads_are_exactly_the_cutoff_links(ds):
    down = [r for r in ds["roads"] if not is_true(r["available"])]
    assert len(down) == 4
    for r in down:
        assert {r["u"], r["v"]} & MAIN and {r["u"], r["v"]} & CUTOFF
    # and every road between the two groups is unavailable
    for r in ds["roads"]:
        if {r["u"], r["v"]} & MAIN and {r["u"], r["v"]} & CUTOFF:
            assert not is_true(r["available"])


def test_surjani_has_no_available_road(ds):
    assert all("S12" not in (r["u"], r["v"]) for r in available(ds))


def test_baseline_has_three_components(ds):
    sites = [l["location_id"] for l in ds["loc"]]
    comps = components(sites, [(r["u"], r["v"]) for r in available(ds)])
    assert set(comps) == {frozenset(MAIN), frozenset(CUTOFF), frozenset(ISOLATED)}


def test_cheap_triangle_exists(ds):
    roads = available(ds)
    cost = {frozenset((r["u"], r["v"])): int(r["cost"]) for r in roads}
    cheapest = min(cost.values())
    sites = {x for p in cost for x in p}
    triangles = [t for t in combinations(sorted(sites), 3)
                 if all(frozenset(p) in cost for p in combinations(t, 2))]
    # the triangle must contain the globally cheapest available road
    assert any(min(cost[frozenset(p)] for p in combinations(t, 2)) == cheapest
               for t in triangles)


def test_equal_cost_groups(ds):
    counts = Counter(int(r["cost"]) for r in available(ds))
    assert sum(1 for c in counts.values() if c >= 2) >= 2


def test_equal_cost_group_needs_id_tiebreak(ds):
    """Some equal-cost roads also tie on s(u)+s(v), so the ID rule is used."""
    sev = {l["location_id"]: int(l["severity"]) for l in ds["loc"]}
    keys = Counter((int(r["cost"]), sev[r["u"]] + sev[r["v"]]) for r in available(ds))
    assert max(keys.values()) >= 2


def test_unavailable_road_cheaper_than_a_selected_road(ds):
    g = nx_graph(ds, available(ds))
    msf = nx.minimum_spanning_tree(g)                 # forest on disconnected g
    max_selected = max(d["weight"] for _, _, d in msf.edges(data=True))
    cheapest_down = min(int(r["cost"]) for r in ds["roads"] if not is_true(r["available"]))
    assert cheapest_down < max_selected


def test_msf_cost_and_edge_count(ds):
    g = nx_graph(ds, available(ds))
    msf = nx.minimum_spanning_tree(g)
    assert msf.size(weight="weight") == 36
    assert msf.number_of_edges() == 12 - 3            # n - (#components)


# ---------- E2 failure roads ----------

def test_e2_failure_roles(ds):
    roads = {r["edge_id"]: r for r in ds["roads"]}
    avail = available(ds)
    g = nx_graph(ds, avail)
    # Roles are checked by removing the road and comparing with the baseline,
    # so they hold for every minimum spanning forest, not just one of them.
    base_cost = nx.minimum_spanning_tree(g).size(weight="weight")
    base_comps = nx.number_connected_components(g)

    assert len(ds["fail"]) == 3
    roles = Counter(f["role"] for f in ds["fail"])
    assert roles == {"in_forest_with_replacement": 1,
                     "in_forest_no_replacement": 1,
                     "not_in_forest": 1}

    for f in ds["fail"]:
        r = roads[f["edge_id"]]
        assert is_true(r["available"]) and (r["u"], r["v"]) == (f["u"], f["v"])
        h = g.copy()
        h.remove_edge(r["u"], r["v"])
        new_cost = nx.minimum_spanning_tree(h).size(weight="weight")
        new_comps = nx.number_connected_components(h)
        if f["role"] == "not_in_forest":
            assert new_cost == base_cost and new_comps == base_comps
        elif f["role"] == "in_forest_no_replacement":
            assert new_comps == base_comps + 1                 # a bridge
        else:
            assert new_comps == base_comps                     # replacement exists
            assert new_cost > base_cost                        # so it was in every MSF

    # and all three failures together leave a valid graph for E2
    h = g.copy()
    for f in ds["fail"]:
        h.remove_edge(f["u"], f["v"])
    assert nx.number_connected_components(h) == base_comps + 1


def test_not_in_forest_road_is_never_selected(ds):
    """Stronger check: the road closes a cycle of strictly cheaper roads."""
    f = next(x for x in ds["fail"] if x["role"] == "not_in_forest")
    road = next(r for r in ds["roads"] if r["edge_id"] == f["edge_id"])
    w = int(road["cost"])
    cheaper = [r for r in available(ds) if int(r["cost"]) < w]
    sites = [l["location_id"] for l in ds["loc"]]
    comps = components(sites, [(r["u"], r["v"]) for r in cheaper])
    assert any(road["u"] in c and road["v"] in c for c in comps)


# ---------- stations ----------

def test_stations(ds):
    active = [s for s in ds["st"] if is_true(s["active"])]
    assert [s["station_id"] for s in active] == ["ST1", "ST2", "ST3"]
    caps = [int(s["capacity_units"]) for s in ds["st"]]
    assert len(caps) == len(set(caps)), "capacities must be distinct"
    by_id = {s["station_id"]: s for s in ds["st"]}
    assert by_id["ST1"]["location_id"] == "S02"
    assert by_id["ST2"]["location_id"] == "S05"
    assert by_id["ST3"]["location_id"] == "S09"
    assert by_id["ST4"]["location_id"] == "S08"


def test_dense_state_counts(ds):
    caps = {s["station_id"]: int(s["capacity_units"]) for s in ds["st"]}
    k3 = math.prod(caps[s] + 1 for s in ("ST1", "ST2", "ST3"))
    k4 = k3 * (caps["ST4"] + 1)
    assert (k3, k4) == (1040, 6240)


# ---------- requests ----------

def test_request_distribution(ds):
    where = Counter("main" if q["origin_id"] in MAIN else
                    "cutoff" if q["origin_id"] in CUTOFF else "isolated"
                    for q in ds["req"])
    assert where == {"main": 16, "cutoff": 7, "isolated": 1}


def _caps_by_group(ds):
    loc = {s["station_id"]: s["location_id"] for s in ds["st"] if is_true(s["active"])}
    cap = {s["station_id"]: int(s["capacity_units"]) for s in ds["st"] if is_true(s["active"])}
    main = [cap[s] for s in cap if loc[s] in MAIN]
    cut = [cap[s] for s in cap if loc[s] in CUTOFF]
    return main, cut


def test_too_heavy_requests(ds):
    main_caps, cut_caps = _caps_by_group(ds)
    heavy_main = [q for q in ds["req"]
                  if q["origin_id"] in MAIN and int(q["units"]) > max(main_caps)]
    heavy_cut = [q for q in ds["req"]
                 if q["origin_id"] in CUTOFF and int(q["units"]) > max(cut_caps)]
    assert [int(q["units"]) for q in heavy_main] == [14]
    assert [int(q["units"]) for q in heavy_cut] == [9]
    # 14 units exceeds every station, even ST4
    assert 14 > max(int(s["capacity_units"]) for s in ds["st"])


def test_real_over_demand_per_component(ds):
    main_caps, cut_caps = _caps_by_group(ds)
    feasible_main = sum(int(q["units"]) for q in ds["req"]
                        if q["origin_id"] in MAIN and int(q["units"]) <= max(main_caps))
    feasible_cut = sum(int(q["units"]) for q in ds["req"]
                       if q["origin_id"] in CUTOFF and int(q["units"]) <= max(cut_caps))
    assert feasible_main > sum(main_caps)
    assert feasible_cut > sum(cut_caps)
    assert sum(int(s["capacity_units"]) for s in ds["st"] if is_true(s["active"])) == 28


def test_isolated_request_has_no_reachable_station(ds):
    station_sites = {s["location_id"] for s in ds["st"]}
    iso = [q for q in ds["req"] if q["origin_id"] in ISOLATED]
    assert len(iso) == 1 and not (ISOLATED & station_sites)


# ---------- reproducibility ----------

def test_generator_is_deterministic(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_dataset.py"), str(tmp_path)],
                   check=True)
    for name in ("locations.csv", "roads.csv", "stations.csv",
                 "requests.csv", "e2_failures.csv"):
        assert filecmp.cmp(tmp_path / name, DATA / name, shallow=False), name
