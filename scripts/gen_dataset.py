"""Generate the synthetic "Karachi-EV-12" dataset.

All values are SYNTHETIC. Site names are real Karachi areas, but costs,
severities, capacities, demands and benefits are invented for the study.

Sites, roads and stations are fixed design tables (chosen by hand so the
design properties in PROJECT_BRIEF.md section 4 hold). Request energies and
benefits are drawn from a seeded RNG; the edge-case requests are fixed rows.
Running the script twice gives byte-identical files.

Usage:  python scripts/gen_dataset.py [out_dir]     (default: data/)
"""

import csv
import math
import random
import sys
from pathlib import Path

SEED = 363            # course code; never change once the data is frozen
KWH_PER_UNIT = 10     # 1 energy unit = 10 kWh

# location_id, name, latitude, longitude, severity, is_hub
# Coordinates are approximate area centres, for plotting only.
LOCATIONS = [
    ("S01", "Saddar",           24.8556, 67.0300,  6, True),
    ("S02", "Clifton",          24.8138, 67.0300,  8, False),
    ("S03", "DHA",              24.7950, 67.0650,  9, False),
    ("S04", "PECHS",            24.8700, 67.0600,  7, False),
    ("S05", "Gulshan-e-Iqbal",  24.9200, 67.0950, 10, False),
    ("S06", "Gulistan-e-Johar", 24.9180, 67.1350,  7, False),
    ("S07", "North Nazimabad",  24.9420, 67.0400,  6, False),
    ("S08", "Korangi",          24.8300, 67.1300,  5, False),
    ("S09", "Malir",            24.8950, 67.2000,  5, False),
    ("S10", "Airport",          24.9000, 67.1650,  4, False),
    ("S11", "Landhi",           24.8450, 67.2050,  3, False),
    ("S12", "Surjani Town",     25.0300, 67.0550,  2, False),
]

# u, v, cost, available   (cost in synthetic units, e.g. million PKR)
ROADS = [
    # main component (S01..S08): 18 available roads
    ("S02", "S03", 2, True),   # cheap triangle S01-S02-S03 ...
    ("S01", "S03", 3, True),   # ... equal-cost group at 3 (tie broken by severity)
    ("S01", "S02", 3, True),   # ... closes the triangle: rejected as a cycle
    ("S05", "S06", 4, True),   # Johar's only available road (E3 isolates Johar)
    ("S01", "S04", 4, True),
    ("S04", "S05", 5, True),   # E2: forest road WITH a replacement (S04-S07)
    ("S02", "S04", 5, True),   # E2: road NOT in the forest
    ("S03", "S08", 5, True),
    ("S03", "S04", 6, True),   # equal-cost group at 6 with equal severity sum:
    ("S05", "S07", 6, True),   #   S03-S04 and S05-S07 both 16, ID decides
    ("S04", "S07", 6, True),
    ("S01", "S05", 7, True),
    ("S04", "S08", 7, True),
    ("S01", "S07", 8, True),
    ("S05", "S08", 8, True),
    ("S03", "S05", 8, True),
    ("S02", "S08", 9, True),
    ("S01", "S08", 9, True),
    # cut-off component (S09..S11): 2 available roads
    ("S09", "S10", 3, True),
    ("S10", "S11", 4, True),   # E2: forest road with NO replacement
    # unavailable roads: exactly the links between cut-off and main
    ("S08", "S11", 2, False),  # cheaper than roads Kruskal selects
    ("S08", "S09", 3, False),
    ("S05", "S10", 6, False),
    ("S06", "S09", 7, False),
]

# station_id, location_id, capacity_kwh, active
# kWh values are not multiples of 10 so the round-DOWN rule is exercised.
STATIONS = [
    ("ST1", "S02", 125, True),   # 12 units
    ("ST2", "S05",  95, True),   #  9 units
    ("ST3", "S09",  78, True),   #  7 units
    ("ST4", "S08",  54, False),  #  5 units, k = 4 stress run only
]

# Request origins in ID order. 16 main, 7 cut-off, 1 isolated.
REQUEST_ORIGINS = (
    ["S01", "S01", "S02", "S02", "S03", "S03", "S04", "S04",
     "S05", "S05", "S06", "S06", "S07", "S07", "S08", "S08"]
    + ["S09", "S09", "S09", "S10", "S10", "S11", "S11"]
    + ["S12"]
)
# Hand-fixed edge-case rows: request_id -> (energy_kwh, benefit)
FIXED_REQUESTS = {
    "EV08": (135, 90),   # main, 14 units > every station (too heavy)
    "EV20": (85, 80),    # cut-off, 9 units > Malir's 7 (too heavy)
    "EV24": (20, 70),    # Surjani Town: no reachable station
}


def request_units(kwh):
    """Requests round UP to whole units."""
    return math.ceil(kwh / KWH_PER_UNIT)


def station_units(kwh):
    """Capacities round DOWN to whole units."""
    return kwh // KWH_PER_UNIT


def build_requests():
    rng = random.Random(SEED)
    rows = []
    for idx, origin in enumerate(REQUEST_ORIGINS, start=1):
        rid = f"EV{idx:02d}"
        # Draw for every row (even fixed ones) so a fixed row never shifts
        # the random values of later rows. 11..30 kWh = 2..3 units, so the
        # 15 feasible main requests need >= 30 units (> 21) and the 6
        # feasible cut-off requests need >= 12 units (> 7): real over-demand.
        kwh = rng.randint(11, 30)
        benefit = rng.randint(10, 100)
        if rid in FIXED_REQUESTS:
            kwh, benefit = FIXED_REQUESTS[rid]
        rows.append((rid, origin, kwh, request_units(kwh), benefit))
    return rows


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def flag(b):
    return "true" if b else "false"


def main(out_dir="data"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    write_csv(out / "locations.csv",
              ["location_id", "name", "latitude", "longitude", "severity", "is_hub", "active"],
              [(i, n, f"{lat:.4f}", f"{lon:.4f}", s, flag(h), "true")
               for i, n, lat, lon, s, h in LOCATIONS])

    write_csv(out / "roads.csv",
              ["edge_id", "u", "v", "cost", "available"],
              [(f"R{i:02d}", u, v, c, flag(a))
               for i, (u, v, c, a) in enumerate(ROADS, start=1)])

    write_csv(out / "stations.csv",
              ["station_id", "location_id", "capacity_kwh", "capacity_units", "active"],
              [(s, loc, kwh, station_units(kwh), flag(a)) for s, loc, kwh, a in STATIONS])

    write_csv(out / "requests.csv",
              ["request_id", "origin_id", "energy_kwh", "units", "benefit"],
              build_requests())

    # E2 failure roads, chosen before any experiment runs.
    edge_id = {(u, v): f"R{i:02d}" for i, (u, v, _, _) in enumerate(ROADS, start=1)}
    write_csv(out / "e2_failures.csv",
              ["edge_id", "u", "v", "role"],
              [(edge_id[("S04", "S05")], "S04", "S05", "in_forest_with_replacement"),
               (edge_id[("S10", "S11")], "S10", "S11", "in_forest_no_replacement"),
               (edge_id[("S02", "S04")], "S02", "S04", "not_in_forest")])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
