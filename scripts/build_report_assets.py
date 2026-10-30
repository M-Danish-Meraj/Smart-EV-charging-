"""Copy the generated results into report/ so the report never hand-types a number.

    python run_all.py
    python scripts/build_report_assets.py

Copies output/figures/*.png -> report/figures/, and output/results_summary.md
and output/edge_cases.log -> report/generated/, and output/results.json ->
dashboard/data/results.json (the dashboard's only data source). Refuses to run if output/ is
missing, so stale or illustrative numbers cannot end up in the report.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "output"
    needed = [out / "results_summary.md", out / "edge_cases.log", out / "figures"]
    missing = [str(p) for p in needed if not p.exists()]
    if missing:
        sys.exit(f"run `python run_all.py` first; missing: {', '.join(missing)}")

    figs = ROOT / "report" / "figures"
    gen = ROOT / "report" / "generated"
    figs.mkdir(parents=True, exist_ok=True)
    gen.mkdir(parents=True, exist_ok=True)
    for png in sorted((out / "figures").glob("*.png")):
        shutil.copy2(png, figs / png.name)
        print("figure  ", png.name)
    for name in ["results_summary.md", "edge_cases.log"]:
        shutil.copy2(out / name, gen / name)
        print("results ", name)
    dash = ROOT / "dashboard" / "data"
    if (out / "results.json").exists() and dash.parent.exists():
        dash.mkdir(exist_ok=True)
        shutil.copy2(out / "results.json", dash / "results.json")
        print("dashboard results.json")


if __name__ == "__main__":
    main()
