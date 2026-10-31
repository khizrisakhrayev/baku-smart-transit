"""ETA calculation: when will each bus reach a given stop?

The simulator moves a bus one full stop-to-stop segment every SEGMENT_SECONDS,
regardless of distance. So for a bus that left path[i] and is `progress` of the way
to the next stop, the time to reach path[k] is:

    ((k - i) mod len(path) - progress) * SEGMENT_SECONDS

A stop can appear twice on the round-trip path (outbound and return); we take the
soonest visit. If the bus has just left the stop, its next visit is a full loop away.

Passengers see realistic times: the result is scaled by config.SIM_TIME_SCALE
(see config.py), so one stop-to-stop segment (30s on the map) shows as 2.5 minutes.
"""
from app import config
from app.models import Bus, BusEta, Route
from app.simulator import route_path
from app.store import Store

SEGMENT_SECONDS = config.STEPS_PER_SEGMENT * config.TICK_SECONDS


def segments_until_stop(bus: Bus, route: Route, stop_id: str) -> float | None:
    """Segments (possibly fractional) until the bus reaches the stop; None if not on route."""
    path = route_path(route)
    best = None
    for k, stop in enumerate(path):
        if stop.id != stop_id:
            continue
        remaining = (k - bus.path_index) % len(path) - bus.progress
        if remaining < 0:  # just passed it
            remaining += len(path)
        best = remaining if best is None else min(best, remaining)
    return best


def eta_minutes(bus: Bus, route: Route, stop_id: str) -> float | None:
    segments = segments_until_stop(bus, route, stop_id)
    if segments is None:
        return None
    return round(segments * SEGMENT_SECONDS * config.SIM_TIME_SCALE / 60, 1)


def etas_for_stop(store: Store, stop_id: str) -> list[BusEta]:
    """ETA and current density of every bus serving the stop, soonest first."""
    etas = []
    for route in store.routes_with_stop(stop_id):
        for bus in store.buses_on_route(route.id):
            etas.append(BusEta(bus_id=bus.id, route_id=route.id,
                               eta_minutes=eta_minutes(bus, route, stop_id),
                               density=bus.density))
    return sorted(etas, key=lambda e: e.eta_minutes)
