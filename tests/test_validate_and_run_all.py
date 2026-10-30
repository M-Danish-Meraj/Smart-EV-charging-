"""Steps 7-8: validators catch bad results; run_all.py produces every output."""

from pathlib import Path

import pytest

from src.graph import build_active_graph
from src.io_validate import Road, load_dataset
from src.kruskal import kruskal_msf
from src.validate import ValidationError, check_allocation, check_forest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def net():
    g = build_active_graph(load_dataset(ROOT / "data"))
    return g, kruskal_msf(g.sites, g.edges, g.severity)


# ---------- network validator ----------

def test_forest_validator_accepts_kruskal(net):
    g, msf = net
    assert check_forest(g.sites, g.edges, msf.forest, msf.total_cost) == msf.total_cost


def test_forest_validator_rejects_cycle(net):
    g, msf = net
    closing = next(t.road for t in msf.trace if not t.accepted)
    with pytest.raises(ValidationError, match="cycle"):
        check_forest(g.sites, g.edges, msf.forest + [closing])


def test_forest_validator_rejects_unavailable_road(net):
    g, msf = net
    bad = Road("RX", "S08", "S11", 2, False)
    with pytest.raises(ValidationError, match="unavailable"):
        check_forest(g.sites, g.edges, msf.forest + [bad])


def test_forest_validator_rejects_missing_span(net):
    g, msf = net
    with pytest.raises(ValidationError, match="span"):
        check_forest(g.sites, g.edges, msf.forest[:-1])


def test_forest_validator_rejects_wrong_cost(net):
    g, msf = net
    with pytest.raises(ValidationError, match="cost"):
        check_forest(g.sites, g.edges, msf.forest, msf.total_cost + 1)


# ---------- allocation validator ----------

REQ = {"A": (3, 50), "B": (2, 40)}
CAP = {"ST1": 4, "ST2": 2}
ELIG = {"A": ["ST1"], "B": ["ST1", "ST2"]}


def test_allocation_validator_accepts_valid():
    assert check_allocation([("A", "ST1"), ("B", "ST2")], REQ, CAP, ELIG, 90)[0] == 90


@pytest.mark.parametrize("pairs,claimed,msg", [
    ([("A", "ST1"), ("A", "ST1")], None, "more than once"),
    ([("A", "ST1"), ("B", "ST1")], None, "capacity"),
    ([("A", "ST2")], None, "not eligible"),
    ([("A", "ST1")], 99, "DP value"),
    ([("A", "ST9")], None, "unknown"),
])
def test_allocation_validator_rejects(pairs, claimed, msg):
    with pytest.raises(ValidationError, match=msg):
        check_allocation(pairs, REQ, CAP, ELIG, claimed)


# ---------- run_all.py end to end ----------

@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    import run_all
    out = tmp_path_factory.mktemp("output")
    run_all.main(out, quick=True)
    return out


def test_run_all_writes_every_file(outputs):
    for name in ["E1_baseline.md", "E2_three_road_failure.md", "E3_remove_top2.md",
                 "E4_capacity_demand.md", "E5_scaling.md", "verification.md",
                 "edge_cases.log", "results_summary.md"]:
        assert (outputs / name).stat().st_size > 0, name
    figs = {p.name for p in (outputs / "figures").glob("*.png")}
    assert {"fig_network_baseline.png", "fig_network_e2.png", "fig_network_e3.png",
            "fig_benefit_by_scenario.png", "fig_e5_network_runtime.png",
            "fig_e5_dp_states.png", "fig_e5_brute_vs_dp.png"} <= figs


def test_edge_case_log_has_the_three_cep_cases(outputs):
    log = (outputs / "edge_cases.log").read_text(encoding="utf-8")
    assert "CASE 1: DISCONNECTED GRAPH" in log and "Surjani Town [ISOLATED]" in log
    assert "CASE 2: OVER-DEMAND" in log and "lost to capacity competition" in log
    assert "CASE 3: TOO-HEAVY REQUEST" in log and "EV08" in log and "EV20" in log
    assert "FAIL" not in log


def test_e2_repair_equals_full_kruskal_in_output(outputs):
    assert "Costs equal: yes" in (outputs / "E2_three_road_failure.md").read_text(encoding="utf-8")


def test_e3_removes_top2_and_reruns_both_stages(outputs):
    text = (outputs / "E3_remove_top2.md").read_text(encoding="utf-8")
    assert "Removed sites: Gulshan-e-Iqbal, DHA" in text
    assert "Deactivated stations: ST2" in text and "Gulistan-e-Johar | yes" in text


def test_verification_dp_agrees_with_brute(outputs):
    text = (outputs / "verification.md").read_text(encoding="utf-8")
    assert "40 of 40 agree" in text
