"""Smart dispatch: donor selection (unit) and the dispatch endpoint (API)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import anomaly, config, dispatch, simulator
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


def add_reports(route_id: str, *levels: str) -> None:
    bus_id = store.buses_on_route(route_id)[0].id
    for level in levels:
        store.add_report(ReportIn(client_id="test", route_id=route_id, bus_id=bus_id, level=level))


def make_only_eligible(*route_ids: str) -> None:
    """Mark every other route as crowded so only `route_ids` (and the target) can donate."""
    for route in ROUTES:
        if route.id not in route_ids and route.id != "5":
            add_reports(route.id, "high")


# --- Donor selection ---

def test_prefers_route_with_most_low_reports():
    add_reports("8", "low", "low")
    add_reports("11", "low")
    assert dispatch.choose_donor(store, "5") == "8"


def test_route_without_reports_is_eligible():
    make_only_eligible("67")
    assert dispatch.choose_donor(store, "5") == "67"


def test_low_beats_no_data():
    make_only_eligible("67", "77")
    add_reports("77", "low")
    assert dispatch.choose_donor(store, "5") == "77"


def test_target_route_is_never_donor():
    add_reports("5", "low", "low", "low")
    assert dispatch.choose_donor(store, "5") != "5"


def test_crowded_routes_are_excluded():
    add_reports("8", "low", "low", "high", "high", "high")  # dominant: high
    add_reports("11", "low")
    assert dispatch.choose_donor(store, "5") == "11"


def test_route_with_too_few_buses_is_excluded():
    add_reports("8", "low", "low")
    add_reports("11", "low")
    del store.buses[store.buses_on_route("8")[-1].id]  # route 8 now has 2 buses
    assert dispatch.choose_donor(store, "5") == "11"


def test_route_with_active_alert_is_excluded():
    add_reports("8", "low", "low")
    add_reports("11", "low")
    store.create_alert("8", anomaly.ALERT_MESSAGE)
    assert dispatch.choose_donor(store, "5") == "11"


def test_no_donor_when_every_route_is_busy():
    make_only_eligible()
    assert dispatch.choose_donor(store, "5") is None


def test_recommendation_text():
    assert dispatch.recommendation_text("8", "5") == "Tövsiyə: Marşrut 8 → Marşrut 5 (1 avtobus yönləndirin)"


def test_new_alert_carries_recommendation():
    add_reports("8", "low", "low")
    now = utcnow()
    for age in (600, 300, 0):
        store.add_report(ReportIn(client_id="test", route_id="5", bus_id="5-1", level="high"), timestamp=now - timedelta(seconds=age))
    alert = anomaly.check_route(store, "5", now)
    assert alert.donor_route_id == "8"
    assert alert.recommendation == dispatch.recommendation_text("8", "5")


# --- Dispatch endpoint ---

def flood(route_id: str) -> dict:
    return client.post("/api/demo/flood-high", params={"route_id": route_id}).json()["alert"]


def test_dispatch_moves_bus_and_resolves_alert():
    add_reports("8", "low", "low")
    alert = flood("5")
    assert alert["donor_route_id"] == "8"

    response = client.post(f"/api/operator/alerts/{alert['id']}/dispatch")
    assert response.status_code == 200
    body = response.json()
    bus = body["bus"]
    assert bus["route_id"] == "5"
    assert bus["density"] is None
    first_stop = store.routes["5"].stops[0]
    assert (bus["lat"], bus["lon"]) == (first_stop.lat, first_stop.lon)
    assert body["alert"]["resolved_at"] is not None
    assert body["alert"]["dispatched_bus_id"] == bus["id"]

    assert len(store.buses_on_route("5")) == store.routes["5"].bus_count + 1
    assert len(store.buses_on_route("8")) == store.routes["8"].bus_count - 1


def test_dispatched_bus_keeps_moving_on_new_route():
    alert = flood("5")
    bus_id = client.post(f"/api/operator/alerts/{alert['id']}/dispatch").json()["bus"]["id"]
    for _ in range(config.STEPS_PER_SEGMENT):
        simulator.tick(store)
    assert store.buses[bus_id].path_index == 1  # reached the 2nd stop of route 5


def test_dispatch_twice_conflicts():
    alert = flood("5")
    client.post(f"/api/operator/alerts/{alert['id']}/dispatch")
    assert client.post(f"/api/operator/alerts/{alert['id']}/dispatch").status_code == 409


def test_dispatch_without_donor_conflicts():
    alert = store.create_alert("5", anomaly.ALERT_MESSAGE)  # no recommendation
    assert client.post(f"/api/operator/alerts/{alert.id}/dispatch").status_code == 409
    assert store.get_alert(alert.id).resolved_at is None


def test_dispatch_when_donor_lost_buses_conflicts():
    alert = flood("5")
    donor_buses = store.buses_on_route(alert["donor_route_id"])
    for bus in donor_buses[config.MIN_DONOR_BUSES - 1:]:  # leave the donor one bus short
        del store.buses[bus.id]
    assert client.post(f"/api/operator/alerts/{alert['id']}/dispatch").status_code == 409


def test_dispatch_unknown_alert():
    assert client.post("/api/operator/alerts/999/dispatch").status_code == 404


def test_alert_list_shows_recommendation():
    add_reports("8", "low")
    flood("5")
    alert = client.get("/api/operator/alerts").json()[0]
    assert alert["recommendation"] == "Tövsiyə: Marşrut 8 → Marşrut 5 (1 avtobus yönləndirin)"


def test_old_database_gets_new_alert_columns(tmp_path):
    import sqlite3
    from app.store import Store
    db_file = str(tmp_path / "old.db")
    old = sqlite3.connect(db_file)
    old.execute("CREATE TABLE alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, route_id TEXT NOT NULL, "
                "message TEXT NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT)")
    old.commit()
    old.close()
    alert = Store(db_file).create_alert("5", "x", donor_route_id="8", recommendation="r")
    assert alert.donor_route_id == "8"
