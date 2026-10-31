import uuid

import pytest
from fastapi.testclient import TestClient

from app import config, simulator
from app.main import app
from app.routes_data import ROUTES
from app.store import store

client = TestClient(app)  # no lifespan: simulator not running, positions stay fixed


@pytest.fixture(autouse=True)
def fresh_store():
    store.reset()
    simulator.seed(store, ROUTES)


def report(route_id="5", bus_id="5-1", level="high"):
    return client.post("/api/reports", json={
        "route_id": route_id, "bus_id": bus_id, "level": level, "client_id": uuid.uuid4().hex,
    })


def test_stops_of_route():
    response = client.get("/api/stops", params={"route_id": "65"})
    assert response.status_code == 200
    assert [s["id"] for s in response.json()][:2] == ["20-yanvar", "memar-ecemi"]


def test_stops_unknown_route():
    assert client.get("/api/stops", params={"route_id": "999"}).status_code == 404


def test_stops_requires_route_id():
    assert client.get("/api/stops").status_code == 422


def test_eta_for_shared_stop_includes_all_its_routes():
    response = client.get("/api/stops/28-may/eta")
    assert response.status_code == 200
    etas = response.json()
    expected_routes = {r.id for r in ROUTES if any(s.id == "28-may" for s in r.stops)}
    assert len(expected_routes) > 2
    assert {e["route_id"] for e in etas} == expected_routes
    assert len(etas) == sum(r.bus_count for r in ROUTES if r.id in expected_routes)
    minutes = [e["eta_minutes"] for e in etas]
    assert minutes == sorted(minutes)


def test_eta_unknown_stop():
    assert client.get("/api/stops/nowhere/eta").status_code == 404


def test_buses_filtered_by_route():
    buses = client.get("/api/buses", params={"route_id": "65"}).json()
    assert len(buses) == store.routes["65"].bus_count
    assert {b["route_id"] for b in buses} == {"65"}
    assert len(client.get("/api/buses").json()) == sum(r.bus_count for r in ROUTES)


def test_create_report():
    response = report()
    assert response.status_code == 201
    body = response.json()
    assert body["bus_id"] == "5-1" and body["level"] == "high"
    assert "timestamp" in body
    assert len(store.reports_for_route("5")) == 1


def test_report_updates_bus_density_and_eta():
    report(level="medium")
    buses = {b["id"]: b for b in client.get("/api/buses").json()}
    assert buses["5-1"]["density"] == "medium"
    assert buses["5-2"]["density"] is None
    etas = {e["bus_id"]: e for e in client.get("/api/stops/sahil/eta").json()}
    assert etas["5-1"]["density"] == "medium"


@pytest.mark.parametrize("payload", [
    {"route_id": "5", "bus_id": "5-1", "level": "extreme", "client_id": "c"},  # bad level
    {"route_id": "5", "bus_id": "5-1", "client_id": "c"},                        # missing level
    {"route_id": "5", "bus_id": "99-1", "level": "low", "client_id": "c"},       # unknown bus
    {"route_id": "1", "bus_id": "5-1", "level": "low", "client_id": "c"},        # bus not on route
    {"route_id": "5", "bus_id": "5-1", "level": "low"},                          # missing client_id
    {"route_id": "5", "bus_id": "5-1", "level": "low", "client_id": ""},         # empty client_id
])
def test_invalid_report_rejected(payload):
    assert client.post("/api/reports", json=payload).status_code == 422
    assert all(store.reports_for_route(r.id) == [] for r in ROUTES)
