from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_frontend_served():
    assert client.get("/passenger.html").status_code == 200


def test_startup_seeds_routes_and_buses():
    with TestClient(app) as started:
        assert len(started.get("/api/routes").json()) == 4
        assert len(started.get("/api/buses").json()) == 12
