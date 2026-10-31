"""Analytics endpoint, plus the time-ranged report queries behind it."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import analytics, anomaly, config, density, simulator
from app.main import app
from app.models import ReportIn
from app.routes_data import ROUTES
from app.store import Store, store, utcnow

NOW = datetime(2026, 10, 31, 17, 0, tzinfo=timezone.utc)
client = TestClient(app)


@pytest.fixture
def db(monkeypatch) -> Store:
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", 600)
    monkeypatch.setattr(config, "ANALYTICS_MINUTES", 30)
    monkeypatch.setattr(config, "ANALYTICS_TOP_ROUTES", 10)
    db = Store()
    simulator.seed(db, ROUTES)
    return db


def add(db: Store, route_id: str, level: str, minutes_ago: float, client: str = "c") -> None:
    bus_id = db.buses_on_route(route_id)[0].id
    db.add_report(ReportIn(route_id=route_id, bus_id=bus_id, level=level, client_id=client),
                  timestamp=NOW - timedelta(minutes=minutes_ago))


# --- Timeline ---

def test_timeline_has_one_bucket_per_minute(db):
    result = analytics.timeline(db, NOW)
    assert len(result) == 30
    assert result[0].minute == NOW - timedelta(minutes=30)
    assert result[-1].minute == NOW - timedelta(minutes=1)
    assert all((m.low, m.medium, m.high) == (0, 0, 0) for m in result)


def test_timeline_counts_levels_in_the_right_minute(db):
    add(db, "5", "high", 0.5)
    add(db, "1", "high", 0.2)
    add(db, "65", "low", 0.7)
    add(db, "88", "medium", 10.5)
    add(db, "5", "high", 45)  # older than 30 minutes: ignored
    result = analytics.timeline(db, NOW)
    assert (result[-1].low, result[-1].medium, result[-1].high) == (1, 0, 2)
    assert result[-11].medium == 1
    assert sum(m.low + m.medium + m.high for m in result) == 4


# --- Top routes and density index ---

def test_top_routes_sorted_by_high_share(db):
    add(db, "5", "high", 1)
    add(db, "5", "high", 1)
    add(db, "1", "high", 1)
    add(db, "1", "low", 1)
    add(db, "65", "low", 1)  # no high: not listed
    result = analytics.top_routes(density.summary(db, NOW))
    assert [r.route_id for r in result] == ["5", "1"]
    assert result[0].high_share == 1.0
    assert result[1].high_share == pytest.approx(0.5)


def test_top_routes_limited_to_ten(db):
    for route in ROUTES[:12]:
        add(db, route.id, "high", 1)
    assert len(analytics.top_routes(density.summary(db, NOW))) == 10


def test_density_index_scale(db):
    assert analytics.density_index(density.summary(db, NOW)) is None
    add(db, "5", "low", 0)
    assert analytics.density_index(density.summary(db, NOW)) == 0
    add(db, "1", "high", 0)
    assert analytics.density_index(density.summary(db, NOW)) == 50
    add(db, "8", "high", 0)
    add(db, "11", "high", 0)
    assert analytics.density_index(density.summary(db, NOW)) == 75


# --- API ---

def test_analytics_endpoint(monkeypatch):
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", 600)
    store.reset()
    simulator.seed(store, ROUTES)
    for n, level in enumerate(["high", "high", "medium"]):
        client.post("/api/reports", json={"route_id": "5", "bus_id": f"5-{n + 1}", "level": level,
                                          "client_id": f"phone-{n}"})
    body = client.get("/api/operator/analytics").json()
    assert len(body["timeline"]) == config.ANALYTICS_MINUTES
    last = body["timeline"][-1]
    assert (last["low"], last["medium"], last["high"]) == (0, 1, 2)
    assert body["top_routes"][0]["route_id"] == "5"
    assert body["top_routes"][0]["high_share"] == pytest.approx(2 / 3, abs=0.01)
    assert body["density_index"] == 83  # scores 3,3,2 -> 2.67 -> 83


# --- Time-ranged queries ---

def test_reports_for_route_since(db):
    add(db, "5", "low", 60)
    add(db, "5", "high", 5)
    assert [r.level for r in db.reports_for_route("5")] == ["low", "high"]
    assert [r.level for r in db.reports_for_route("5", since=NOW - timedelta(minutes=10))] == ["high"]


def test_density_still_reports_all_time_last_report(db):
    add(db, "5", "high", 60)
    d = density.route_summary(db, db.routes["5"], NOW)
    assert d.counts["high"] == 0
    assert d.last_report_at == NOW - timedelta(minutes=60)


def test_report_indexes_exist(db):
    names = {row[0] for row in db.db.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    assert {"idx_reports_route_time", "idx_reports_time", "idx_reports_client_bus"} <= names


def test_anomaly_ignores_stale_runs(db):
    for minutes_ago in (90, 85, 80):  # an old high run spanning 10 min, nothing since
        add(db, "5", "high", minutes_ago)
    assert anomaly.check_route(db, "5", now=NOW) is None


def test_anomaly_detects_run_longer_than_lookback(db):
    for minutes_ago in (40, 30, 20, 10, 0):  # run started before the 21-min lookback
        add(db, "5", "high", minutes_ago)
    assert anomaly.check_route(db, "5", now=NOW) is not None
