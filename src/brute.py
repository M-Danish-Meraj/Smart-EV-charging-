"""Brute-force baseline for the multi-knapsack allocation (small q only).

Each request has (1 + its eligible stations) options, so at most (k+1)^q
assignments are enumerated; each is checked in O(q + k).
Time O((k+1)^q * (q + k)). For q = 10, k = 3 that is 4^10 = 1,048,576.
Same objective and same eligibility as the DP: maximise (benefit, served).
"""

from dataclasses import dataclass
from itertools import product

SKIP = -1
MAX_Q = 10


@dataclass
class BruteResult:
    assignment: dict      # request_id -> station index
    total_benefit: int
    served: int
    checked: int          # assignments enumerated


def brute_force(items, capacities, max_q=MAX_Q):
    if len(items) > max_q:
        raise ValueError(f"brute force is only for q <= {max_q} (got {len(items)})")
    options = [[SKIP] + sorted(it.stations) for it in items]
    best_key, best = (0, 0), {}
    checked = 0
    for combo in product(*options):        # every way to place every request
        checked += 1
        loads = [0] * len(capacities)
        benefit = served = 0
        for it, j in zip(items, combo):
            if j != SKIP:
                loads[j] += it.units
                benefit += it.benefit
                served += 1
        if any(l > c for l, c in zip(loads, capacities)):
            continue                        # violates a station capacity
        if (benefit, served) > best_key:
            best_key = (benefit, served)
            best = {it.request_id: j for it, j in zip(items, combo) if j != SKIP}
    return BruteResult(best, best_key[0], best_key[1], checked)
