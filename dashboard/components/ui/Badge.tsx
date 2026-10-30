import { CheckCircle2, CircleSlash, Scale, Unplug, Weight } from "lucide-react";
import { REASON_LABEL, type Reason, siteName, station } from "@/data/results";
import { COLOR, STATION_COLOR } from "@/lib/format";

export function Badge({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className="inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-1.5 py-0.5 font-mono text-[11px]"
      style={{ color, borderColor: `${color}55`, background: `${color}14` }}
    >
      {children}
    </span>
  );
}

export function StationBadge({ id }: { id: string }) {
  return (
    <Badge color={STATION_COLOR[id] ?? COLOR.cyan}>
      <CheckCircle2 className="h-3 w-3" aria-hidden />
      {id} · {siteName(station(id).site)}
    </Badge>
  );
}

export const REASON_COLOR: Record<Reason, string> = {
  lost_to_capacity_competition: COLOR.amber,
  too_large_for_any_eligible_station: COLOR.red,
  no_eligible_station: "#FB7185",
  origin_site_removed: COLOR.slate,
};

const REASON_ICON = {
  lost_to_capacity_competition: Scale,
  too_large_for_any_eligible_station: Weight,
  no_eligible_station: Unplug,
  origin_site_removed: CircleSlash,
};

export function ReasonBadge({ reason }: { reason: Reason }) {
  const Icon = REASON_ICON[reason];
  return (
    <Badge color={REASON_COLOR[reason]}>
      <Icon className="h-3 w-3" aria-hidden />
      {REASON_LABEL[reason]}
    </Badge>
  );
}
