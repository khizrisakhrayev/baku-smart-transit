"""Passenger alternatives at a stop, computed from its ETA list (soonest first).

- Suggestion: for each "high" (crowded) bus, the soonest bus arriving at the same time or
  later, on any route serving the stop, that is not "high" (low, medium or unknown).
  Only suggested if the extra wait is at most MAX_EXTRA_WAIT_MIN. A calmer bus arriving
  *before* the crowded one needs no suggestion: the passenger takes it anyway.
- Most comfortable: among buses arriving within COMFORT_HORIZON_MIN, the least crowded
  one (low before medium; earliest on ties). Only marked if it is known to be low or
  medium, so we never recommend a bus we know nothing about.
"""
from app import config
from app.models import BusEta, Suggestion

COMFORT_RANK = {"low": 0, "medium": 1}  # unknown and high are never "most comfortable"


def find_suggestion(crowded: BusEta, etas: list[BusEta]) -> Suggestion | None:
    """Soonest non-crowded bus at or after `crowded`, within the extra-wait limit."""
    for other in etas:
        if other.bus_id == crowded.bus_id or other.density == "high":
            continue
        extra_wait = round(other.eta_minutes - crowded.eta_minutes, 1)
        if extra_wait < 0:
            continue
        if extra_wait > config.MAX_EXTRA_WAIT_MIN:
            return None  # list is sorted, so every later bus is even further away
        return Suggestion(bus_id=other.bus_id, route_id=other.route_id, eta_minutes=other.eta_minutes,
                          density=other.density, extra_wait_minutes=extra_wait)
    return None


def most_comfortable(etas: list[BusEta]) -> BusEta | None:
    """Least crowded known-calm bus arriving within the comfort horizon."""
    candidates = [e for e in etas
                  if e.eta_minutes <= config.COMFORT_HORIZON_MIN and e.density in COMFORT_RANK]
    if not candidates:
        return None
    return min(candidates, key=lambda e: (COMFORT_RANK[e.density], e.eta_minutes))


def annotate(etas: list[BusEta]) -> list[BusEta]:
    """Add suggestions and the most-comfortable flag to a stop's ETA list (sorted by ETA)."""
    etas = sorted(etas, key=lambda e: e.eta_minutes)
    for bus_eta in etas:
        if bus_eta.density == "high":
            bus_eta.suggestion = find_suggestion(bus_eta, etas)
    best = most_comfortable(etas)
    if best:
        best.most_comfortable = True
    return etas
