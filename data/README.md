# Karachi-EV-12 dataset (SYNTHETIC)

The site names are real Karachi areas. Every cost, severity, capacity, demand and benefit is **synthetic** and was invented for this CT-363 study. The coordinates are approximate area centres, used only for plotting.

`scripts/gen_dataset.py` (seed 363) generates the files. Running it again gives byte-identical files, and `tests/test_dataset.py` checks this along with every design property. **The data is frozen**, so do not edit the CSVs by hand.

| File | Rows | Fields |
| --- | --- | --- |
| `locations.csv` | 12 | location_id, name, latitude, longitude, severity, is_hub, active |
| `roads.csv` | 24 (4 unavailable) | edge_id, u, v, cost, available |
| `stations.csv` | 4 (ST4 inactive: stress run only) | station_id, location_id, capacity_kwh, capacity_units, active |
| `requests.csv` | 24 | request_id, origin_id, energy_kwh, units, benefit |
| `e2_failures.csv` | 3 | edge_id, u, v, role (failure roads for E2, chosen up front) |

Units: 1 unit = 10 kWh. Request energy rounds up and station capacity rounds down. Road cost is in synthetic units.

## Design choices
- **Components (baseline):** main = S01–S08, cut-off = Malir/Airport/Landhi, and Surjani Town (no roads at all). The 4 unavailable roads are exactly the main↔cut-off links. One of them (R21 Korangi–Landhi, cost 2) is cheaper than roads Kruskal selects.
- **Cycle and ties:** the cheap triangle Saddar–Clifton–DHA (2, 3, 3) and equal-cost groups at costs 3, 5, 6, 8 and 9. At cost 6, R09 DHA–PECHS and R10 Gulshan–North Nazimabad also tie on severity sum, so the endpoint-ID rule decides.
- **E2 failure roads:** R06 PECHS–Gulshan (in the forest, with a replacement), R20 Airport–Landhi (in the forest, no replacement) and R07 Clifton–PECHS (not in the forest).
- **E3:** Gulistan-e-Johar's only available road goes to Gulshan-e-Iqbal, so removing the top 2 (Gulshan-e-Iqbal 10, DHA 9) also cuts Johar off. The hub, Saddar (6), is not in the top 2.
- **Stations:** ST1 Clifton 125 kWh = 12 units, ST2 Gulshan 95 = 9, ST3 Malir 78 = 7, and ST4 Korangi 54 = 5 (inactive). That gives dense states of 1,040 (k = 3) or 6,240 (k = 4).
- **Edge-case requests:** EV08 (PECHS, 135 kWh = 14 units, more than any station), EV20 (Airport, 85 kWh = 9 units, more than Malir's 7) and EV24 (Surjani Town, no reachable station). The other requests draw 11–30 kWh (2–3 units) and a benefit of 10–100 from the seeded RNG.

## Changes from the brief's draft
- **Total demand:** the draft's "about 45 units" was not real over-demand. After taking out the 14-unit, 9-unit and Surjani requests, only about 20 feasible units would compete for 28 units of capacity. Every feasible request now needs at least 2 units, so feasible demand is guaranteed to exceed capacity in both the main and cut-off components. The test computes the actual totals.
- **Request split:** 16 main, 7 cut-off, 1 isolated, which makes 24. The draft said "about 15" for main.
