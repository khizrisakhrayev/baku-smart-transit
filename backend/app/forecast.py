"""Short-term density forecast per route.

1. Score each recent report: low = 1, medium = 2, high = 3.
2. Group them into one-minute buckets over the last FORECAST_BUCKETS minutes and
   average each bucket -> points (x = minutes relative to now, negative = past; y = score).
3. Fit a straight line through the points (ordinary least squares).
4. Extend the line FORECAST_HORIZON_MIN minutes ahead -> predicted score -> level.
Trend: slope above +TREND_THRESHOLD per minute is "rising", below -TREND_THRESHOLD
"falling", otherwise "stable".
Early warning: predicted "high" while the route is not "high" now.
"""
from datetime import datetime

from app import config, density
from app.models import Report, Route, RouteForecast
from app.store import Store, utcnow

SCORES = {"low": 1, "medium": 2, "high": 3}


def bucket_points(reports: list[Report], now: datetime) -> list[tuple[float, float]]:
    """(minutes relative to now, average score) for each bucket that has reports, oldest first."""
    history_sec = config.FORECAST_BUCKET_SEC * config.FORECAST_BUCKETS
    buckets: dict[int, list[int]] = {}
    for report in reports:
        age = (now - report.timestamp).total_seconds()
        if 0 <= age < history_sec:
            buckets.setdefault(int(age // config.FORECAST_BUCKET_SEC), []).append(SCORES[report.level])
    bucket_min = config.FORECAST_BUCKET_SEC / 60
    return sorted((-(k + 0.5) * bucket_min, sum(s) / len(s)) for k, s in buckets.items())


def fit_line(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Least-squares line y = slope * x + intercept. One point (or same x) -> flat line."""
    n = len(points)
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    spread_x = sum((x - mean_x) ** 2 for x, _ in points)
    if spread_x == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / spread_x
    return slope, mean_y - slope * mean_x


def score_to_level(score: float) -> str:
    if score < 1.5:
        return "low"
    if score < 2.5:
        return "medium"
    return "high"


def trend_of(slope: float) -> str:
    if slope > config.TREND_THRESHOLD:
        return "rising"
    if slope < -config.TREND_THRESHOLD:
        return "falling"
    return "stable"


def is_early_warning(predicted_level: str | None, current_level: str | None) -> bool:
    return predicted_level == "high" and current_level != "high"


def forecast_route(store: Store, route: Route, now: datetime) -> RouteForecast:
    current_level = density.route_summary(store, route, now).dominant_level
    points = bucket_points(store.reports_for_route(route.id), now)
    if not points:
        return RouteForecast(route_id=route.id, current_level=current_level, predicted_level=None,
                             predicted_score=None, trend="stable", slope_per_min=0.0, early_warning=False)
    slope, intercept = fit_line(points)
    predicted_score = min(3.0, max(1.0, intercept + slope * config.FORECAST_HORIZON_MIN))
    predicted_level = score_to_level(predicted_score)
    return RouteForecast(
        route_id=route.id,
        current_level=current_level,
        predicted_level=predicted_level,
        predicted_score=round(predicted_score, 2),
        trend=trend_of(slope),
        slope_per_min=round(slope, 3),
        early_warning=is_early_warning(predicted_level, current_level),
    )


def summary(store: Store, now: datetime | None = None) -> list[RouteForecast]:
    now = now or utcnow()
    return [forecast_route(store, route, now) for route in store.routes.values()]
