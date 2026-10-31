"""Operator overview: same numbers as the single endpoints, from a constant number of queries."""
import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import anomaly, config, density, forecast, overview, simulator
from app.main import app
from app.models import ReportIn
from app.routes_data import ROUTES
from app.store import Store, store

NOW = datetime(2026, 10, 31, 17, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(monkeypatch) -> Store:
    """A network with a mix of states: active alert, resolved alert, pending, calm, old data."""
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", 600)
    db = Store()
    simulator.seed(db, ROUTES)

    def add(route_id, level, minutes_ago, client):
        bus_id = db.buses_on_route(route_id)[0].id
        db.add_report(ReportIn(route_id=route_id, bus_id=bus_id, level=level, client_id=client),
                      timestamp=NOW - timedelta(minutes=minutes_ago))

    for n, minutes in enumerate((12, 8, 4, 0)):  # route 5: active alert
        add("5", "high", minutes, f"a{n}")
    db.create_alert("5", anomaly.ALERT_MESSAGE, NOW)
    for n, minutes in enumerate((9, 2)):         # route 88: pending (2 high so far)
        add("88", "high", minutes, f"b{n}")
    add("1", "low", 1, "c")                      # route 1: calm
    add("65", "medium", 7, "d")                  # route 65: medium, rising
    add("65", "high", 1, "e")
    add("30", "high", 90, "f")                   # route 30: only old data
    old = db.create_alert("30", anomaly.ALERT_MESSAGE, NOW - timedelta(minutes=80))
    db.resolve_alert(old.id, resolved_at=NOW - timedelta(minutes=70))
    return db


def test_overview_matches_single_endpoints(db):
    result = overview.build(db, NOW)
    assert result.densities == density.summary(db, NOW)
    assert result.forecasts == forecast.summary(db, NOW)
    assert result.pending == anomaly.pending(db, NOW)
    assert result.alerts == db.list_alerts()
    assert [r.id for r in result.routes] == [r.id for r in ROUTES]
    assert len(result.buses) == len(db.buses)


def test_overview_sees_the_mixed_states(db):
    result = overview.build(db, NOW)
    assert sorted(p.route_id for p in result.pending.routes) == ["65", "88"]  # latest report high, no alert
    assert {a.route_id for a in result.alerts if a.resolved_at is None} == {"5"}
    by_route = {d.route_id: d for d in result.densities}
    assert by_route["1"].dominant_level == "low"
    assert by_route["30"].dominant_level is None and by_route["30"].last_report_at is not None


def count_queries(db: Store, action) -> int:
    statements = []
    db.db.set_trace_callback(statements.append)
    try:
        action()
    finally:
        db.db.set_trace_callback(None)
    return len(statements)


def test_overview_uses_a_constant_number_of_queries(db):
    batched = count_queries(db, lambda: overview.build(db, NOW))
    one_by_one = count_queries(db, lambda: (density.summary(db, NOW), forecast.summary(db, NOW),
                                            anomaly.pending(db, NOW), db.list_alerts()))
    assert batched == 3
    assert one_by_one > 10 * len(ROUTES) / 5  # the per-route path runs many more


def test_overview_endpoint():
    store.reset()
    simulator.seed(store, ROUTES)
    body = TestClient(app).get("/api/operator/overview").json()
    assert set(body) == {"routes", "buses", "densities", "forecasts", "pending", "alerts"}
    assert len(body["routes"]) == len(ROUTES) and body["routes"][0]["stops"]
    assert len(body["densities"]) == len(body["forecasts"]) == len(ROUTES)


def test_store_is_safe_under_concurrent_use():
    """Regression: many threads sharing the one connection used to corrupt reads."""
    db = Store()
    simulator.seed(db, ROUTES)
    errors = []

    def worker(n):
        try:
            for i in range(30):
                db.add_report(ReportIn(route_id="5", bus_id="5-1", level="high", client_id=f"t{n}-{i}"))
                overview.build(db)
        except Exception as error:  # noqa: BLE001 - any failure is the bug
            errors.append(error)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(db.reports_for_route("5")) == 8 * 30
