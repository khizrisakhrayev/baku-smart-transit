"""End-to-end flow through the HTTP API only:
passenger reports -> density -> pending -> alert with recommendation -> dispatch -> resolved.

The anomaly window is shortened to 1 second, so the "high" run really has to last that long
(the test waits ~1.2s in total); everything else is exactly what the app does in production.
"""
import time

import pytest
from fastapi.testclient import TestClient

from app import anomaly, config, simulator
from app.main import app
from app.routes_data import ROUTES
from app.store import store

client = TestClient(app)
TARGET, DONOR = "5", "8"  # route 5 passes 28 May and Gənclik; route 8 passes no hub


@pytest.fixture(autouse=True)
def fresh_network(monkeypatch):
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", 1)
    store.reset()
    simulator.seed(store, ROUTES)


def report(route_id: str, bus_id: str, level: str, client_id: str):
    response = client.post("/api/reports", json={
        "route_id": route_id, "bus_id": bus_id, "level": level, "client_id": client_id})
    assert response.status_code == 201, response.text
    return response.json()


def overview() -> dict:
    return client.get("/api/operator/overview").json()


def route_entry(items: list[dict], route_id: str) -> dict | None:
    return next((item for item in items if item["route_id"] == route_id), None)


def test_report_to_resolved_alert():
    # 1. A passenger on route 8 says it is quiet: that makes it the best donor.
    report(DONOR, "8-1", "low", "phone-donor")

    # 2. Two passengers on route 5 report "high": density turns high, the route is
    #    watched (pending) but there is no alert yet.
    report(TARGET, "5-1", "high", "phone-1")
    time.sleep(0.6)
    report(TARGET, "5-2", "high", "phone-2")
    data = overview()
    assert route_entry(data["densities"], TARGET)["dominant_level"] == "high"
    assert route_entry(data["pending"]["routes"], TARGET)["high_reports"] == 2
    assert data["alerts"] == []

    # 3. A third "high" report after the window has passed: the alert opens, with a
    #    smart-dispatch recommendation naming the quiet donor route.
    time.sleep(0.6)
    report(TARGET, "5-3", "high", "phone-3")
    alerts = client.get("/api/operator/alerts").json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["route_id"] == TARGET and alert["resolved_at"] is None
    assert alert["message"] == anomaly.ALERT_MESSAGE
    assert alert["donor_route_id"] == DONOR
    assert alert["recommendation"] == f"Tövsiyə: Marşrut {DONOR} → Marşrut {TARGET} (1 avtobus yönləndirin)"
    data = overview()
    assert route_entry(data["pending"]["routes"], TARGET) is None  # now a real alert

    # 4. The operator confirms: one bus moves from route 8 to route 5.
    buses_before = {r: store.routes[r].bus_count for r in (TARGET, DONOR)}
    response = client.post(f"/api/operator/alerts/{alert['id']}/dispatch")
    assert response.status_code == 200
    moved = response.json()["bus"]
    assert moved["id"].startswith(f"{DONOR}-") and moved["route_id"] == TARGET

    buses = client.get("/api/buses").json()
    assert sum(b["route_id"] == TARGET for b in buses) == buses_before[TARGET] + 1
    assert sum(b["route_id"] == DONOR for b in buses) == buses_before[DONOR] - 1

    # 5. The alert is resolved, records the moved bus, and is not reopened by the old run.
    resolved = client.get("/api/operator/alerts").json()[0]
    assert resolved["resolved_at"] is not None
    assert resolved["dispatched_bus_id"] == moved["id"]
    anomaly.check_all(store)
    data = overview()
    assert [a for a in data["alerts"] if a["resolved_at"] is None] == []
    assert route_entry(data["pending"]["routes"], TARGET) is None

    # 6. The moved bus keeps driving on its new route.
    for _ in range(config.STEPS_PER_SEGMENT):
        simulator.tick(store)
    assert store.buses[moved["id"]].path_index == 1
