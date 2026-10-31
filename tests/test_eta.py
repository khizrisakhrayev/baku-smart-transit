import pytest

from app import eta
from app.models import Bus, Route, Stop
from app.store import Store


@pytest.fixture
def route() -> Route:
    """3-stop route: round-trip path is a(0), b(1), c(2), b(3)."""
    return Route(id="T", name="Test", stops=[
        Stop(id="a", name="A", lat=40.0, lon=49.0),
        Stop(id="b", name="B", lat=40.1, lon=49.1),
        Stop(id="c", name="C", lat=40.2, lon=49.2),
    ])


def bus_at(path_index: int, progress: float = 0.0) -> Bus:
    return Bus(id="T-1", route_id="T", path_index=path_index, progress=progress, lat=0, lon=0)


def test_bus_at_stop_has_zero_eta(route):
    assert eta.segments_until_stop(bus_at(1), route, "b") == 0


def test_eta_counts_remaining_segments(route):
    assert eta.segments_until_stop(bus_at(0), route, "c") == 2
    assert eta.segments_until_stop(bus_at(0, progress=0.4), route, "c") == pytest.approx(1.6)


def test_eta_uses_soonest_visit_on_round_trip(route):
    # Bus at c heading back: next visit to b is 1 segment away (return leg).
    assert eta.segments_until_stop(bus_at(2), route, "b") == 1


def test_eta_wraps_after_passing_stop(route):
    # Bus just left a: must go a->b->c->b->a = 4 segments, minus progress made.
    assert eta.segments_until_stop(bus_at(0, progress=0.2), route, "a") == pytest.approx(3.8)


def test_stop_not_on_route(route):
    assert eta.segments_until_stop(bus_at(0), route, "zzz") is None
    assert eta.eta_minutes(bus_at(0), route, "zzz") is None


def test_eta_minutes_uses_simulator_speed(route):
    expected = 2 * eta.SEGMENT_SECONDS / 60
    assert eta.eta_minutes(bus_at(0), route, "c") == round(expected, 1)


def test_etas_for_stop_sorted_with_density(route):
    store = Store()
    store.add_route(route)
    store.add_bus(Bus(id="T-1", route_id="T", path_index=0, lat=0, lon=0))
    store.add_bus(Bus(id="T-2", route_id="T", path_index=1, lat=0, lon=0, density="high"))
    result = eta.etas_for_stop(store, "c")
    assert [e.bus_id for e in result] == ["T-2", "T-1"]
    assert result[0].density == "high"
    assert result[1].density is None
