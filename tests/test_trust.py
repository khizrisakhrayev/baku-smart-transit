"""Report trust: rate limit, distance check, freshness weighting and confidence."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config, density, simulator, trust
from app.main import app
from app.models import Bus, Report, ReportIn
from app.routes_data import ROUTES
from app.store import Store, store, utcnow

T0 = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
WINDOW = 600


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def report_in(client_id="a", bus_id="5-1", level="high", lat=None, lon=None) -> ReportIn:
    return ReportIn(route_id="5", bus_id=bus_id, level=level, client_id=client_id, lat=lat, lon=lon)


# --- Rate limit ---

@pytest.fixture
def db() -> Store:
    return Store()


def test_second_report_within_cooldown_is_limited(db):
    db.add_report(report_in(), timestamp=at(0))
    assert trust.is_rate_limited(db, "a", "5-1", now=at(30))


def test_report_after_cooldown_is_allowed(db):
    db.add_report(report_in(), timestamp=at(0))
    assert not trust.is_rate_limited(db, "a", "5-1", now=at(config.REPORT_COOLDOWN_SEC + 1))


def test_rate_limit_is_per_client_and_per_bus(db):
    db.add_report(report_in(), timestamp=at(0))
    assert not trust.is_rate_limited(db, "b", "5-1", now=at(10))  # other client
    assert not trust.is_rate_limited(db, "a", "5-2", now=at(10))  # other bus


def test_first_report_is_never_limited(db):
    assert not trust.is_rate_limited(db, "a", "5-1", now=at(0))


# --- Distance check ---

BUS = Bus(id="5-1", route_id="5", lat=40.3660, lon=49.8317)


def test_distance_of_known_offset():
    # 0.01° of latitude is about 1.11 km.
    assert trust.distance_m(40.0, 49.0, 40.01, 49.0) == pytest.approx(1112, abs=5)


def test_report_without_location_is_accepted():
    assert not trust.is_too_far(report_in(), BUS)


def test_report_near_bus_is_accepted():
    assert not trust.is_too_far(report_in(lat=40.3680, lon=49.8317), BUS)  # ~220 m


def test_report_far_from_bus_is_rejected():
    assert trust.is_too_far(report_in(lat=40.3760, lon=49.8317), BUS)  # ~1.1 km


def test_distance_check_can_be_disabled(monkeypatch):
    monkeypatch.setattr(config, "MAX_REPORT_DISTANCE_M", 0)
    assert not trust.is_too_far(report_in(lat=41.0, lon=49.0), BUS)


def test_lat_without_lon_is_invalid():
    with pytest.raises(ValueError):
        report_in(lat=40.0)


# --- Freshness weighting ---

@pytest.mark.parametrize("age, weight", [(0, 1.0), (150, 0.75), (300, 0.5), (600, 0.0), (900, 0.0)])
def test_freshness_falls_linearly_to_zero(age, weight):
    assert trust.freshness_weight(at(0), at(age), WINDOW) == pytest.approx(weight)


def test_future_timestamp_is_capped_at_one():
    assert trust.freshness_weight(at(10), at(0), WINDOW) == 1.0


def test_fresh_low_outweighs_old_highs(db, monkeypatch):
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", WINDOW)
    route = next(r for r in ROUTES if r.id == "5")
    db.add_route(route)
    for client in ("a", "b"):
        db.add_report(report_in(client_id=client, level="high"), timestamp=at(0))
    db.add_report(report_in(client_id="c", level="low"), timestamp=at(500))
    summary = density.route_summary(db, route, now=at(500))
    assert summary.counts == {"low": 1, "medium": 0, "high": 2}
    assert summary.weighted_counts["high"] == pytest.approx(0.33, abs=0.01)  # 2 × 1/6
    assert summary.dominant_level == "low"


# --- Confidence ---

def reports_from(clients: list[str], age: float) -> tuple[list[Report], datetime]:
    """One report per client made at T0, and the time `age` seconds later."""
    return [Report(route_id="5", bus_id="5-1", level="high", client_id=c, timestamp=at(0)) for c in clients], at(age)


def test_no_reports_means_zero_confidence():
    assert trust.confidence([], at(0), WINDOW) == 0.0


def test_one_fresh_reporter_gives_low_confidence():
    reports, now = reports_from(["a"], age=0)
    assert trust.confidence(reports, now, WINDOW) == pytest.approx(1 / config.CONFIDENT_CLIENTS)


def test_same_client_repeating_does_not_raise_confidence():
    reports, now = reports_from(["a", "a", "a"], age=0)
    assert trust.confidence(reports, now, WINDOW) == pytest.approx(1 / config.CONFIDENT_CLIENTS)


def test_many_fresh_reporters_give_full_confidence():
    reports, now = reports_from(["a", "b", "c", "d", "e"], age=0)
    assert trust.confidence(reports, now, WINDOW) == 1.0


def test_old_reports_lower_confidence():
    reports, now = reports_from(["a", "b", "c", "d", "e"], age=300)
    assert trust.confidence(reports, now, WINDOW) == pytest.approx(0.5)


# --- API ---

client = TestClient(app)


@pytest.fixture
def api_store(monkeypatch):
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", WINDOW)
    store.reset()
    simulator.seed(store, ROUTES)
    return store


def post(client_id="phone-1", bus_id="5-1", **extra):
    payload = {"route_id": "5", "bus_id": bus_id, "level": "high", "client_id": client_id, **extra}
    return client.post("/api/reports", json=payload)


def test_api_rate_limit_returns_429(api_store):
    assert post().status_code == 201
    response = post()
    assert response.status_code == 429
    assert "artıq bildiriş" in response.json()["detail"]
    assert post(client_id="phone-2").status_code == 201
    assert post(bus_id="5-2").status_code == 201


def test_api_rejects_report_far_from_bus(api_store):
    bus = api_store.buses["5-1"]
    response = post(lat=bus.lat + 0.01, lon=bus.lon)
    assert response.status_code == 422
    assert response.json()["detail"] == "Avtobusdan çox uzaqdasınız"
    assert api_store.reports_for_route("5") == []


def test_api_accepts_report_near_bus(api_store):
    bus = api_store.buses["5-1"]
    assert post(lat=bus.lat + 0.001, lon=bus.lon).status_code == 201


def test_rejected_far_report_does_not_count_for_rate_limit(api_store):
    bus = api_store.buses["5-1"]
    post(lat=bus.lat + 0.01, lon=bus.lon)
    assert post().status_code == 201


def test_density_api_exposes_confidence(api_store):
    for n in range(3):
        post(client_id=f"phone-{n}")
    d = next(d for d in client.get("/api/operator/density").json() if d["route_id"] == "5")
    assert d["confidence"] == pytest.approx(3 / config.CONFIDENT_CLIENTS, abs=0.01)
    assert d["weighted_counts"]["high"] == pytest.approx(3, abs=0.01)


def test_demo_flood_uses_distinct_clients(api_store):
    client.post("/api/demo/flood-high", params={"route_id": "88"})
    reports = api_store.reports_for_route("88")
    assert len({r.client_id for r in reports}) == len(reports)
    d = next(d for d in client.get("/api/operator/density").json() if d["route_id"] == "88")
    assert d["dominant_level"] == "high"
    assert d["confidence"] > 0


def test_old_database_reports_get_client_id(tmp_path):
    import sqlite3
    db_file = str(tmp_path / "old.db")
    old = sqlite3.connect(db_file)
    old.execute("CREATE TABLE reports (id INTEGER PRIMARY KEY AUTOINCREMENT, route_id TEXT NOT NULL, "
                "bus_id TEXT NOT NULL, level TEXT NOT NULL, timestamp TEXT NOT NULL)")
    old.execute("INSERT INTO reports (route_id, bus_id, level, timestamp) VALUES ('5', '5-1', 'low', ?)",
                (T0.isoformat(),))
    old.commit()
    old.close()
    assert [r.client_id for r in Store(db_file).reports_for_route("5")] == ["unknown"]
