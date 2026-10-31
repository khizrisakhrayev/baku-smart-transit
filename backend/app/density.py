"""Operator density overview: per-route summary of recent passenger reports.

The dominant level uses freshness-weighted counts (see trust.py), so a fresh "low"
report outweighs several "high" reports that are about to leave the window.
"""
from datetime import datetime, timedelta

from app import config, trust
from app.models import Report, Route, RouteDensity
from app.store import Store, utcnow

LEVELS = ("low", "medium", "high")


def dominant_level(counts: dict[str, float]) -> str | None:
    """Highest (weighted) count; ties go to the more crowded level. None if all zero."""
    if not any(counts.values()):
        return None
    return max(LEVELS, key=lambda level: (counts[level], LEVELS.index(level)))


def route_summary(store: Store, route: Route, now: datetime) -> RouteDensity:
    """Summarises reports from the last ANOMALY_WINDOW_SEC; last_report_at covers all time."""
    recent = store.reports_for_route(route.id, since=window_start(now))
    return summarize(route, recent, store.last_report_at(route.id), len(store.buses_on_route(route.id)), now)


def window_start(now: datetime) -> datetime:
    return now - timedelta(seconds=config.ANOMALY_WINDOW_SEC)


def summarize(route: Route, recent: list[Report], last_report_at: datetime | None,
              bus_count: int, now: datetime) -> RouteDensity:
    """Pure: the density summary from the route's reports inside the window."""
    window = config.ANOMALY_WINDOW_SEC
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
        bus_count=bus_count,
        last_report_at=last_report_at,
    )


def summary(store: Store, now: datetime | None = None) -> list[RouteDensity]:
    now = now or utcnow()
    return [route_summary(store, route, now) for route in store.routes.values()]
