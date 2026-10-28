# PROJECT BRIEF: Smart EV Charging Station Planning and Energy Allocation System

Course: CT-363 Design and Analysis of Algorithms, NED University (Dept. of Computer Science and Information Systems)
Instructor: Miss Tooba Shaikh
Team: Sarim Khan (CT-24266), Muhammad Saraib (CT-24255), Danish Meraj (CT-24268), Muhammad Maaz Ali (CT-24265)
Repo: https://github.com/M-Danish-Meraj/Smart-EV-charging-
Plan start: 2026-10-28. Submission date is NOT given in any document; assume 2026-11-24 and ask the team.

This file is the single source of truth. Read it fully before doing anything. If anything here conflicts with a later chat message from the user, the user wins.

---

## 0. How to work (rules for Claude Code)

1. Work one module at a time, in the order of section 9. After each module: write tests, run pytest, show the result, then stop and summarize in 3 lines.
2. Use plan mode before any module bigger than ~100 lines.
3. Algorithms must be written by hand in pure Python (standard library + NumPy for the DP array). Do NOT use networkx, scipy or any library MST/knapsack routine in `src/`. networkx is allowed ONLY inside `tests/` to cross-check Kruskal's total cost.
4. Every number that will appear in the report must be printed by `run_all.py`. Never hardcode result values in docs.
5. Keep code readable and commented with the invariant of each step. The students must be able to explain every line in a viva.
6. Never claim something is done unless the tests or the run output prove it.
7. Do not build the dashboard/API until section 9 step 9 is reached and the user says go.
8. Notation everywhere (code, comments, docs): n sites, m roads, q requests, k stations.
9. Commit small, with clear messages. Do not push if the push is refused; tell the user instead.

---

## 1. What we are building and how it is graded

One Python system that solves two linked problems on one synthetic Karachi-style dataset:

- Part A (Greedy): Kruskal + DSU gives a minimum spanning forest (MSF) of the road network.
- Part B (Dynamic Programming): exact multi-knapsack DP assigns EV charging requests to stations.
- Link: a request is eligible only for active stations in the same connected component as the request's origin site.

The CEP sheet is a flood-relief scenario; we use EV charging as our own case study. Mapping for the report: village = site, truck = station, relief item = EV request, lives-impacted = benefit, EOC = hub, submerged road = unavailable road.

CEP marks are out of 20:

| Rubric row | Share | Marks | What earns it |
| --- | --- | --- | --- |
| WP5 Extent of code (CLO-2) | 40% | 8 | Correct, tested, efficient code; edge cases pass with printed output; clean pseudocode |
| WP3 Depth of analysis (CLO-3) | 30% | 6 | Greedy-choice and optimal-substructure proofs; DP justification; exact time and space complexity |
| WP2 Conflicting requirements (CLO-3) | 20% | 4 | Trade-off table with justified resolutions |
| WP1 Depth of knowledge (CLO-2) | 10% | 2 | Both problems clearly mapped to the right paradigm with theory |

---

## 2. Fixed decisions (do not change without asking the user)

- Language: Python 3.11+. Tests: pytest. Arrays: NumPy. Plots: matplotlib. Timing: time.perf_counter.
- Data: CSV files only, no database.
- Units: 1 energy unit = 10 kWh. Request energy rounds UP, station capacity rounds DOWN.
- Benefits are integers (10 to 100). No floats in DP comparisons.
- Time-decay of benefit is OFF by default (CEP says values are constants).
- Dense DP uses k = 3 stations (stress run k = 4). Report actual state counts.
- Bonus (optional): a greedy benefit-per-unit heuristic as a baseline, reporting the observed gap to DP. Claim no approximation ratio.
- Frontend (later, optional): React + Vite. Backend: FastAPI over the same `src/` package. CORS must be enabled (5173 to 8000).

---

## 3. Repo layout

```
data/            locations.csv, roads.csv, stations.csv, requests.csv
src/
  dsu.py         union by rank + path compression
  io_validate.py loading + validation
  graph.py       active-graph construction (drops unavailable roads)
  kruskal.py     Kruskal MSF + components with names
  repair.py      incremental repair after road failures
  eligibility.py request -> eligible stations
  dp.py          exact multi-knapsack DP + backtracking
  brute.py       brute-force solver (q <= 10)
  heuristic.py   optional greedy baseline
  validate.py    result validators (see section 7)
tests/           pytest files + edge-case log output
scripts/gen_dataset.py   seeded dataset generator
run_all.py       runs E1..E5, prints and saves every table the report needs
output/          generated results (run_all.py writes here)
docs/            the three original PDFs (CEP sheet, project description, proposal)
report/          report sources and figures
CLAUDE.md        short rules file (copy section 0 and section 2 into it)
PROJECT_BRIEF.md this file
```

---

## 4. Dataset: "Karachi-EV-12" (synthetic, label it synthetic everywhere)

Generated by `scripts/gen_dataset.py` with a fixed seed, then hand-fixed for edge-case rows. Treat the values below as a DRAFT: verify the design properties hold, adjust numbers if needed, and record the final values.

Sites (12):

| ID | Site | Severity | Role |
| --- | --- | --- | --- |
| S01 | Saddar | 6 | Hub. Middle severity so it is NOT in the top-2 removal |
| S02 | Clifton | 8 | Main component, station ST1 |
| S03 | DHA | 9 | Second-highest severity, removed in E3 |
| S04 | PECHS | 7 | Main component |
| S05 | Gulshan-e-Iqbal | 10 | Highest severity, removed in E3, station ST2 |
| S06 | Gulistan-e-Johar | 7 | Main component |
| S07 | North Nazimabad | 6 | Main component |
| S08 | Korangi | 5 | Main component, optional station ST4 in stress run |
| S09 | Malir | 5 | Cut-off component, station ST3 |
| S10 | Airport | 4 | Cut-off component |
| S11 | Landhi | 3 | Cut-off component |
| S12 | Surjani Town | 2 | Isolated (no available road) |

Files and fields:
- locations.csv: location_id, name, latitude, longitude, severity, is_hub, active
- roads.csv: edge_id, u, v, cost, available
- stations.csv: station_id, location_id, capacity_kwh, capacity_units, active
- requests.csv: request_id, origin_id, energy_kwh, units, benefit

Design properties that MUST hold (assert them in a test):
- 24 roads total, 4 flagged unavailable. The unavailable ones are exactly those that would link Malir/Airport/Landhi to the main component, so the baseline has 3 components: main (8 sites), cut-off (3 sites), and Surjani Town alone.
- At least two groups of equal-cost roads (to exercise the tie-break), one triangle of cheap roads (cycle prevention), and at least one unavailable road that is CHEAPER than roads Kruskal selects (so filtering matters).
- Failure experiment roads chosen now and recorded: two roads that are in the baseline forest (one has a replacement edge across its cut, one has none) and one road that is not in the forest.
- Stations (k = 3), distinct capacities. Draft: ST1 Clifton 12 units, ST2 Gulshan 9 units, ST3 Malir 7 units. Dense states = 13 x 10 x 8 = 1,040. Stress run adds ST4 Korangi 5 units: 6,240 states.
- 24 EV requests: about 15 originate in the main component, 7 in the cut-off component, 1 at Surjani Town (no station reachable, so unserviceable). Total demand about 45 units vs 28 capacity (real over-demand).
- One main-component request needs 14 units (more than any station holds: too-heavy case). One cut-off request needs 9 units (more than Malir's 7).
- Unique stable IDs everywhere. Benefits integer, set once, never regenerated.

---

## 5. Part A: Greedy minimum spanning forest

Algorithm: Kruskal with DSU. Justification vs Prim: works on an edge list, returns a forest without restarts, and the DSU directly answers component queries used for eligibility and repair.

Steps:
1. Validate input (reject duplicate IDs, negative costs/capacities, invalid endpoints).
2. Drop every road with available = false BEFORE sorting.
3. Sort by key (cost asc, s(u)+s(v) desc, min(u,v) asc, max(u,v) asc). Severity only breaks ties, so it cannot change the minimum total cost. Say clearly in the report that Kruskal does NOT maximize severity coverage.
4. Scan edges; keep an edge only if FIND(u) != FIND(v), then UNION by rank with path compression.
5. Output forest edges, total cost, and every component by site NAME. Mark the hub's component and list isolated sites by name. Never invent a connection.

Proof outline (for the report; the team must understand it):
- Greedy-choice: when Kruskal adds edge e joining two DSU components, e is the lowest-ranked available edge crossing that cut, so the cut property makes it safe. Exchange argument: any optimal forest without e can swap e in for a no-cheaper edge on the cycle e creates.
- Optimal substructure: after adding a safe edge, contract its endpoints; an optimal forest of the contracted graph plus e is optimal for the original, otherwise a cheaper completion would contradict optimality.
- Disconnected case: same argument inside each component, one minimum tree per component.

Complexity:
- T(n,m) = O(n + m log m + m alpha(n)) = O(m log m). Filtering O(m), sorting O(m log m), DSU O(m alpha(n)) amortized. Space O(n + m). Since m <= n^2, log m = O(log n).

Incremental repair after r = 3 road failures:
1. Remove failed roads from the active set.
2. For each failed road that is in the forest: delete it, find the two cut sides (BFS/DFS on the forest), scan surviving roads for the lowest-ranked one crossing the cut (same sort key), add it; if none exists, keep the split.
3. A failed road not in the forest needs no change.
4. Validate: all edges available, acyclic, every component spanned, total cost equals full Kruskal on the modified graph. Edge sets may differ only on equal-cost ties.
5. Cost O(r(n+m)) = O(n+m). Compare with full Kruskal O(m log m) by MEASURING on generated graphs up to n = 200, 20 repeated runs, report the median. Do NOT assume the repair is faster.

---

## 6. Part B: Exact multi-knapsack DP

Each EV request is one indivisible item assigned to at most one station or skipped (0/1 multiple knapsack). Do NOT run k independent knapsacks (one request could be loaded twice).

Formulation:
- State: DP[i][c1..ck] = best (benefit, requests_served) pair using the first i requests when station j has budget c_j units.
- Base: DP[0][c] = (0, 0) for every capacity vector.
- Transition: skip request i, or assign it to an eligible station j with c_j >= w_i and take b_i + DP[i-1][c with c_j - w_i]. Take the lexicographic maximum of the pair (benefit, served).
- Answer: DP[q][C1..Ck]. Store the decision per state; backtrack from the full capacity vector to print the actual request-to-station assignment.
- Tie rule: higher benefit, then more requests served, then lower station ID. Document it.

Preprocessing and unserved reasons:
1. Convert kWh to units (requests up, capacities down).
2. Build each request's eligible stations from its origin's component.
3. Label BEFORE the DP: `no_eligible_station` (isolated or cut-off with no station) and `too_large_for_any_eligible_station`. Remove those from the DP input.
4. After the DP, any still-unassigned request is `lost_to_capacity_competition`.

Implementation: dense NumPy array of shape (q+1, C1+1, ..., Ck+1) so the code matches the analysis. Same code for the k = 4 stress run; report state counts and memory.

Complexity:
- S = product over j of (C_j + 1). Time O(q k S). Space O(q S) (all layers kept for backtracking). Pseudo-polynomial and exponential in k.
- Brute force: (k+1)^q assignments. For q = 24, k = 3 that is 4^24 ~ 2.8e14, infeasible; for q = 10 it is 4^10 = 1,048,576, which is why brute force only runs for q <= 10.

Why not greedy: with 50 units, a greedy pick of one 50-unit request worth 100 loses to two 20-unit requests worth 60 each (120).

Verification: brute force on 100+ random instances with q <= 10 must match DP's optimal benefit (compare objective and validity, not identical assignments).

---

## 7. Validators (`src/validate.py`, used by every experiment)

Network: forest acyclic; spans every component of the active graph; no unavailable edge selected; total cost recomputed.
Allocation: each request assigned at most once; each station load <= capacity; every assignment is eligible; reconstruction value equals DP value.

---

## 8. Experiments (all produced by `run_all.py`)

| Exp | What changes | Record |
| --- | --- | --- |
| E1 Baseline | Full dataset, 4 roads filtered | Sorted edge trace, forest edges and cost, components by name, per-request assignment or reason, station loads, total energy, total benefit, runtimes, state count |
| E2 Three-road failure | Mark the 3 pre-chosen roads unavailable | Incremental repair vs full Kruskal: validity, cost, edge differences, median runtime over 20 runs |
| E3 Remove top-2 severity | Remove Gulshan-e-Iqbal and DHA, their roads, and the station at Gulshan; rerun BOTH stages | Change in forest, cost, components, eligible stations, requests served/unserved, energy, benefit |
| E4 Capacity and demand | Cut capacities by a stated percentage; add requests with new unique IDs | Benefit, utilization, unserved list vs baseline |
| E5 Scaling | Random graphs of 20, 50, 100, 200 sites; k = 3 and 4 | Kruskal runtime, repair vs recompute, DP state count and time |

E3 discussion: removing a high-severity site can split a component and remove a station, shrinking the eligible set. Report only the model's numbers, no safety claims.

---

## 9. Build order (stop after each step, run tests, summarize)

1. Scaffold repo, `CLAUDE.md` (copy sections 0 and 2), `.gitignore`, `requirements.txt` (numpy, matplotlib, pytest, networkx for tests only), copy PDFs to `docs/` if provided.
2. `scripts/gen_dataset.py` + the four CSVs + a test asserting every design property in section 4. Freeze the data after this step.
3. `dsu.py`, `io_validate.py`, `graph.py`, `kruskal.py` + tests (cycle prevention, equal-cost determinism, unavailable edge never selected, disconnected graph names, cost matches networkx in tests).
4. `eligibility.py`, `dp.py` + tests (duplicate-assignment guard, over-demand, too-heavy request, zero requests / zero capacity).
5. `brute.py` + DP-vs-brute-force agreement test (100+ random instances, q <= 10).
6. `repair.py` + tests (one failed road in the forest and one outside; cost equals full Kruskal).
7. `validate.py` wired into everything; `run_all.py` for E1 to E5 saving tables/figures to `output/`.
8. Edge-case log: run the 3 CEP-mandatory cases (disconnected graph, over-demand, too-heavy item) and save readable output to `output/edge_cases.log`.
9. Only if the user says go: optional heuristic baseline, then FastAPI + React dashboard (static matplotlib charts are an acceptable fallback).
10. Report support: write `report/` figures and a results summary generated from `output/`.

Mandatory tests (CEP requires the first three with printed output):
disconnected graph, over-demand, too-heavy request, unavailable edge, cycle prevention, equal-cost edges, duplicate assignment guard, zero requests / zero capacity, incremental failure.

---

## 10. Report requirements (written by the team, supported by generated output)

Minimum 6 pages (target about 10). Sections: Title page, Abstract, Introduction, Literature Review, Problem Formulation, Block Diagram / Architecture, Methodology + pseudocode for EVERY algorithm (labelled by part), Correctness (proofs), Complexity Analysis, Implementation and dataset, Results, Conclusion and Limitations, References.

- Title page uses "Department of Computer Science and Information Systems" (CEP wording).
- Include the village-to-site mapping table and the conflicting-requirements table (cost vs coverage, capacity vs demand, safety vs cost, decay vs computation, exactness vs scalability).
- References only for works actually consulted: CLRS (MST, disjoint sets, DP), a standard text for multiple knapsack and pseudo-polynomial DP, course slides, the CT-363 CEP sheet. Verify the Pakistan NEV Policy 2025-30 citation or drop it.
- Never present illustrative output as measured results.

---

## 11. Known gaps and decisions already made

- Scenario mismatch (flood relief vs EV): keep EV, confirm with the instructor, include the mapping table.
- Part D bonus (approximation): only the small greedy baseline, no approximation-ratio claim.
- CEP says bounded/multiple knapsack; ours is 0/1 multiple knapsack because each request is one indivisible item. State this explicitly.
- Incremental repair is not guaranteed faster; report measurements honestly.
- Hub must stay out of the top-2 severity removal; say so in the report.
- Submission deadline unknown: ask the team before the schedule matters.

---

## 12. Final checklist

- [ ] Code runs from a clean setup with documented commands
- [ ] Dataset: 10+ sites, 20+ roads, 20+ requests, labelled synthetic
- [ ] Kruskal filters unavailable roads, uses the documented tie-break, returns a forest, names components
- [ ] Three-road repair checked against full Kruskal on the same graph
- [ ] DP recurrence, base case, units, eligibility, tie-break and complexity match the code
- [ ] DP matches brute force on small instances
- [ ] Disconnected, over-demand and too-heavy cases run with output included
- [ ] E1 to E5 outputs come from the submitted code
- [ ] Top-2 severity removal reruns both stages
- [ ] Pseudocode and complexity for every algorithm
- [ ] Report has every CEP section, 6+ pages, correct department wording
- [ ] Faculty signature block and student IDs on the CEP form filled in
