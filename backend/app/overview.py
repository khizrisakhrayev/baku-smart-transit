"""Operator overview: everything the operator page needs, in one response.

Batched instead of per route: 3 SQL queries in total (recent reports of the whole network,
latest report time per route, all alerts), then each route's density, forecast and pending
status is computed in memory with the same pure functions the single endpoints use, so the
numbers always match /api/operator/density, /forecast and /pending.
"""
from collections import defaultdict
from datetime import datetime

from app import anomaly, density, forecast
from app.models import Overview
from app.store import Store, utcnow


def build(store: Store, now: datetime | None = None) -> Overview:
    now = now or utcnow()
    window_start = density.window_start(now)
    history_start = forecast.history_start(now)
    lookback_start = anomaly.lookback_start(now)

    # Query 1: every report any of the three calculations needs, grouped by route.
    reports_by_route = defaultdict(list)
    for report in store.reports_since(min(window_start, history_start, lookback_start)):
        reports_by_route[report.route_id].append(report)
    # Query 2 and 3.
    last_report_times = store.last_report_times()
    alerts = store.list_alerts()

    active_routes = {a.route_id for a in alerts if a.resolved_at is None}
    last_resolved = {}
    for alert in alerts:
        if alert.resolved_at and (alert.route_id not in last_resolved or alert.resolved_at > last_resolved[alert.route_id]):
            last_resolved[alert.route_id] = alert.resolved_at

    densities, forecasts, pending = [], [], []
    for route in store.routes.values():
        reports = reports_by_route[route.id]  # oldest first
        route_density = density.summarize(
            route, [r for r in reports if r.timestamp >= window_start],
            last_report_times.get(route.id), len(store.buses_on_route(route.id)), now)
        densities.append(route_density)
        forecasts.append(forecast.forecast_from(
            route.id, [r for r in reports if r.timestamp >= history_start], route_density.dominant_level, now))
        if route.id not in active_routes:
            entry = anomaly.pending_route(
                route.id, [r for r in reports if r.timestamp >= lookback_start], last_resolved.get(route.id), now)
            if entry:
                pending.append(entry)

    return Overview(
        routes=list(store.routes.values()),
        buses=list(store.buses.values()),
        densities=densities,
        forecasts=forecasts,
        pending=anomaly.pending_summary(pending),
        alerts=alerts,
    )
