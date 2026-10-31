"""Check that a fresh clone is ready to run. Prints what is missing and how to fix it.

    python scripts/check_setup.py
"""

import importlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ok = True


def report(passed, label, fix=""):
    global ok
    print(f"  [{'OK' if passed else 'MISSING'}] {label}" + ("" if passed else f"  ->  {fix}"))
    ok = ok and passed


print("Python")
report(sys.version_info >= (3, 11), f"Python {sys.version.split()[0]} (need 3.11+)",
       "install Python 3.11 or newer from python.org")

print("Python packages")
for module, pip_name in [("numpy", "numpy"), ("matplotlib", "matplotlib"), ("pytest", "pytest"),
                         ("networkx", "networkx"), ("docx", "python-docx")]:
    try:
        mod = importlib.import_module(module)
        report(True, f"{pip_name} {getattr(mod, '__version__', '')}".strip())
    except ImportError:
        report(False, pip_name, "pip install -r requirements.txt")

print("Project files")
for rel in ["data/locations.csv", "data/roads.csv", "data/stations.csv", "data/requests.csv",
            "data/e2_failures.csv", "dashboard/data/results.json"]:
    report((ROOT / rel).exists(), rel, "re-clone the repository (this file is committed)")

print("Optional: dashboard (Node.js 20+)")
node = shutil.which("node")
if node:
    ver = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    major = int(ver.lstrip("v").split(".")[0]) if ver.startswith("v") else 0
    print(f"  [{'OK' if major >= 20 else 'OLD'}] node {ver}" + ("" if major >= 20 else "  ->  install Node.js 20 or newer"))
    installed = (ROOT / "dashboard" / "node_modules").exists()
    print(f"  [{'OK' if installed else 'TODO'}] dashboard packages"
          + ("" if installed else "  ->  npm --prefix dashboard install"))
else:
    print("  [SKIP] node not found  ->  install Node.js 20+ from nodejs.org (only needed for the dashboard)")

print("Optional: PDF export of the report (Edge or Chrome)")
sys.path.insert(0, str(ROOT / "scripts"))
from build_report import find_browser  # noqa: E402

b = find_browser()
print(f"  [{'OK' if b else 'SKIP'}] " + (b if b else "no Edge/Chrome found; the .docx and .html are still built"))

print()
print("Ready. Next: python -m pytest" if ok else "Fix the MISSING items above, then run this again.")
sys.exit(0 if ok else 1)
