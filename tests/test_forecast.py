"""Forecast: trend fit and predicted levels with fixed data."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config, forecast, simulator
from app.main import app
from app.models import ReportIn, Route, Stop
from app.routes_data import ROUTES
from app.store import Store, store

NOW = datetime(2026, 10, 31, 17, 0, tzinfo=timezone.utc)
ROUTE = Route(id="T", name="Test", stops=[Stop(id="a", name="A", lat=40.0, lon=49.0)])


@pytest.fixture(autouse=True)
def fixed_settings(monkeypatch):
    monkeypatch.setattr(config, "FORECAST_BUCKET_SEC", 60)
    monkeypatch.setattr(config, "FORECAST_BUCKETS", 10)
    monkeypatch.setattr(config, "FORECAST_HORIZON_MIN", 15)
    monkeypatch.setattr(config, "TREND_THRESHOLD", 0.05)
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", 600)


# --- Line fit ---

def test_fit_exact_line():
    slope, intercept = forecast.fit_line([(-3, 1.4), (-2, 1.6), (-1, 1.8)])
    assert slope == pytest.approx(0.2)
    assert intercept == pytest.approx(2.0)


def test_fit_flat_data():
    assert forecast.fit_line([(-3, 2), (-2, 2), (-1, 2)]) == pytest.approx((0, 2))


def test_fit_single_point_is_flat():
    assert forecast.fit_line([(-1, 2.5)]) == (0.0, 2.5)


def test_fit_noisy_data_finds_trend():
    slope, _ = forecast.fit_line([(-4, 1.0), (-3, 1.5), (-2, 1.3), (-1, 2.0)])
    assert slope == pytest.approx(0.28)


# --- Levels and trend ---

@pytest.mark.parametrize("score, level", [(1.0, "low"), (1.49, "low"), (1.5, "medium"),
                                          (2.49, "medium"), (2.5, "high"), (3.0, "high")])
def test_score_to_level(score, level):
    assert forecast.score_to_level(score) == level


@pytest.mark.parametrize("slope, trend", [(0.2, "rising"), (0.05, "stable"), (0.0, "stable"),
                                          (-0.05, "stable"), (-0.2, "falling")])
def test_trend_of(slope, trend):
    assert forecast.trend_of(slope) == trend


def test_early_warning_only_when_high_is_coming():
    assert forecast.is_early_warning("high", "medium")
    assert forecast.is_early_warning("high", None)
    assert not forecast.is_early_warning("high", "high")
    assert not forecast.is_early_warning("medium", "low")


# --- Buckets and full forecast ---

def db_with(levels_by_minute_ago: dict[float, list[str]]) -> Store:
    """Store with reports for route T: {minutes ago: [levels]}."""
    db = Store()
    db.add_route(ROUTE)
    for minutes_ago, levels in levels_by_minute_ago.items():
        for n, level in enumerate(levels):
            db.add_report(ReportIn(route_id="T", bus_id="T-1", level=level, client_id=f"c{n}"),
                          timestamp=NOW - timedelta(minutes=minutes_ago))
    return db


def test_bucket_points_average_each_minute_and_skip_old_reports():
    db = db_with({0.5: ["high", "low"], 2.2: ["medium"], 30: ["high"]})
    points = forecast.bucket_points(db.reports_for_route("T"), NOW)
    assert points == [(-2.5, 2.0), (-0.5, 2.0)]


def test_rising_route_is_predicted_high_with_early_warning():
    # Mostly low 9 minutes ago, climbing to medium now: score 1.0 -> 2.0.
    db = db_with({8.5: ["low", "low"], 6.5: ["low", "medium"], 4.5: ["medium", "low"],
                  2.5: ["medium", "medium"], 0.5: ["medium", "medium"]})
    result = forecast.forecast_route(db, ROUTE, NOW)
    assert result.trend == "rising"
    assert result.current_level == "medium"
    assert result.predicted_level == "high"
    assert result.early_warning


def test_falling_route_is_predicted_low():
    db = db_with({8.5: ["high", "high"], 4.5: ["high", "medium"], 0.5: ["medium", "medium"]})
    result = forecast.forecast_route(db, ROUTE, NOW)
    assert result.trend == "falling"
    assert result.predicted_level == "low"
    assert not result.early_warning


def test_stable_route_keeps_its_level():
    db = db_with({8.5: ["medium"], 4.5: ["medium"], 0.5: ["medium"]})
    result = forecast.forecast_route(db, ROUTE, NOW)
    assert (result.trend, result.predicted_level, result.predicted_score) == ("stable", "medium", 2.0)


def test_already_high_route_is_not_an_early_warning():
    db = db_with({8.5: ["high"], 0.5: ["high"]})
    result = forecast.forecast_route(db, ROUTE, NOW)
    assert result.predicted_level == "high" and not result.early_warning


def test_predicted_score_is_clamped_to_scale():
    db = db_with({2.5: ["low"], 0.5: ["high"]})  # very steep rise
    assert forecast.forecast_route(db, ROUTE, NOW).predicted_score == 3.0


def test_route_without_reports_has_no_prediction():
    result = forecast.forecast_route(db_with({}), ROUTE, NOW)
    assert (result.predicted_level, result.trend, result.early_warning) == (None, "stable", False)


# --- API ---

def test_forecast_endpoint_lists_every_route():
    store.reset()
    simulator.seed(store, ROUTES)
    body = TestClient(app).get("/api/operator/forecast").json()
    assert {f["route_id"] for f in body} == {r.id for r in ROUTES}
    assert {"trend", "predicted_level", "early_warning"} <= set(body[0])
