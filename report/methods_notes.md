# Methods notes for the report (no measured numbers here)

This file holds the pseudocode, proofs and complexity of every algorithm, written to match the code in `src/`. The team writes the final report from it. **Every result number must come from `report/generated/results_summary.md`**, which `run_all.py` generates. Notation throughout: n sites, m roads, q requests, k stations.

## Mapping the CEP scenario to our case study

| CEP (flood relief) | This project (EV charging) |
| --- | --- |
| village | site (candidate charging location) |
| road / submerged road | road / unavailable road |
| EOC (emergency operations centre) | hub (Saddar) |
| truck | station |
| relief item | EV charging request |
| lives impacted | benefit |
| bounded/multiple knapsack | **0/1** multiple knapsack (each request is one indivisible item) |

## Part A: Kruskal minimum spanning forest (`src/kruskal.py`, `src/dsu.py`)

```
KRUSKAL-MSF(V, E):
    A <- { e in E : e.available }                          O(m)
    sort A by (cost asc, s(u)+s(v) desc, min(u,v), max(u,v))   O(m log m)
    for v in V: MAKE-SET(v)                                O(n)
    F <- empty
    for (u, v, cost) in A:                                 m iterations
        if FIND(u) != FIND(v):                             O(alpha(n)) amortized
            F <- F + {(u, v)};  UNION(u, v)
    return F, components of the DSU
```
- **Invariant:** F is acyclic, and each DSU set equals the vertex set of one tree of F.
- **Greedy choice (cut property):** when Kruskal accepts e = (u, v), u and v lie in different DSU sets. Let C be u's set, which defines the cut (C, V minus C). Every road ranked before e that crosses this cut was already scanned. Such a road would have joined two different sets and been accepted, which would contradict u and v still being apart. So e is the lowest-ranked road crossing the cut. Exchange argument: take any optimal forest T* that does not contain e. Adding e to T* creates a cycle, and that cycle crosses the cut at some other road f with cost(f) >= cost(e). Then T* - f + e is a spanning forest that costs no more, so it is also optimal and contains e.
- **Optimal substructure:** contract e. An optimal forest of the contracted graph plus e is optimal for the original graph. If a cheaper completion existed, adding e to it would beat the optimum.
- **Disconnected graph:** the same argument holds inside each component. The result is one minimum tree per component (a forest with n - c roads for c components). The algorithm never adds a road between components, because no available road exists there.
- **Severity** only breaks ties among equal costs, so it never changes the minimum total cost. Kruskal does **not** maximise severity coverage.
- **Complexity:** T = O(m) + O(m log m) + O(n) + O(m alpha(n)) = **O(m log m)**, and log m = O(log n) because m <= n^2. Space is **O(n + m)**.
- **Why not Prim:** Kruskal works directly on the edge list and returns a forest without restarting per component. Its DSU also answers "same component?" for eligibility.

## Incremental repair after r road failures (`src/repair.py`)

```
REPAIR(F, E_active, failed):
    S <- E_active minus failed
    for e = (u, v) in failed:
        if e not in F: continue
        F <- F - {e}
        C1 <- BFS(u, F);  C2 <- BFS(v, F)                O(n)
        best <- lowest-ranked road of S with one end in C1, the other in C2    O(m)
        if best exists: F <- F + {best}   else: keep the split
    return F
```
- **Correctness:** deleting e splits one tree into C1 and C2. Every other road of F stays inside C1 or C2, so it remains part of an optimal forest. By the cut property, the cheapest surviving road across (C1, C2) is a safe replacement. If no road crosses the cut, the component really did split. Other failed forest roads never cross this cut, so it is safe to exclude them up front.
- **Complexity:** O(r(n + m)). With r = 3 this is O(n + m). It is a simple repair, not a dynamic-MST structure, so its speed is **measured** in E2/E5, not assumed.
- **Validation:** all roads are available, the forest is acyclic, it spans every component, and its cost equals full Kruskal on the same modified graph. The edge sets may differ only on equal-cost ties.

## Link between the parts: eligibility (`src/eligibility.py`)

A request may use an active station only if the station is in the same component as the request's origin. These labels are applied **before** the DP: `no_eligible_station`, `too_large_for_any_eligible_station`, and `origin_site_removed` (E3 only). After the DP, every remaining unassigned request gets `lost_to_capacity_competition`. Cost: O(q k).

## Part B: exact 0/1 multiple knapsack DP (`src/dp.py`)

Model: maximise sum_i sum_j b_i x_ij subject to sum_j x_ij <= 1 for every request i, sum_i w_i x_ij <= C_j for every station j, x_ij = 0 when j is not eligible for i, and x_ij in {0, 1}.

```
MULTI-KNAPSACK-DP(items, C[1..k]):
    DP[0][c] <- (0, 0) for every capacity vector c
    for i = 1..q:
        for every c:
            DP[i][c] <- DP[i-1][c];  choice[i][c] <- SKIP
            for each eligible j (ascending ID) with c_j >= w_i:
                cand <- (b_i, 1) + DP[i-1][c with c_j - w_i]
                if cand > DP[i][c]: DP[i][c] <- cand; choice[i][c] <- j
    c <- C
    for i = q..1:                         # backtrack
        if choice[i][c] = j: assign i to j; c_j <- c_j - w_i
    return DP[q][C], assignment
```
- **State meaning:** c_j is the remaining *budget* of station j, not its load.
- **Optimal substructure:** in an optimal solution for (i, c), request i is either skipped or placed in exactly one eligible station j. Removing it leaves a solution for (i-1, c) or (i-1, c - w_i e_j). That remainder must be optimal, or swapping in a better one would improve (i, c). The recurrence tries every case, so DP[i][c] is optimal.
- **No duplicate assignment:** each request is decided exactly once (one layer), and the decision is skip or a single station j. That is why we do **not** run k separate knapsacks, which could place the same request in two stations.
- **Ties:** the pair (benefit, served) is compared lexicographically, and at each state the skip option is checked first, then stations in ascending ID order. The code encodes the pair as the single integer benefit·(q+1)+served, so no floats are ever compared.
- **Why not greedy:** with 50 units, greedy takes one 50-unit request worth 100, but two 20-unit requests worth 60 each give 120. `heuristic.py` measures the actual gap.
- **Complexity:** S = prod_j (C_j + 1). Time is **O(q k S)** and space is **O(q S)**, since every layer is kept for backtracking. This is pseudo-polynomial (it depends on the capacity values) and exponential in k, which is why the dense DP uses k = 3, with k = 4 only for the stress run.
- **Brute force:** at most (k+1)^q assignments, each checked in O(q + k). It is used only for q <= 10, where the agreement test compares objective and validity, not the exact assignment.

## Conflicting requirements (decisions)

| Conflict | Resolution |
| --- | --- |
| Connection cost vs coverage | Kruskal minimises cost only. We report components and membership and never claim maximum coverage. |
| Safety vs low cost | Unavailable roads are a hard filter applied before sorting, so a cheaper unavailable road is never selected. |
| Capacity vs demand | Station capacities are hard constraints. The DP maximises benefit, and every unserved request has a stated reason. Fairness is not guaranteed. |
| Time-decay vs computation | Decay is off (the CEP says benefit values are constants). If it were on, b_i would be fixed per run so the DP stays exact. |
| Exactness vs scalability | Exact dense DP with k = 3 (stress k = 4) and 10 kWh units. E5 reports the state growth. |

## Limitations
The data is synthetic. The MST minimises connection cost only, not travel time, safety or coverage. Benefit scores encode the designers' priorities. Rounding to 10 kWh units can change feasibility. Requests are indivisible. k is limited by the DP state space. Queues, charger power, prices and grid limits are not modelled.
