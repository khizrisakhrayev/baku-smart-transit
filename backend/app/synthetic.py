"""Synthetic background reports, so the demo looks alive without real passengers.

Every SYNTHETIC_INTERVAL_SEC a few random buses get a report from a made-up passenger.
A rush-hour wave (intensity 0 -> 1 -> 0 over RUSH_PERIOD_SEC) pushes central routes
(those through 28 May, Koroğlu or Gənclik) toward "high"; outer routes stay mostly "low".
Turned off with SYNTHETIC_REPORTS=0 (and always in tests).
"""
import asyncio
import math
import random
import time
from datetime import datetime

from app import config
from app.models import Report, ReportIn, Route
from app.store import Store, utcnow

LEVELS = ("low", "medium", "high")
OUTER_WEIGHTS = {"low": 0.70, "medium": 0.25, "high": 0.05}


def is_central(route: Route) -> bool:
    return any(stop.id in config.CENTRAL_STOP_IDS for stop in route.stops)


def rush_intensity(elapsed_sec: float) -> float:
    """Smooth wave from 0 (quiet) up to 1 (peak rush) and back over RUSH_PERIOD_SEC."""
    return (1 - math.cos(2 * math.pi * elapsed_sec / config.RUSH_PERIOD_SEC)) / 2


def level_weights(central: bool, intensity: float) -> dict[str, float]:
    """Probability of each level. Central routes: 15% high when quiet, 80% at peak."""
    if not central:
        return OUTER_WEIGHTS
    high = 0.15 + 0.65 * intensity
    medium = 0.20
    return {"low": max(0.0, 1 - high - medium), "medium": medium, "high": high}  # max: float rounding


def generate(store: Store, rng: random.Random, elapsed_sec: float,
             count: int = config.SYNTHETIC_REPORTS_PER_TICK, now: datetime | None = None) -> list[Report]:
    """Add `count` synthetic reports on random buses, each from a distinct fake client."""
    buses = list(store.buses.values())
    if not buses:
        return []
    intensity = rush_intensity(elapsed_sec)
    reports = []
    for _ in range(count):
        bus = rng.choice(buses)
        weights = level_weights(is_central(store.routes[bus.route_id]), intensity)
        level = rng.choices(LEVELS, weights=[weights[l] for l in LEVELS])[0]
        report_in = ReportIn(route_id=bus.route_id, bus_id=bus.id, level=level,
                             client_id=f"sim-{rng.getrandbits(48):012x}")
        reports.append(store.add_report(report_in, timestamp=now or utcnow()))
    return reports


async def run(store: Store, interval: float = config.SYNTHETIC_INTERVAL_SEC) -> None:
    """Background loop: generate reports until cancelled. The rush wave starts at startup."""
    rng = random.Random()
    started = time.monotonic()
    while True:
        await asyncio.sleep(interval)
        generate(store, rng, time.monotonic() - started)
