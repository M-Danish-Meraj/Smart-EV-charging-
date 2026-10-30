"""Seeded random instances for tests and the E5 scaling experiment.

Everything here is synthetic. Same seed -> same instance.
"""

import random

from src.io_validate import Dataset, Location, Road


def random_graph(n, seed, extra_per_site=2, unavailable_share=0.05, max_cost=50):
    """A Dataset with n sites and about n - 1 + extra_per_site * n roads.

    A random spanning tree is laid first, then extra random roads are added.
    A small share of roads is marked unavailable, so the active graph may be
    disconnected. Costs are small integers, so many equal-cost ties appear.
    """
    rng = random.Random(seed)
    ids = [f"V{i:03d}" for i in range(1, n + 1)]
    locations = [Location(v, f"Site {v}", rng.uniform(24.8, 25.0), rng.uniform(66.9, 67.3),
                          rng.randint(1, 10), i == 0, True)
                 for i, v in enumerate(ids)]
    pairs = set()
    for i in range(1, n):                          # random spanning tree
        pairs.add(tuple(sorted((ids[i], ids[rng.randrange(i)]))))
    target = len(pairs) + extra_per_site * n
    max_pairs = n * (n - 1) // 2
    while len(pairs) < min(target, max_pairs):     # extra roads
        a, b = rng.sample(ids, 2)
        pairs.add(tuple(sorted((a, b))))
    roads = [Road(f"E{i:04d}", u, v, rng.randint(1, max_cost), rng.random() >= unavailable_share)
             for i, (u, v) in enumerate(sorted(pairs), start=1)]
    rng.shuffle(roads)                             # input order must not matter
    return Dataset(locations, roads, [], [])


def random_knapsack(seed, q_max=8, k_max=3, cap_max=8):
    """(items, capacities) for DP-vs-brute-force checks.

    items: list of (request_id, units, benefit, eligible station indices).
    Includes zero-capacity stations, too-heavy items and items with no
    eligible station, because those are the cases that break naive code.
    """
    rng = random.Random(seed)
    k = rng.randint(1, k_max)
    capacities = [rng.randint(0, cap_max) for _ in range(k)]
    q = rng.randint(0, q_max)
    items = []
    for i in range(q):
        eligible = sorted(j for j in range(k) if rng.random() < 0.7)
        items.append((f"R{i:02d}", rng.randint(1, cap_max + 2), rng.randint(10, 100), eligible))
    return items, capacities
