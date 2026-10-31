"""Anomaly detection on crowd density reports.

Rule: a route is anomalous when its most recent reports form an unbroken run of
"high" reports (no low/medium in between) that has at least MIN_HIGH_REPORTS reports
and spans at least ANOMALY_WINDOW_SEC from the first to the last of them.

Then one alert is opened for the route (with a smart-dispatch recommendation, see
dispatch.py); while it is active no duplicate is created.
After the operator resolves it, the route alerts again only once a new "high"
report arrives (so the background check doesn't immediately re-open it).
"""
import asyncio
import os
from datetime import datetime

from app import dispatch
from app.models import Alert, Report
from app.store import Store, utcnow

ANOMALY_WINDOW_SEC = int(os.getenv("ANOMALY_WINDOW_SEC", "600"))
MIN_HIGH_REPORTS = 3
CHECK_INTERVAL_SEC = 10
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
    if len(run) < MIN_HIGH_REPORTS:
        return False
    span = (run[-1].timestamp - run[0].timestamp).total_seconds()
    return span >= window_sec


def check_route(store: Store, route_id: str, now: datetime | None = None) -> Alert | None:
    """Open an alert for the route if it is anomalous and has none active. Returns the new alert."""
    if store.active_alert(route_id):
        return None
    reports = store.reports_for_route(route_id)
    if not is_anomalous(reports, ANOMALY_WINDOW_SEC):
        return None
    resolved_at = store.last_resolved_at(route_id)
    if resolved_at and reports[-1].timestamp <= resolved_at:
        return None  # already handled; wait for a new report
    donor = dispatch.choose_donor(store, route_id)
    return store.create_alert(
        route_id, ALERT_MESSAGE, now or utcnow(),
        donor_route_id=donor,
        recommendation=dispatch.recommendation_text(donor, route_id) if donor else None,
    )


def check_all(store: Store, now: datetime | None = None) -> list[Alert]:
    alerts = [check_route(store, route_id, now) for route_id in store.routes]
    return [a for a in alerts if a]


async def run(store: Store, interval: float = CHECK_INTERVAL_SEC) -> None:
    """Background loop: re-check all routes until cancelled."""
    while True:
        await asyncio.sleep(interval)
        check_all(store)
