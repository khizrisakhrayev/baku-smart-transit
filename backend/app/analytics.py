"""Network analytics for the operator dashboard.

- Timeline: report counts per level for each of the last ANALYTICS_MINUTES minutes
  (whole network, oldest minute first, empty minutes included as zeros).
- Top routes: the ANALYTICS_TOP_ROUTES routes with the largest share of "high" in their
  freshness-weighted reports (see density.py / trust.py).
- Density index (0-100): freshness-weighted average score over the whole network,
  where low = 1 -> 0, medium = 2 -> 50, high = 3 -> 100. None if there are no reports.
"""
from datetime import datetime, timedelta

from app import config, density
from app.models import Analytics, MinuteCounts, RouteDensity, RouteHighShare
from app.store import Store, utcnow

SCORES = {"low": 1, "medium": 2, "high": 3}


def timeline(store: Store, now: datetime) -> list[MinuteCounts]:
    minutes = config.ANALYTICS_MINUTES
    start = now - timedelta(minutes=minutes)
    buckets = [MinuteCounts(minute=start + timedelta(minutes=i)) for i in range(minutes)]
    for report in store.reports_since(start):
        index = int((report.timestamp - start).total_seconds() // 60)
        if 0 <= index < minutes:
            counts = buckets[index]
            setattr(counts, report.level, getattr(counts, report.level) + 1)
    return buckets


def high_share(d: RouteDensity) -> float:
    total = sum(d.weighted_counts.values())
    return d.weighted_counts["high"] / total if total else 0.0


def top_routes(densities: list[RouteDensity]) -> list[RouteHighShare]:
    """Routes with any "high" weight, largest high share first (ties: more high weight)."""
    crowded = [d for d in densities if d.weighted_counts["high"] > 0]
    crowded.sort(key=lambda d: (high_share(d), d.weighted_counts["high"]), reverse=True)
    return [RouteHighShare(route_id=d.route_id, route_name=d.route_name,
                           high_share=round(high_share(d), 3), weighted_high=d.weighted_counts["high"])
            for d in crowded[:config.ANALYTICS_TOP_ROUTES]]


def density_index(densities: list[RouteDensity]) -> int | None:
    total_weight = sum(sum(d.weighted_counts.values()) for d in densities)
    if total_weight == 0:
        return None
    score_sum = sum(SCORES[level] * w for d in densities for level, w in d.weighted_counts.items())
    average = score_sum / total_weight  # 1..3
    return round((average - 1) / 2 * 100)


def summary(store: Store, now: datetime | None = None) -> Analytics:
    now = now or utcnow()
    densities = density.summary(store, now)
    return Analytics(timeline=timeline(store, now), top_routes=top_routes(densities),
                     density_index=density_index(densities))
