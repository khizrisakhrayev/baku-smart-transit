"""Anomaly detection on crowd density reports.

Rule: a route is anomalous when its most recent reports form an unbroken run of
"high" reports (no low/medium in between) that has at least config.MIN_HIGH_REPORTS reports
and spans at least config.ANOMALY_WINDOW_SEC from the first to the last of them.

Then one alert is opened for the route (with a smart-dispatch recommendation, see
dispatch.py); while it is active no duplicate is created.
Only reports from the last 2 windows (+1 min slack) are read: that is enough to see any
run that spans a full window and whose latest report is within the last window (older
runs are stale anyway).
After the operator resolves it, the route alerts again only once a new "high"
report arrives (so the background check doesn't immediately re-open it).

Pending: a route with a current high run but no alert yet is "being watched"; we report
how many high reports the run has and how many seconds until it spans the window.
"""
import asyncio
from datetime import datetime, timedelta

from app import config, dispatch
from app.models import Alert, PendingRoute, PendingSummary, Report
from app.store import Store, utcnow

ALERT_MESSAGE = "Əlavə avtobus ehtiyatı ayrılmalıdır"


def trailing_high_run(reports: list[Report]) -> list[Report]:
    """The newest consecutive "high" reports (oldest first), stopping at any low/medium."""
    run = []
    for report in reversed(reports):
        if report.level != "high":
            break
        run.append(report)
    return run[::-1]


def is_anomalous(reports: list[Report], window_sec: float) -> bool:
    """Apply the rule above to a route's reports (sorted oldest first)."""
    run = trailing_high_run(reports)
    if len(run) < config.MIN_HIGH_REPORTS:
        return False
    span = (run[-1].timestamp - run[0].timestamp).total_seconds()
    return span >= window_sec


def recent_reports(store: Store, route_id: str, now: datetime) -> list[Report]:
    """The reports the rule looks at: the last 2 windows (+1 min slack)."""
    lookback = timedelta(seconds=2 * config.ANOMALY_WINDOW_SEC + 60)
    return store.reports_for_route(route_id, since=now - lookback)


def already_handled(store: Store, route_id: str, reports: list[Report]) -> bool:
    """True if an alert was resolved after the latest report (wait for a new report)."""
    resolved_at = store.last_resolved_at(route_id)
    return bool(reports) and resolved_at is not None and reports[-1].timestamp <= resolved_at


def check_route(store: Store, route_id: str, now: datetime | None = None) -> Alert | None:
    """Open an alert for the route if it is anomalous and has none active. Returns the new alert."""
    if store.active_alert(route_id):
        return None
    now = now or utcnow()
    reports = recent_reports(store, route_id, now)
    if not is_anomalous(reports, config.ANOMALY_WINDOW_SEC):
        return None
    if already_handled(store, route_id, reports):
        return None
    donor = dispatch.choose_donor(store, route_id)
    return store.create_alert(
        route_id, ALERT_MESSAGE, now,
        donor_route_id=donor,
        recommendation=dispatch.recommendation_text(donor, route_id) if donor else None,
    )


def pending_status(reports: list[Report], window_sec: float, now: datetime) -> tuple[int, float] | None:
    """(high reports in the current run, seconds until the run spans the window),
    or None if the latest report is not "high". Seconds never go below 0."""
    run = trailing_high_run(reports)
    if not run:
        return None
    window_reached_at = run[0].timestamp + timedelta(seconds=window_sec)
    return len(run), max(0.0, (window_reached_at - now).total_seconds())


def pending(store: Store, now: datetime | None = None) -> PendingSummary:
    """Routes heading toward an alert: a current high run, no active alert, not already handled."""
    now = now or utcnow()
    routes = []
    for route_id in store.routes:
        if store.active_alert(route_id):
            continue
        reports = recent_reports(store, route_id, now)
        status = pending_status(reports, config.ANOMALY_WINDOW_SEC, now)
        if status is None or already_handled(store, route_id, reports):
            continue
        high_reports, seconds = status
        routes.append(PendingRoute(route_id=route_id, high_reports=high_reports,
                                   seconds_remaining=round(seconds)))
    return PendingSummary(window_sec=config.ANOMALY_WINDOW_SEC,
                          required_reports=config.MIN_HIGH_REPORTS, routes=routes)


def check_all(store: Store, now: datetime | None = None) -> list[Alert]:
    alerts = [check_route(store, route_id, now) for route_id in store.routes]
    return [a for a in alerts if a]


async def run(store: Store, interval: float = config.CHECK_INTERVAL_SEC) -> None:
    """Background loop: re-check all routes until cancelled."""
    while True:
        await asyncio.sleep(interval)
        check_all(store)
