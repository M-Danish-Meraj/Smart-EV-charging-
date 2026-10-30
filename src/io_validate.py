"""Load the four dataset CSV files into typed records and validate them.

Validation rejects: duplicate IDs, negative costs / capacities / energy /
benefit, roads with unknown or identical endpoints, stations or requests at
unknown sites, unit values that break the rounding rule, and malformed values.
"""

import csv
import math
from dataclasses import dataclass
from pathlib import Path

KWH_PER_UNIT = 10   # 1 energy unit = 10 kWh


class DataError(ValueError):
    """Raised when input data is malformed or violates a rule."""


@dataclass(frozen=True)
class Location:
    location_id: str
    name: str
    latitude: float
    longitude: float
    severity: int
    is_hub: bool
    active: bool


@dataclass(frozen=True)
class Road:
    edge_id: str
    u: str
    v: str
    cost: int
    available: bool


@dataclass(frozen=True)
class Station:
    station_id: str
    location_id: str
    capacity_kwh: int
    capacity_units: int
    active: bool


@dataclass(frozen=True)
class Request:
    request_id: str
    origin_id: str
    energy_kwh: int
    units: int
    benefit: int


@dataclass
class Dataset:
    locations: list
    roads: list
    stations: list
    requests: list

    @property
    def names(self):
        return {l.location_id: l.name for l in self.locations}

    @property
    def severity(self):
        return {l.location_id: l.severity for l in self.locations}

    @property
    def hub(self):
        hubs = [l.location_id for l in self.locations if l.is_hub and l.active]
        return hubs[0] if hubs else None


def request_units(kwh):
    """Request energy rounds UP: a 21 kWh request needs 3 units."""
    return math.ceil(kwh / KWH_PER_UNIT)


def station_units(kwh):
    """Station capacity rounds DOWN: a 125 kWh station offers 12 units."""
    return kwh // KWH_PER_UNIT


# ---------- parsing helpers ----------

def _bool(value, where):
    if value == "true":
        return True
    if value == "false":
        return False
    raise DataError(f"{where}: expected true/false, got {value!r}")


def _int(value, where):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise DataError(f"{where}: expected an integer, got {value!r}") from None


def _float(value, where):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise DataError(f"{where}: expected a number, got {value!r}") from None


def _read(path, columns):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and set(columns) - set(rows[0]):
        raise DataError(f"{path.name}: missing columns {sorted(set(columns) - set(rows[0]))}")
    return rows


def load_dataset(data_dir="data"):
    d = Path(data_dir)
    locations = [
        Location(r["location_id"], r["name"],
                 _float(r["latitude"], r["location_id"]),
                 _float(r["longitude"], r["location_id"]),
                 _int(r["severity"], r["location_id"]),
                 _bool(r["is_hub"], r["location_id"]),
                 _bool(r["active"], r["location_id"]))
        for r in _read(d / "locations.csv",
                       ["location_id", "name", "latitude", "longitude", "severity", "is_hub", "active"])
    ]
    roads = [
        Road(r["edge_id"], r["u"], r["v"], _int(r["cost"], r["edge_id"]),
             _bool(r["available"], r["edge_id"]))
        for r in _read(d / "roads.csv", ["edge_id", "u", "v", "cost", "available"])
    ]
    stations = [
        Station(r["station_id"], r["location_id"],
                _int(r["capacity_kwh"], r["station_id"]),
                _int(r["capacity_units"], r["station_id"]),
                _bool(r["active"], r["station_id"]))
        for r in _read(d / "stations.csv",
                       ["station_id", "location_id", "capacity_kwh", "capacity_units", "active"])
    ]
    requests = [
        Request(r["request_id"], r["origin_id"],
                _int(r["energy_kwh"], r["request_id"]),
                _int(r["units"], r["request_id"]),
                _int(r["benefit"], r["request_id"]))
        for r in _read(d / "requests.csv", ["request_id", "origin_id", "energy_kwh", "units", "benefit"])
    ]
    ds = Dataset(locations, roads, stations, requests)
    validate_dataset(ds)
    return ds


def _unique(ids, what):
    seen = set()
    for i in ids:
        if i in seen:
            raise DataError(f"duplicate {what} ID {i!r}")
        seen.add(i)


def validate_dataset(ds):
    """Raise DataError on the first rule violation; return None if clean."""
    _unique([l.location_id for l in ds.locations], "location")
    _unique([r.edge_id for r in ds.roads], "road")
    _unique([s.station_id for s in ds.stations], "station")
    _unique([q.request_id for q in ds.requests], "request")

    sites = {l.location_id for l in ds.locations}
    for l in ds.locations:
        if l.severity < 0:
            raise DataError(f"{l.location_id}: negative severity")
    if sum(1 for l in ds.locations if l.is_hub) > 1:
        raise DataError("more than one hub")

    for r in ds.roads:
        if r.u not in sites or r.v not in sites:
            raise DataError(f"{r.edge_id}: invalid endpoint ({r.u}, {r.v})")
        if r.u == r.v:
            raise DataError(f"{r.edge_id}: self-loop at {r.u}")
        if r.cost < 0:
            raise DataError(f"{r.edge_id}: negative cost {r.cost}")

    for s in ds.stations:
        if s.location_id not in sites:
            raise DataError(f"{s.station_id}: unknown site {s.location_id}")
        if s.capacity_kwh < 0 or s.capacity_units < 0:
            raise DataError(f"{s.station_id}: negative capacity")
        if s.capacity_units != station_units(s.capacity_kwh):
            raise DataError(f"{s.station_id}: capacity_units must be floor(kWh/10)")

    for q in ds.requests:
        if q.origin_id not in sites:
            raise DataError(f"{q.request_id}: unknown origin {q.origin_id}")
        if q.energy_kwh < 0 or q.benefit < 0:
            raise DataError(f"{q.request_id}: negative energy or benefit")
        if q.units != request_units(q.energy_kwh):
            raise DataError(f"{q.request_id}: units must be ceil(kWh/10)")
