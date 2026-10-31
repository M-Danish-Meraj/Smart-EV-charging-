# Submission checklist (brief section 12)

Status of every item in the brief's final checklist, with the file that proves it. "Team" items cannot be done in code and need a person.

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Code runs from a clean setup with documented commands | Done | `README.md` setup guide; `python scripts/check_setup.py` |
| 2 | Dataset: 10+ sites, 20+ roads, 20+ requests, labelled synthetic | Done | `data/` (12 / 24 / 24), `data/README.md`, `tests/test_dataset.py` |
| 3 | Kruskal filters unavailable roads, documented tie-break, returns a forest, names components | Done | `src/kruskal.py`, `tests/test_kruskal.py`, report §5.2 and §9.1 |
| 4 | Three-road repair checked against full Kruskal on the same graph | Done | `src/repair.py`, `tests/test_repair.py`, report §9.3 |
| 5 | DP recurrence, base case, units, eligibility, tie-break and complexity match the code | Done | `src/dp.py` docstring, report §3.2, §5.5, §6.5, §7 |
| 6 | DP matches brute force on small instances | Done | `tests/test_brute.py` (151 instances), report §9.7 (200 of 200) |
| 7 | Disconnected, over-demand and too-heavy cases run with output included | Done | `report/generated/edge_cases.log`, report §9.8 and Appendix A |
| 8 | E1 to E5 outputs come from the submitted code | Done | `run_all.py` → `output/results.json` → report and dashboard |
| 9 | Top-2 severity removal reruns both stages | Done | report §9.4, `tests/test_validate_and_run_all.py` |
| 10 | Pseudocode and complexity for every algorithm | Done | report §5 and §7 (A1–A3, B0–B3) |
| 11 | Report has every CEP section, 6+ pages, correct department wording | Done, wording to confirm | `report/CT363_Smart_EV_Report.docx` / `.pdf`; see open item 1 |
| 12 | Faculty signature block and student IDs on the CEP form | Team | Student IDs are on the title page; the signature line is blank for the instructor |

## Open items for the team

1. **Department name.** The brief says the CEP sheet uses "Department of Computer Science and Information Systems", but the proposal's title page says "Computer Science and Information Technology". The CEP sheet itself was not available. Check it, then change `DEPARTMENT` at the top of `scripts/build_report.py` and run `python scripts/build_report.py`.
2. **CEP sheet PDF.** Add it to `docs/` (see `docs/README.md`).
3. **References.** The report lists standard sources (CLRS, Kruskal 1956, Prim 1957, Tarjan 1975, Frederickson 1985, Holm et al. 2001, Martello & Toth 1990, Kellerer et al. 2004, course slides, CEP sheet). The brief requires citing only works the team actually consulted, so remove any you did not use. The Pakistan NEV Policy 2025–30 citation could not be verified and was dropped.
4. **Scenario.** The CEP sheet is flood relief; this project uses EV charging with a mapping table (report Table 1). Confirm with the instructor that this is acceptable.
5. **Submission date.** Not given in any document; confirm it.
6. **Viva preparation.** Every member should be able to explain `src/dsu.py`, `src/kruskal.py`, `src/repair.py` and `src/dp.py` line by line. `report/project_explained.html` is a plain-language walkthrough.
7. **Timings.** Runtime numbers depend on the machine. If you rerun `run_all.py` before submitting, rebuild the report so the text and the tables match.
