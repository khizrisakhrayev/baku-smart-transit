import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import anomaly, config, density, simulator
from app.main import app
from app.models import ReportIn
from app.routes_data import ROUTES
from app.store import store, utcnow

client = TestClient(app)  # no lifespan: background loops not running


@pytest.fixture(autouse=True)
def fresh_store(monkeypatch):
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", 600)
    store.reset()
    simulator.seed(store, ROUTES)


def report(level: str, route_id: str = "5", bus_id: str = "5-1"):
    return client.post("/api/reports", json={
        "route_id": route_id, "bus_id": bus_id, "level": level, "client_id": uuid.uuid4().hex,
    })


def density_of(route_id: str) -> dict:
    return next(d for d in client.get("/api/operator/density").json() if d["route_id"] == route_id)


# --- Density overview ---

def test_density_without_reports():
    d = density_of("1")
    assert d["dominant_level"] is None
    assert d["counts"] == {"low": 0, "medium": 0, "high": 0}
    assert d["bus_count"] == config.BUSES_PER_ROUTE
    assert d["last_report_at"] is None


def test_density_counts_and_dominant_level():
    for level in ("medium", "high", "high", "low"):
        report(level)
    d = density_of("5")
    assert d["counts"] == {"low": 1, "medium": 1, "high": 2}
    assert d["dominant_level"] == "high"
    assert d["last_report_at"] is not None


def test_density_ignores_reports_older_than_window():
    old = utcnow() - timedelta(seconds=1200)
    store.add_report(ReportIn(client_id="test", route_id="5", bus_id="5-1", level="high"), timestamp=old)
    d = density_of("5")
    assert d["counts"]["high"] == 0
    assert d["dominant_level"] is None
    assert d["last_report_at"] is not None


def test_dominant_level_tie_goes_to_more_crowded():
    assert density.dominant_level({"low": 2, "medium": 2, "high": 0}) == "medium"
    assert density.dominant_level({"low": 0, "medium": 0, "high": 0}) is None


# --- Alerts ---

def test_new_report_triggers_alert(monkeypatch):
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", 0)
    for _ in range(3):
        report("high")
    report("high")  # still only one active alert
    alerts = client.get("/api/operator/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["route_id"] == "5"
    assert alerts[0]["message"] == "Əlavə avtobus ehtiyatı ayrılmalıdır"


def test_no_alert_before_window_elapsed():
    for _ in range(3):
        report("high")
    assert client.get("/api/operator/alerts").json() == []


def test_resolve_alert_and_active_first():
    first = client.post("/api/demo/flood-high", params={"route_id": "1"}).json()["alert"]
    client.post("/api/demo/flood-high", params={"route_id": "88"})
    response = client.post(f"/api/operator/alerts/{first['id']}/resolve")
    assert response.status_code == 200
    assert response.json()["resolved_at"] is not None
    alerts = client.get("/api/operator/alerts").json()
    assert [a["route_id"] for a in alerts] == ["88", "1"]


def test_resolve_unknown_alert():
    assert client.post("/api/operator/alerts/999/resolve").status_code == 404


# --- Demo flood ---

def test_flood_high_creates_alert_immediately():
    response = client.post("/api/demo/flood-high", params={"route_id": "88"})
    assert response.status_code == 200
    body = response.json()
    assert body["reports_added"] == config.MIN_HIGH_REPORTS + 1
    assert body["alert"]["route_id"] == "88"
    buses = [b for b in client.get("/api/buses").json() if b["route_id"] == "88"]
    assert all(b["density"] == "high" for b in buses)


def test_flood_shows_high_reports_in_density():
    client.post("/api/demo/flood-high", params={"route_id": "88"})
    d = density_of("88")
    assert d["counts"]["high"] == config.MIN_HIGH_REPORTS
    assert d["dominant_level"] == "high"


def test_flood_again_after_resolve_reopens_alert():
    alert = client.post("/api/demo/flood-high", params={"route_id": "65"}).json()["alert"]
    client.post(f"/api/operator/alerts/{alert['id']}/resolve")
    again = client.post("/api/demo/flood-high", params={"route_id": "65"}).json()["alert"]
    assert again is not None and again["id"] != alert["id"]


def test_flood_unknown_route():
    assert client.post("/api/demo/flood-high", params={"route_id": "999"}).status_code == 404


def test_pending_endpoint():
    report("high", route_id="5", bus_id="5-1")
    body = client.get("/api/operator/pending").json()
    assert body["window_sec"] == 600 and body["required_reports"] == config.MIN_HIGH_REPORTS
    assert [(p["route_id"], p["high_reports"]) for p in body["routes"]] == [("5", 1)]
    assert 590 <= body["routes"][0]["seconds_remaining"] <= 600
