"""Step 5: DP must agree with brute force on 150 random small instances.

We compare the objective (benefit, served) and the validity of both
assignments, not the assignments themselves (ties may differ).
"""

import random

import pytest

from src.brute import brute_force
from src.dp import DPItem, solve_multi_knapsack
from src.random_instances import random_knapsack
from src.validate import check_allocation


def to_items(raw):
    return [DPItem(rid, w, b, el) for rid, w, b, el in raw]


def assert_valid(assignment, items, capacities, benefit):
    check_allocation(
        sorted(assignment.items()),
        {it.request_id: (it.units, it.benefit) for it in items},
        dict(enumerate(capacities)),
        {it.request_id: it.stations for it in items},
        benefit)


@pytest.mark.parametrize("seed", range(150))
def test_dp_matches_brute_force(seed):
    raw, caps = random_knapsack(seed, q_max=8, k_max=3, cap_max=8)
    items = to_items(raw)
    dp = solve_multi_knapsack(items, caps)
    bf = brute_force(items, caps)
    assert (dp.total_benefit, dp.served) == (bf.total_benefit, bf.served)
    assert_valid(dp.assignment, items, caps, dp.total_benefit)
    assert_valid(bf.assignment, items, caps, bf.total_benefit)


def test_dp_matches_brute_force_at_q10():
    # largest size brute force allows: q = 10, k = 3 -> 4^10 = 1,048,576 assignments
    rng = random.Random(2024)
    caps = [rng.randint(4, 10) for _ in range(3)]
    items = [DPItem(f"R{i:02d}", rng.randint(1, 6), rng.randint(10, 100),
                    sorted(rng.sample(range(3), rng.randint(1, 3)))) for i in range(10)]
    dp = solve_multi_knapsack(items, caps)
    bf = brute_force(items, caps)
    assert (dp.total_benefit, dp.served) == (bf.total_benefit, bf.served)


def test_brute_force_refuses_large_q():
    items = [DPItem(f"R{i}", 1, 10, [0]) for i in range(11)]
    with pytest.raises(ValueError):
        brute_force(items, [5])
