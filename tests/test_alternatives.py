"""Passenger alternatives: suggestion rules (unit) and the ETA endpoint (API)."""
import pytest
from fastapi.testclient import TestClient

from app import alternatives, config, simulator
from app.main import app
from app.models import BusEta
from app.routes_data import ROUTES
from app.store import store


def bus(bus_id: str, eta: float, density: str | None) -> BusEta:
    return BusEta(bus_id=bus_id, route_id=bus_id.split("-")[0], eta_minutes=eta, density=density)


def suggestion_for(bus_id: str, etas: list[BusEta]):
    return next(e for e in alternatives.annotate(etas) if e.bus_id == bus_id).suggestion


# --- Suggestions ---

def test_suggests_next_bus_on_same_route():
    s = suggestion_for("5-1", [bus("5-1", 2, "high"), bus("5-2", 6, "low")])
    assert (s.bus_id, s.route_id, s.eta_minutes, s.extra_wait_minutes) == ("5-2", "5", 6, 4)
    assert s.density == "low"


def test_suggests_bus_on_other_route_skipping_crowded_ones():
    s = suggestion_for("5-1", [bus("5-1", 2, "high"), bus("5-2", 4, "high"), bus("1-1", 5, "medium")])
    assert (s.bus_id, s.route_id, s.extra_wait_minutes) == ("1-1", "1", 3)


def test_unknown_density_counts_as_alternative():
    s = suggestion_for("5-1", [bus("5-1", 2, "high"), bus("8-1", 3, None)])
    assert s.bus_id == "8-1" and s.density is None


def test_no_suggestion_when_extra_wait_too_long():
    assert suggestion_for("5-1", [bus("5-1", 2, "high"), bus("5-2", 12.5, "low")]) is None


def test_extra_wait_exactly_at_limit_is_suggested():
    limit = config.MAX_EXTRA_WAIT_MIN
    s = suggestion_for("5-1", [bus("5-1", 2, "high"), bus("5-2", 2 + limit, "low")])
    assert s.extra_wait_minutes == limit


def test_no_suggestion_when_no_alternative():
    assert suggestion_for("5-1", [bus("5-1", 2, "high"), bus("5-2", 4, "high")]) is None
    assert suggestion_for("5-1", [bus("5-1", 2, "high")]) is None


def test_calmer_bus_arriving_earlier_is_not_suggested():
    assert suggestion_for("5-1", [bus("1-1", 1, "low"), bus("5-1", 3, "high")]) is None


def test_only_crowded_buses_get_suggestions():
    etas = alternatives.annotate([bus("5-1", 2, "medium"), bus("5-2", 4, "low")])
    assert all(e.suggestion is None for e in etas)


# --- Most comfortable ---

def comfortable(etas: list[BusEta]) -> list[str]:
    return [e.bus_id for e in alternatives.annotate(etas) if e.most_comfortable]


def test_most_comfortable_prefers_low_even_if_later():
    assert comfortable([bus("5-1", 2, "medium"), bus("1-1", 8, "low"), bus("8-1", 9, "low")]) == ["1-1"]


def test_most_comfortable_ignores_buses_beyond_horizon():
    late = config.COMFORT_HORIZON_MIN + 1
    assert comfortable([bus("5-1", 2, "medium"), bus("1-1", late, "low")]) == ["5-1"]


def test_no_most_comfortable_without_known_calm_bus():
    assert comfortable([bus("5-1", 2, "high"), bus("1-1", 4, None)]) == []


# --- API ---

client = TestClient(app)


@pytest.fixture
def seeded():
    store.reset()
    simulator.seed(store, ROUTES)


def test_eta_endpoint_includes_suggestion_and_comfort_flag(seeded):
    # Busy hub stop: make the first arriving bus crowded and every other bus calm.
    first = client.get("/api/stops/28-may/eta").json()[0]
    for b in store.buses.values():
        b.density = "high" if b.id == first["bus_id"] else "low"

    etas = client.get("/api/stops/28-may/eta").json()
    crowded = next(e for e in etas if e["bus_id"] == first["bus_id"])
    assert crowded["suggestion"]["density"] == "low"
    assert 0 <= crowded["suggestion"]["extra_wait_minutes"] <= config.MAX_EXTRA_WAIT_MIN
    assert sum(e["most_comfortable"] for e in etas) == 1
    assert all(e["suggestion"] is None for e in etas if e["density"] != "high")
