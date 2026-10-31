# Smart EV Charging Station Planning and Energy Allocation System

CT-363 Design and Analysis of Algorithms, NED University. Team: Sarim Khan (CT-24266), Muhammad Saraib (CT-24255), Danish Meraj (CT-24268), Muhammad Maaz Ali (CT-24265). Instructor: Miss Tooba Shaikh.

The system solves two linked problems on one **synthetic** Karachi road network (Karachi-EV-12):

- **Part A (Greedy):** Kruskal + Union-Find builds a minimum spanning forest over the available roads. A three-road failure is repaired incrementally and checked against full Kruskal.
- **Part B (Dynamic Programming):** an exact 0/1 multiple-knapsack DP assigns EV charging requests to stations, maximising benefit within each station's capacity.
- **Link:** a request may use only stations in the same connected component as its origin.

## Deliverables

| What | Where |
| --- | --- |
| Final report (editable Word file) | [`report/CT363_Smart_EV_Report.docx`](report/CT363_Smart_EV_Report.docx) |
| Final report (PDF) | [`report/CT363_Smart_EV_Report.pdf`](report/CT363_Smart_EV_Report.pdf) |
| Plain-language explainer (open in a browser) | [`report/project_explained.html`](report/project_explained.html) |
| All generated tables, edge-case log, figures | `report/generated/`, `report/figures/` |
| Interactive dashboard | `dashboard/` (see below) |
| Submission checklist and open items | [`report/SUBMISSION_CHECKLIST.md`](report/SUBMISSION_CHECKLIST.md) |

---

## Setup for teammates (after cloning)

### What you need installed

| Tool | Version | Needed for |
| --- | --- | --- |
| Git | any | cloning |
| Python | **3.11 or newer** (tested on 3.14) | everything: algorithms, tests, experiments, report |
| Node.js + npm | **20 or newer** (tested on 24) | only the dashboard |
| Microsoft Edge or Google Chrome | any recent | only to re-export the report as PDF |

No database and no internet services are needed. All data are CSV files in `data/`.

### 1. Clone

```
git clone https://github.com/M-Danish-Meraj/Smart-EV-charging-.git
cd Smart-EV-charging-
```

### 2. Create a virtual environment and install Python packages

Windows (PowerShell):

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again (or use Command Prompt with `.venv\Scripts\activate.bat`).

macOS / Linux:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Check the setup

```
python scripts/check_setup.py
```

It lists anything missing and how to fix it.

### 4. Run the tests

```
python -m pytest
```

All tests should pass (about 340 tests, a few seconds).

### 5. Run every experiment and rebuild the report

```
python run_all.py                       # E1-E5, verification, edge cases, figures -> output/
python scripts/build_report_assets.py   # copy figures + results into report/ and dashboard/
python scripts/build_report.py          # report/CT363_Smart_EV_Report.docx, .html and .pdf
```

Every number in the report and the dashboard comes from `output/results.json`, which `run_all.py` writes. Timings change slightly between machines and runs; costs, counts and benefits are always the same.

### 6. Start the dashboard (optional)

```
npm --prefix dashboard install
npm --prefix dashboard run dev
```

Open http://localhost:3000. The dashboard reads `dashboard/data/results.json`, which step 5 refreshes. To make a production build instead: `npm --prefix dashboard run build`, then `npm --prefix dashboard start`.

### Troubleshooting

| Problem | Fix |
| --- | --- |
| `ModuleNotFoundError` (numpy, docx, ...) | Activate the virtual environment, then `pip install -r requirements.txt`. |
| `python` not found on macOS/Linux | Use `python3`. |
| Port 3000 already in use | `npm --prefix dashboard run dev -- -p 3001`, then open http://localhost:3001. |
| PDF not produced by `build_report.py` | Install Edge or Chrome, or open the `.docx` in Word and use *Save as PDF*. |
| Word shows "update the fields?" when opening the report | Click *Yes*; it fills in the table of contents page numbers. |
| `test_generator_is_deterministic` fails after editing data | The dataset is frozen. Revert `data/` with `git checkout -- data`. |

---

## Repository layout

| Path | Contents |
| --- | --- |
| `data/` | Karachi-EV-12 dataset (12 sites, 24 roads, 4 stations, 24 requests) and the E2 failure roads. See `data/README.md` |
| `src/dsu.py`, `graph.py`, `kruskal.py` | Union-Find, active graph and edge order, Kruskal MSF |
| `src/repair.py` | Incremental repair after road failures |
| `src/eligibility.py`, `dp.py` | Component-based eligibility, exact multi-knapsack DP with backtracking |
| `src/brute.py`, `heuristic.py` | Brute-force checker (q ≤ 10), optional greedy baseline |
| `src/validate.py`, `pipeline.py` | Result validators and the glue that runs both stages |
| `run_all.py` | All experiments; every reported number comes from here |
| `scripts/` | Dataset generator, report builder, asset copier, setup checker |
| `tests/` | pytest suite (networkx is used here only, as a cross-check) |
| `report/` | Final report, methods notes, generated figures and results, explainer page |
| `dashboard/` | Next.js dashboard over `results.json` (see `dashboard/README.md`) |
| `docs/` | Original project description and proposal PDFs |
| `PROJECT_BRIEF.md`, `CLAUDE.md` | Project specification and working rules |

All algorithms are written by hand in pure Python (NumPy only for the DP table).
