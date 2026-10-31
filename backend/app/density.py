"""Operator density overview: per-route summary of recent passenger reports."""
from datetime import datetime, timedelta

from app import anomaly
from app.models import Route, RouteDensity
from app.store import Store, utcnow

LEVELS = ("low", "medium", "high")


def dominant_level(counts: dict[str, int]) -> str | None:
    """Most reported level; ties go to the more crowded level. None if no reports."""
    if not any(counts.values()):
        return None
    return max(LEVELS, key=lambda level: (counts[level], LEVELS.index(level)))


def route_summary(store: Store, route: Route, now: datetime) -> RouteDensity:
    """Counts reports from the last ANOMALY_WINDOW_SEC; last_report_at covers all time."""
    reports = store.reports_for_route(route.id)
    since = now - timedelta(seconds=anomaly.ANOMALY_WINDOW_SEC)
    counts = {level: 0 for level in LEVELS}
    for report in reports:
        if report.timestamp >= since:
            counts[report.level] += 1
    return RouteDensity(
        route_id=route.id,
        route_name=route.name,
        dominant_level=dominant_level(counts),
        counts=counts,
        bus_count=len(store.buses_on_route(route.id)),
        last_report_at=reports[-1].timestamp if reports else None,
    )


def summary(store: Store, now: datetime | None = None) -> list[RouteDensity]:
    now = now or utcnow()
    return [route_summary(store, route, now) for route in store.routes.values()]
