# report/

| Path | What | Source |
| --- | --- | --- |
| `methods_notes.md` | Pseudocode, proofs, complexity, mapping and trade-off tables (no measured numbers) | written to match `src/` |
| `figures/*.png` | Network maps (E1, E2, E3), benefit by scenario, E5 scaling charts | generated |
| `generated/results_summary.md` | Every table from E1–E5 plus verification | generated |
| `generated/edge_cases.log` | The three CEP-mandatory edge cases with actual output | generated |

To regenerate everything:

```
python run_all.py
python scripts/build_report_assets.py
```

The final report must take every number from `generated/`, and never type numbers by hand. The title page wording ("Information Systems" or "Information Technology") is still to be confirmed against the CEP sheet.
