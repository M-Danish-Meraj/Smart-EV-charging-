"""Part B (Dynamic Programming): exact 0/1 multiple knapsack with backtracking.

Items are EV requests (indivisible), knapsacks are stations. Each request is
assigned to at most ONE eligible station or skipped.

State   DP[i][c_1..c_k] = best (benefit, served) using requests 1..i when
        station j may still use at most c_j units (a budget, not a load).
Base    DP[0][c] = (0, 0) for every capacity vector c.
Step    DP[i][c] = max( DP[i-1][c],                                  skip i
                        (b_i, 1) + DP[i-1][c with c_j - w_i]         assign i to j
                        for each eligible j with c_j >= w_i )
Answer  DP[q][C_1..C_k]; backtrack the stored decisions from (q, C).

Pairs are compared lexicographically: higher benefit, then more requests
served. At a state, the skip option is checked first and stations in
ascending ID order with a strict ">", so a full tie keeps skip, then the
lowest station ID. Backtracking starts at the LAST request, so when two
requests could swap stations at no difference, the later request is the one
that gets the lower station ID.

To compare a pair with one integer, the table stores
    key = benefit * (q + 1) + served          (0 <= served <= q < q + 1)
so key order == lexicographic (benefit, served) order. All values are
integers; no floats are compared.

Size: S = prod_j (C_j + 1) states per layer, q + 1 layers.
Time O(q k S), space O(q S) (all layers kept for backtracking).
"""

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class DPItem:
    request_id: str
    units: int           # w_i
    benefit: int         # b_i
    stations: list       # eligible station indices (0..k-1)


@dataclass
class DPResult:
    assignment: dict     # request_id -> station index
    total_benefit: int
    served: int
    loads: list          # units used per station
    states_per_layer: int    # S
    total_states: int        # (q + 1) * S
    table_bytes: int


def solve_multi_knapsack(items, capacities):
    q, k = len(items), len(capacities)
    shape = tuple(c + 1 for c in capacities)
    S = math.prod(shape)
    if q == 0 or k == 0:
        # nothing to assign, or nowhere to put it: the empty allocation is optimal
        return DPResult({}, 0, 0, [0] * k, S, (q + 1) * S, 0)

    base = q + 1
    key = np.zeros((q + 1,) + shape, dtype=np.int64)     # key[0] = base case = 0
    choice = np.full((q + 1,) + shape, -1, dtype=np.int8)  # -1 = skip, j = station j

    for i, item in enumerate(items, start=1):
        prev = key[i - 1]
        best = prev.copy()                          # option 1: skip request i
        decision = np.full(shape, -1, dtype=np.int8)
        gain = item.benefit * base + 1              # +b_i benefit and +1 served
        w = item.units
        for j in sorted(item.stations):             # option 2: assign to station j
            if w > capacities[j]:
                continue
            # States with c_j >= w read the previous layer at c_j - w.
            # dst selects c_j in [w, C_j], src selects c_j - w in [0, C_j - w].
            dst = [slice(None)] * k
            src = [slice(None)] * k
            dst[j] = slice(w, capacities[j] + 1)
            src[j] = slice(0, capacities[j] + 1 - w)
            candidate = prev[tuple(src)] + gain
            best_view = best[tuple(dst)]            # views: writes go into best/decision
            decision_view = decision[tuple(dst)]
            better = candidate > best_view          # strict: earlier option wins ties
            best_view[better] = candidate[better]
            decision_view[better] = j
        key[i] = best
        choice[i] = decision

    # Backtrack from the full capacity vector.
    c = list(capacities)
    assignment = {}
    for i in range(q, 0, -1):
        j = int(choice[i][tuple(c)])
        if j >= 0:
            assignment[items[i - 1].request_id] = j
            c[j] -= items[i - 1].units          # move to (i-1, c with c_j - w_i)

    final = int(key[q][tuple(capacities)])
    loads = [capacities[j] - c[j] for j in range(k)]
    return DPResult(assignment, final // base, final % base, loads,
                    S, (q + 1) * S, key.nbytes + choice.nbytes)
