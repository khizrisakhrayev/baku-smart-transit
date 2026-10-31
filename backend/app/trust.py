"""Report trust: rate limiting, distance check and freshness weighting.

- Rate limit: one report per client per bus per REPORT_COOLDOWN_SEC.
- Distance: if the passenger sent a location, it must be within MAX_REPORT_DISTANCE_M
  of the bus (0 disables the check).
- Freshness: a report's weight falls linearly from 1.0 (now) to 0.0 (window end).
- Confidence (0-1) = reporter factor * average freshness, where the reporter factor is
  unique clients / CONFIDENT_CLIENTS, capped at 1. Many fresh, independent reporters
  give high confidence; one person or only old reports give low confidence.
"""
import math
from datetime import datetime

from app import config
from app.models import Bus, Report, ReportIn
from app.store import Store

EARTH_RADIUS_M = 6_371_000


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle (haversine) distance in metres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def is_too_far(report_in: ReportIn, bus: Bus) -> bool:
    """True if the report has a location and it is too far from the bus."""
    if report_in.lat is None or config.MAX_REPORT_DISTANCE_M <= 0:
        return False
    return distance_m(report_in.lat, report_in.lon, bus.lat, bus.lon) > config.MAX_REPORT_DISTANCE_M


def is_rate_limited(store: Store, client_id: str, bus_id: str, now: datetime) -> bool:
    """True if this client already reported on this bus within the cooldown."""
    last = store.last_report_time(client_id, bus_id)
    return last is not None and (now - last).total_seconds() < config.REPORT_COOLDOWN_SEC


def freshness_weight(timestamp: datetime, now: datetime, window_sec: float) -> float:
    """1.0 for a report made now, falling linearly to 0.0 at the end of the window."""
    age = (now - timestamp).total_seconds()
    if window_sec <= 0:
        return 1.0 if age <= 0 else 0.0
    return min(1.0, max(0.0, 1 - age / window_sec))


def confidence(reports: list[Report], now: datetime, window_sec: float) -> float:
    """Confidence 0-1 in a route's density, from the reports inside the window."""
    if not reports:
        return 0.0
    unique_clients = len({r.client_id for r in reports})
    reporter_factor = min(1.0, unique_clients / config.CONFIDENT_CLIENTS)
    avg_freshness = sum(freshness_weight(r.timestamp, now, window_sec) for r in reports) / len(reports)
    return round(reporter_factor * avg_freshness, 2)
