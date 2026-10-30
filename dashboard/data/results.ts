// Typed view of data/results.json, the file `python run_all.py` writes to output/.
// No result is typed by hand here: refresh it with `npm run sync-data`.
import raw from "./results.json";

export type Reason =
  | "lost_to_capacity_competition"
  | "too_large_for_any_eligible_station"
  | "no_eligible_station"
  | "origin_site_removed";

export interface Site {
  id: string;
  name: string;
  lat: number;
  lon: number;
  severity: number;
  is_hub: boolean;
}

export interface Road {
  id: string;
  u: string;
  v: string;
  cost: number;
  available: boolean;
}

export interface Station {
  id: string;
  site: string;
  capacity_kwh: number;
  capacity_units: number;
  active: boolean;
}

export interface Component {
  label: string;
  sites: string[];
  has_hub: boolean;
  isolated: boolean;
}

export interface RequestOutcome {
  id: string;
  origin: string;
  kwh: number;
  units: number;
  benefit: number;
  eligible: string[];
  station: string | null;
  reason: Reason | null;
}

export interface Allocation {
  served: number;
  requests_total: number;
  benefit: number;
  units: number;
  kwh: number;
  capacity: number;
  loads: Record<string, { capacity: number; load: number }>;
  unserved_counts: Partial<Record<Reason, number>>;
  dp: { states_per_layer: number; total_states: number; table_bytes: number };
  requests: RequestOutcome[];
}

export interface E1 {
  forest: string[];
  cost: number;
  trace: { road: string; accepted: boolean }[];
  dropped: { road: string; reason: string }[];
  components: Component[];
  allocation: Allocation;
  runtime_ms: { kruskal: number; allocation: number };
  stress: { station: string; allocation: Allocation; runtime_ms: number };
}

export interface E2 {
  cost_before: number;
  failed: {
    road: string;
    role: string;
    action: "replaced" | "split" | "not_in_forest";
    replacement: string | null;
  }[];
  repair_cost: number;
  full_cost: number;
  forest: string[];
  full_forest: string[];
  components: Component[];
  runtime_ms: { repair: number; full: number };
  allocation: Allocation;
}

export interface E3 {
  removed_sites: string[];
  removed_roads: string[];
  deactivated_stations: string[];
  cost: number;
  forest: string[];
  components: Component[];
  allocation: Allocation;
}

export interface E4Scenario {
  label: string;
  capacities: Record<string, number>;
  requests: number;
  served: number;
  unserved: number;
  units: number;
  capacity: number;
  benefit: number;
  lost: string[];
}

export interface E4 {
  cut_percent: number;
  new_requests: { id: string; origin: string; kwh: number; units: number; benefit: number }[];
  scenarios: E4Scenario[];
}

export interface E5 {
  network: {
    n: number;
    m: number;
    components: number;
    kruskal_ms: number;
    repair_ms: number;
    full_ms: number;
    costs_equal: boolean;
  }[];
  dp: {
    n: number;
    q: number;
    k: number;
    states_per_layer: number;
    total_states: number;
    dp_ms: number;
    table_bytes: number;
  }[];
  capacity: {
    factor: number;
    capacities: number[];
    states_per_layer: number;
    dp_ms: number;
    table_bytes: number;
  }[];
  brute: { q: number; checked: number; brute_ms: number; dp_ms: number; same: boolean }[];
}

export interface Results {
  meta: { dataset: string; synthetic: boolean; timing_runs: number; quick: boolean; kwh_per_unit: number };
  sites: Site[];
  roads: Road[];
  stations: Station[];
  e1: E1;
  e2: E2;
  e3: E3;
  e4: E4;
  e5: E5;
  verification: {
    instances: number;
    agree: number;
    greedy: {
      dataset_dp: number;
      dataset_greedy: number;
      random_count: number;
      mean_gap_pct: number;
      max_gap_pct: number;
      optimal_count: number;
    };
  };
  edge_cases_log: string;
}

export const results = raw as unknown as Results;

// ---------- lookups ----------

const siteById = new Map(results.sites.map((s) => [s.id, s]));
const roadById = new Map(results.roads.map((r) => [r.id, r]));
const stationById = new Map(results.stations.map((s) => [s.id, s]));

export const siteName = (id: string) => siteById.get(id)?.name ?? id;
export const road = (id: string) => roadById.get(id)!;
export const roadName = (id: string) => {
  const r = roadById.get(id);
  return r ? `${siteName(r.u)} – ${siteName(r.v)}` : id;
};
export const station = (id: string) => stationById.get(id)!;
export const stationLabel = (id: string) => `${id} (${siteName(station(id).site)})`;

export const REASON_LABEL: Record<Reason, string> = {
  lost_to_capacity_competition: "Capacity competition",
  too_large_for_any_eligible_station: "Too large",
  no_eligible_station: "No eligible station",
  origin_site_removed: "Origin removed",
};
