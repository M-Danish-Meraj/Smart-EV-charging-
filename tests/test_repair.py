"""Step 6: incremental repair after road failures, checked against full Kruskal."""

import csv
import random
from pathlib import Path

import pytest

from src.graph import build_active_graph
from src.io_validate import load_dataset
from src.kruskal import kruskal_msf
from src.random_instances import random_graph
from src.repair import repair_forest
from src.validate import ValidationError, check_forest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ds():
    return load_dataset(ROOT / "data")


def failures():
    with open(ROOT / "data" / "e2_failures.csv", newline="") as f:
        return list(csv.DictReader(f))


def repair_and_full(g, msf, failed):
    rep = repair_forest(g.sites, msf.forest, g.edges, failed, g.severity)
    full = kruskal_msf(g.sites, rep.surviving, g.severity)
    return rep, full


def test_e2_three_failures_match_full_kruskal(ds):
    g = build_active_graph(ds)
    msf = kruskal_msf(g.sites, g.edges, g.severity)
    failed = [f["edge_id"] for f in failures()]
    rep, full = repair_and_full(g, msf, failed)
    check_forest(g.sites, rep.surviving, rep.forest, rep.total_cost)
    assert rep.total_cost == full.total_cost
    assert not {r.edge_id for r in rep.forest} & set(failed)    # failed never kept
    actions = {a.failed.edge_id: a for a in rep.actions}
    role = {f["edge_id"]: f["role"] for f in failures()}
    for eid, a in actions.items():
        expected = {"in_forest_with_replacement": "replaced",
                    "in_forest_no_replacement": "split",
                    "not_in_forest": "not_in_forest"}[role[eid]]
        assert a.action == expected, eid


def test_one_failure_in_forest_one_outside(ds):
    g = build_active_graph(ds)
    msf = kruskal_msf(g.sites, g.edges, g.severity)
    in_forest = "R06"          # PECHS - Gulshan-e-Iqbal
    outside = "R07"            # Clifton - PECHS
    assert in_forest in {r.edge_id for r in msf.forest}
    assert outside not in {r.edge_id for r in msf.forest}
    rep, full = repair_and_full(g, msf, [in_forest, outside])
    assert [a.action for a in rep.actions] == ["replaced", "not_in_forest"]
    # only one forest edge changed: repair touched just the broken cut
    assert len({r.edge_id for r in msf.forest} - {r.edge_id for r in rep.forest}) == 1
    assert rep.total_cost == full.total_cost


def test_failure_outside_forest_changes_nothing(ds):
    g = build_active_graph(ds)
    msf = kruskal_msf(g.sites, g.edges, g.severity)
    rep, _ = repair_and_full(g, msf, ["R07"])
    assert {r.edge_id for r in rep.forest} == {r.edge_id for r in msf.forest}


@pytest.mark.parametrize("seed", range(60))
def test_random_graph_repair_matches_full_kruskal(seed):
    rnd = random_graph(n=15 + seed, seed=seed)
    g = build_active_graph(rnd)
    msf = kruskal_msf(g.sites, g.edges, g.severity)
    rng = random.Random(seed)
    tree_ids = [r.edge_id for r in msf.forest]
    others = [r.edge_id for r in g.edges if r.edge_id not in set(tree_ids)]
    # mostly forest roads, since those are the ones that need repair
    failed = rng.sample(tree_ids, min(2, len(tree_ids))) + rng.sample(others, min(1, len(others)))
    rep, full = repair_and_full(g, msf, failed)
    check_forest(g.sites, rep.surviving, rep.forest, rep.total_cost)
    assert rep.total_cost == full.total_cost
    assert len(rep.forest) == len(full.forest)


def test_validator_rejects_forest_still_using_failed_road(ds):
    g = build_active_graph(ds)
    msf = kruskal_msf(g.sites, g.edges, g.severity)
    surviving = [r for r in g.edges if r.edge_id != "R06"]
    with pytest.raises(ValidationError):
        check_forest(g.sites, surviving, msf.forest)
