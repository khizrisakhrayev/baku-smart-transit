from fastapi.testclient import TestClient

from app import config, simulator
from app.main import app
from app.routes_data import ROUTES

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_frontend_served():
    assert client.get("/passenger.html").status_code == 200


def test_startup_seeds_routes_and_buses():
    with TestClient(app) as started:
        assert len(started.get("/api/routes").json()) == len(ROUTES)
        assert len(started.get("/api/buses").json()) == len(ROUTES) * config.BUSES_PER_ROUTE
