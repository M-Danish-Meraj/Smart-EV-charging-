# Karachi-EV-12 dashboard

A dark-mode Next.js (App Router) dashboard for the CT-363 project, built with Tailwind CSS v4, Recharts, framer-motion and lucide-react.

**Data source:** `data/results.json` only. `python run_all.py` writes it to `output/results.json`. No result is typed by hand anywhere in the UI, so the dashboard always shows the latest real run. Timings vary between runs and machines.

```
# from the repo root: regenerate results, then copy them in
python run_all.py
python scripts/build_report_assets.py      # or: npm run sync-data (inside dashboard/)

# inside dashboard/
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
```

| Path | What |
| --- | --- |
| `app/page.tsx` | Main page: KPI header, network, allocation, sensitivity, scaling, edge-case drawer |
| `data/results.ts` | Types for `results.json` plus lookups (site names, stations, reason labels) |
| `components/ui/` | Card, KpiCard, Badge, Tabs, Button, Modal |
| `components/graph/` | NetworkTopologyCanvas (SVG map with E1/E2/E3 modes), ComponentClusterView, KruskalTrace |
| `components/dp/` | AllocationSection (k=3 / stress k=4), AllocationTable with filter chips, StationLoadBar, StateMemoryChart |
| `components/benchmarks/` | ScalingChart, KruskalVsRepairTable, BruteVsDp chart/table, DpScalingTable, Sensitivity chart/table |
| `components/edge/` | EdgeCasesPanel: the three CEP-mandatory cases |
| `components/layout/` | Sidebar with section tracking (top bar on phones) |
