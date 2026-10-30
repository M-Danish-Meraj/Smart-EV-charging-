import { type Component, type Road, results } from "@/data/results";

export type Scenario = "e1" | "e2" | "e3";

export type RoadStatus = "forest" | "replacement" | "idle" | "unavailable" | "failed" | "removed";

export interface ScenarioView {
  roads: { road: Road; status: RoadStatus }[];
  removedSites: Set<string>;
  activeStations: Set<string>;
  components: Component[];
  componentOf: Map<string, number>;
  cost: number;
}

/** Everything the canvas needs for one scenario, derived from results.json. */
export function scenarioView(s: Scenario): ScenarioView {
  const { e1, e2, e3 } = results;
  const forest = new Set(s === "e1" ? e1.forest : s === "e2" ? e2.forest : e3.forest);
  const failed = new Set(s === "e2" ? e2.failed.map((f) => f.road) : []);
  const replacement = new Set(
    s === "e2" ? e2.failed.flatMap((f) => (f.replacement ? [f.replacement] : [])) : [],
  );
  const removedRoads = new Set(s === "e3" ? e3.removed_roads : []);
  const removedSites = new Set(s === "e3" ? e3.removed_sites : []);
  const deactivated = new Set(s === "e3" ? e3.deactivated_stations : []);
  const components = s === "e1" ? e1.components : s === "e2" ? e2.components : e3.components;

  const roads = results.roads.map((road) => {
    let status: RoadStatus = "idle";
    if (removedRoads.has(road.id)) status = "removed";
    else if (failed.has(road.id)) status = "failed";
    else if (!road.available) status = "unavailable";
    else if (replacement.has(road.id)) status = "replacement";
    else if (forest.has(road.id)) status = "forest";
    return { road, status };
  });

  const componentOf = new Map<string, number>();
  components.forEach((c, i) => c.sites.forEach((site) => componentOf.set(site, i)));

  const activeStations = new Set(
    results.stations.filter((st) => st.active && !deactivated.has(st.id)).map((st) => st.id),
  );
  const cost = s === "e1" ? e1.cost : s === "e2" ? e2.repair_cost : e3.cost;
  return { roads, removedSites, activeStations, components, componentOf, cost };
}

// Component identity colours: hub component is always cyan.
const COMPONENT_PALETTE = ["#A78BFA", "#F472B6", "#60A5FA", "#FBBF24", "#34D399"];

export function componentColor(components: Component[], index: number): string {
  const c = components[index];
  if (!c) return "#475569";
  if (c.has_hub) return "#00F0FF";
  if (c.isolated) return "#64748B";
  const nonHub = components.filter((x) => !x.has_hub && !x.isolated);
  return COMPONENT_PALETTE[nonHub.indexOf(c) % COMPONENT_PALETTE.length];
}
