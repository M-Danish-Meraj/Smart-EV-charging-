"""Link between Part A and Part B: which stations may serve each request.

Rule: a request may use an ACTIVE station only if the station's site is in the
same connected component (of the active road graph) as the request's origin.
Requests that can never be served are labelled BEFORE the DP and kept out of it.
"""

from dataclasses import dataclass

NO_ELIGIBLE = "no_eligible_station"
TOO_LARGE = "too_large_for_any_eligible_station"
ORIGIN_REMOVED = "origin_site_removed"
LOST = "lost_to_capacity_competition"     # assigned after the DP, see pipeline


@dataclass
class Eligibility:
    stations: list         # active stations usable by the DP, sorted by ID (k of them)
    eligible: dict         # request_id -> list of eligible station IDs (sorted)
    reasons: dict          # request_id -> pre-DP unserved reason
    dp_requests: list      # requests that go into the DP, in request-ID order


def build_eligibility(requests, stations, component_of):
    """O(q * k). component_of maps every ACTIVE site to its component label."""
    usable = sorted((s for s in stations if s.active and s.location_id in component_of),
                    key=lambda s: s.station_id)
    capacity = {s.station_id: s.capacity_units for s in usable}

    eligible, reasons, dp_requests = {}, {}, []
    for r in sorted(requests, key=lambda r: r.request_id):
        if r.origin_id not in component_of:          # its site was removed (E3)
            eligible[r.request_id] = []
            reasons[r.request_id] = ORIGIN_REMOVED
            continue
        comp = component_of[r.origin_id]
        el = [s.station_id for s in usable if component_of[s.location_id] == comp]
        eligible[r.request_id] = el
        if not el:
            reasons[r.request_id] = NO_ELIGIBLE      # isolated / no station in component
        elif r.units > max(capacity[s] for s in el):
            reasons[r.request_id] = TOO_LARGE        # cannot fit even an empty station
        else:
            dp_requests.append(r)
    return Eligibility(usable, eligible, reasons, dp_requests)
