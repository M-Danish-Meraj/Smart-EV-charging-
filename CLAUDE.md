# CLAUDE.md

Smart EV Charging Station Planning and Energy Allocation System (CT-363 DAA, NED University).
Full spec: `PROJECT_BRIEF.md` (single source of truth; a later chat message from the user wins over it).
The two sections below are copied from the brief.

## How to work (brief section 0)

1. Work one module at a time, in the order of section 9. After each module: write tests, run pytest, show the result, then stop and summarize in 3 lines.
2. Use plan mode before any module bigger than ~100 lines.
3. Algorithms must be written by hand in pure Python (standard library + NumPy for the DP array). Do NOT use networkx, scipy or any library MST/knapsack routine in `src/`. networkx is allowed ONLY inside `tests/` to cross-check Kruskal's total cost.
4. Every number that will appear in the report must be printed by `run_all.py`. Never hardcode result values in docs.
5. Keep code readable and commented with the invariant of each step. The students must be able to explain every line in a viva.
6. Never claim something is done unless the tests or the run output prove it.
7. Do not build the dashboard/API until section 9 step 9 is reached and the user says go.
8. Notation everywhere (code, comments, docs): n sites, m roads, q requests, k stations.
9. Commit small, with clear messages. Do not push if the push is refused; tell the user instead.

## Fixed decisions (brief section 2; do not change without asking the user)

- Language: Python 3.11+. Tests: pytest. Arrays: NumPy. Plots: matplotlib. Timing: time.perf_counter.
- Data: CSV files only, no database.
- Units: 1 energy unit = 10 kWh. Request energy rounds UP, station capacity rounds DOWN.
- Benefits are integers (10 to 100). No floats in DP comparisons.
- Time-decay of benefit is OFF by default (CEP says values are constants).
- Dense DP uses k = 3 stations (stress run k = 4). Report actual state counts.
- Bonus (optional): a greedy benefit-per-unit heuristic as a baseline, reporting the observed gap to DP. Claim no approximation ratio.
- Frontend (later, optional): React + Vite. Backend: FastAPI over the same `src/` package. CORS must be enabled (5173 to 8000).
  - Superseded by the user (2026-10-31): the dashboard is Next.js in `dashboard/`, reading `results.json`; no API server.

## Commands

```
pip install -r requirements.txt
python scripts/gen_dataset.py     # regenerates data/*.csv (deterministic; data is frozen)
python -m pytest -v
python run_all.py                 # E1-E5 + edge cases + figures -> output/
python scripts/build_report_assets.py   # copy generated results into report/ and dashboard/
python scripts/build_report.py          # final report .docx/.html/.pdf from results.json
python scripts/check_setup.py           # verify a fresh clone
```
