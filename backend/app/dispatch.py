"""Smart dispatch: move a bus from a quiet route to an overcrowded one.

Donor choice: among other routes that are calm (dominant level "low" or no reports in
the window), have no active alert and at least MIN_DONOR_BUSES buses (see config.py),
pick the one with the most "low" reports, then the fewest medium/high reports, then the
most buses.
"""
from app import config, density
from app.models import Alert, Bus, RouteDensity
from app.store import Store

CALM_LEVELS = ("low", None)


class DispatchError(Exception):
    """The recommended dispatch can't be carried out (message is shown to the operator)."""


def recommendation_text(donor_route_id: str, target_route_id: str) -> str:
    # Arrow format avoids Azerbaijani case suffixes, which depend on how the number is read.
    return f"Tövsiyə: Marşrut {donor_route_id} → Marşrut {target_route_id} (1 avtobus yönləndirin)"


def donor_candidates(store: Store, target_route_id: str) -> list[RouteDensity]:
    alerted = {a.route_id for a in store.list_alerts() if a.resolved_at is None}
    return [
        d for d in density.summary(store)
        if d.route_id != target_route_id
        and d.route_id not in alerted
        and d.bus_count >= config.MIN_DONOR_BUSES
        and d.dominant_level in CALM_LEVELS
    ]


def choose_donor(store: Store, target_route_id: str) -> str | None:
    """Best donor route id for `target_route_id`, or None if no route can spare a bus."""
    candidates = donor_candidates(store, target_route_id)
    if not candidates:
        return None
    best = max(candidates, key=lambda d: (
        d.counts["low"],
        -(d.counts["medium"] + d.counts["high"]),
        d.bus_count,
    ))
    return best.route_id


def dispatch_bus(store: Store, alert: Alert) -> tuple[Alert, Bus]:
    """Move one bus from the alert's donor route to its route and resolve the alert."""
    if alert.resolved_at is not None:
        raise DispatchError("Xəbərdarlıq artıq həll edilib")
    if alert.donor_route_id is None:
        raise DispatchError("Bu xəbərdarlıq üçün donor marşrut yoxdur")
    donor_buses = store.buses_on_route(alert.donor_route_id)
    if len(donor_buses) < config.MIN_DONOR_BUSES:
        raise DispatchError(f"Donor marşrutda ({alert.donor_route_id}) kifayət qədər avtobus yoxdur")

    bus = donor_buses[-1]
    first_stop = store.routes[alert.route_id].stops[0]
    # Start the bus at the beginning of its new route; its old density no longer applies.
    bus.route_id = alert.route_id
    bus.path_index = 0
    bus.progress = 0.0
    bus.lat, bus.lon = first_stop.lat, first_stop.lon
    bus.density = None

    resolved = store.resolve_alert(alert.id, dispatched_bus_id=bus.id)
    return resolved, bus
