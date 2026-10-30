"""Step 4: eligibility and the exact multi-knapsack DP."""

from dataclasses import replace
from pathlib import Path

import pytest

from src.dp import DPItem, solve_multi_knapsack
from src.eligibility import LOST, NO_ELIGIBLE, ORIGIN_REMOVED, TOO_LARGE, build_eligibility
from src.io_validate import Request, load_dataset
from src.pipeline import remove_sites, run_allocation, run_network

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ds():
    return load_dataset(ROOT / "data")


@pytest.fixture(scope="module")
def baseline(ds):
    net = run_network(ds)
    return net, run_allocation(ds, net)


# ---------- eligibility ----------

def test_eligibility_follows_components(baseline):
    _, alloc = baseline
    el = alloc.eligibility
    assert [s.station_id for s in el.stations] == ["ST1", "ST2", "ST3"]   # ST4 inactive
    assert el.eligible["EV01"] == ["ST1", "ST2"]      # Saddar: main component
    assert el.eligible["EV17"] == ["ST3"]             # Malir: cut-off component
    assert el.eligible["EV24"] == []                  # Surjani Town: isolated


def test_pre_dp_labels(baseline):
    _, alloc = baseline
    assert alloc.unserved["EV24"] == NO_ELIGIBLE
    assert alloc.unserved["EV08"] == TOO_LARGE        # 14 units > 12 and > 9
    assert alloc.unserved["EV20"] == TOO_LARGE        # 9 units > Malir's 7
    dp_ids = {r.request_id for r in alloc.eligibility.dp_requests}
    assert not dp_ids & {"EV08", "EV20", "EV24"}


def test_origin_removed_label(ds):
    ds3 = remove_sites(ds, ["S05", "S03"])
    alloc = run_allocation(ds3, run_network(ds3))
    assert alloc.unserved["EV09"] == ORIGIN_REMOVED   # request at Gulshan
    assert alloc.unserved["EV11"] == NO_ELIGIBLE      # Johar is now cut off


# ---------- mandatory: over-demand ----------

def test_over_demand_respects_capacity(baseline, ds):
    _, alloc = baseline
    for sid, load in alloc.loads.items():
        assert load <= alloc.capacities[sid]
    lost = [rid for rid, why in alloc.unserved.items() if why == LOST]
    assert lost, "over-demand must leave some feasible requests unserved"
    assert alloc.total_benefit == alloc.dp.total_benefit > 0


# ---------- mandatory: too-heavy request ----------

def test_too_heavy_request_is_never_assigned(baseline):
    _, alloc = baseline
    assert "EV08" not in alloc.assignment and "EV20" not in alloc.assignment


def test_dp_skips_item_heavier_than_every_station():
    res = solve_multi_knapsack([DPItem("A", 9, 100, [0, 1])], [5, 8])
    assert res.assignment == {} and res.total_benefit == 0


# ---------- mandatory: duplicate assignment guard ----------

def test_request_assigned_to_at_most_one_station():
    # one very attractive request, room for it in BOTH stations
    items = [DPItem("A", 3, 100, [0, 1]), DPItem("B", 3, 10, [0, 1])]
    res = solve_multi_knapsack(items, [3, 3])
    assert set(res.assignment) == {"A", "B"}
    assert sorted(res.assignment.values()) == [0, 1]        # one station each
    assert res.total_benefit == 110 and res.served == 2   # not 200 (A counted twice)


# ---------- zero requests / zero capacity ----------

def test_zero_requests():
    res = solve_multi_knapsack([], [5, 5])
    assert (res.assignment, res.total_benefit, res.loads) == ({}, 0, [0, 0])


def test_zero_capacity_station():
    res = solve_multi_knapsack([DPItem("A", 1, 50, [0]), DPItem("B", 2, 40, [0, 1])], [0, 2])
    assert res.assignment == {"B": 1} and res.total_benefit == 40


def test_no_stations_at_all():
    res = solve_multi_knapsack([DPItem("A", 1, 50, [])], [])
    assert res.assignment == {} and res.total_benefit == 0


def test_pipeline_with_zero_requests(ds):
    empty = replace(ds, requests=[])
    alloc = run_allocation(empty, run_network(empty))
    assert alloc.assignment == {} and alloc.total_benefit == 0


# ---------- optimality and tie rule ----------

def test_dp_beats_greedy_counterexample():
    # 50 units: greedy takes the single 50-unit request (100); optimum is 60 + 60
    items = [DPItem("A", 50, 100, [0]), DPItem("B", 20, 60, [0]), DPItem("C", 20, 60, [0])]
    res = solve_multi_knapsack(items, [50])
    assert res.total_benefit == 120 and set(res.assignment) == {"B", "C"}


def test_tie_prefers_more_requests_served():
    items = [DPItem("A", 4, 60, [0]), DPItem("B", 2, 30, [0]), DPItem("C", 2, 30, [0])]
    res = solve_multi_knapsack(items, [4])
    assert res.total_benefit == 60 and res.served == 2


def test_tie_prefers_lower_station_id():
    res = solve_multi_knapsack([DPItem("A", 2, 50, [0, 1])], [5, 5])
    assert res.assignment == {"A": 0}


def test_state_counts_dense_table():
    caps = [12, 9, 7]
    res = solve_multi_knapsack([DPItem("A", 1, 10, [0])], caps)
    assert res.states_per_layer == 13 * 10 * 8 == 1040
    assert res.total_states == 2 * 1040


def test_requests_with_zero_benefit_do_not_break_dp():
    res = solve_multi_knapsack([DPItem("A", 1, 0, [0])], [1])
    assert res.total_benefit == 0 and res.served == 1       # served wins the tie
