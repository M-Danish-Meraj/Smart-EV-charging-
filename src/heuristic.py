"""Optional bonus: greedy benefit-per-unit baseline for the allocation.

Sort requests by benefit / units (descending, compared exactly with
Fraction, no floats), then give each request to the eligible station with the
most remaining capacity that still fits it (ties: lower station index).
O(q log q + q k). It is NOT optimal; run_all.py reports the observed gap to
the DP. No approximation ratio is claimed.
"""

from fractions import Fraction


def greedy_allocate(items, capacities):
    remaining = list(capacities)
    order = sorted(items, key=lambda it: (-Fraction(it.benefit, max(it.units, 1)), it.request_id))
    assignment, benefit = {}, 0
    for it in order:
        fits = [j for j in sorted(it.stations) if it.units <= remaining[j]]
        if not fits:
            continue
        j = max(fits, key=lambda s: (remaining[s], -s))
        remaining[j] -= it.units
        assignment[it.request_id] = j
        benefit += it.benefit
    return assignment, benefit
