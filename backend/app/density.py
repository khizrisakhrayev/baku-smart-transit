"""Operator density overview: per-route summary of recent passenger reports.

The dominant level uses freshness-weighted counts (see trust.py), so a fresh "low"
report outweighs several "high" reports that are about to leave the window.
"""
from datetime import datetime, timedelta

from app import config, trust
from app.models import Route, RouteDensity
from app.store import Store, utcnow

LEVELS = ("low", "medium", "high")


def dominant_level(counts: dict[str, float]) -> str | None:
    """Highest (weighted) count; ties go to the more crowded level. None if all zero."""
    if not any(counts.values()):
        return None
    return max(LEVELS, key=lambda level: (counts[level], LEVELS.index(level)))


def route_summary(store: Store, route: Route, now: datetime) -> RouteDensity:
    """Summarises reports from the last ANOMALY_WINDOW_SEC; last_report_at covers all time."""
    window = config.ANOMALY_WINDOW_SEC
    recent = store.reports_for_route(route.id, since=now - timedelta(seconds=window))

    counts = {level: 0 for level in LEVELS}
    weighted = {level: 0.0 for level in LEVELS}
    for report in recent:
        counts[report.level] += 1
        weighted[report.level] += trust.freshness_weight(report.timestamp, now, window)

    return RouteDensity(
        route_id=route.id,
        route_name=route.name,
        dominant_level=dominant_level(weighted),
        counts=counts,
        weighted_counts={level: round(w, 2) for level, w in weighted.items()},
        confidence=trust.confidence(recent, now, window),
        bus_count=len(store.buses_on_route(route.id)),
        last_report_at=store.last_report_at(route.id),
    )


def summary(store: Store, now: datetime | None = None) -> list[RouteDensity]:
    now = now or utcnow()
    return [route_summary(store, route, now) for route in store.routes.values()]
