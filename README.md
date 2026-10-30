# Smart EV Charging Station Planning and Energy Allocation System

CT-363 Design and Analysis of Algorithms, NED University. Team: Sarim Khan (CT-24266), Muhammad Saraib (CT-24255), Danish Meraj (CT-24268), Muhammad Maaz Ali (CT-24265). Instructor: Miss Tooba Shaikh.

The system solves two linked problems on one **synthetic** Karachi road network:

- **Part A (Greedy):** Kruskal + Union-Find builds a minimum spanning forest over the available roads. A three-road failure is repaired incrementally and checked against full Kruskal.
- **Part B (Dynamic Programming):** an exact 0/1 multiple-knapsack DP assigns EV charging requests to stations, maximising benefit within each station's capacity.
- **Link:** a request may use only stations in the same connected component as its origin.

## Run it

```
pip install -r requirements.txt
python -m pytest            # all tests
python run_all.py           # E1-E5, verification, edge cases, figures -> output/
python scripts/build_report_assets.py   # copy figures + results into report/ and dashboard/
npm --prefix dashboard install
npm --prefix dashboard run dev          # dashboard at http://localhost:3000
```

## Layout

| Path | Contents |
| --- | --- |
| `data/` | Karachi-EV-12 dataset (12 sites, 24 roads, 4 stations, 24 requests) and the E2 failure roads. See `data/README.md` |
| `src/dsu.py`, `graph.py`, `kruskal.py` | Union-Find, active graph and edge order, Kruskal MSF |
| `src/repair.py` | incremental repair after road failures |
| `src/eligibility.py`, `dp.py` | component-based eligibility, exact multi-knapsack DP with backtracking |
| `src/brute.py`, `heuristic.py` | brute-force checker (q <= 10), optional greedy baseline |
| `src/validate.py`, `pipeline.py` | result validators, and the glue that runs both stages |
| `run_all.py` | all experiments; every reported number comes from here |
| `report/` | methods notes (pseudocode, proofs, complexity) and generated figures/results |
| `dashboard/` | Next.js dashboard over `output/results.json` (see `dashboard/README.md`) |
| `docs/` | original project description and proposal PDFs |

All algorithms are written by hand in pure Python (NumPy only for the DP table). networkx appears only in `tests/`, as an independent cross-check.
