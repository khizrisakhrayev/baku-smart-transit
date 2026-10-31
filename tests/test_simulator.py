import asyncio

import pytest

from app import config, simulator
from app.models import Route, Stop
from app.routes_data import ROUTES
from app.store import Store


@pytest.fixture
def route() -> Route:
    """Simple 3-stop route: path is A, B, C, B."""
    return Route(id="T", name="Test", stops=[
        Stop(id="a", name="A", lat=40.0, lon=49.0),
        Stop(id="b", name="B", lat=40.1, lon=49.1),
        Stop(id="c", name="C", lat=40.2, lon=49.2),
    ])


def step_n(bus, route, n):
    for _ in range(n):
        simulator.step_bus(bus, route)


def test_route_path_is_round_trip(route):
    assert [s.name for s in simulator.route_path(route)] == ["A", "B", "C", "B"]


def test_create_buses_spread_along_route(route):
    buses = simulator.create_buses(route, count=2)
    assert [b.id for b in buses] == ["T-1", "T-2"]
    assert [b.path_index for b in buses] == [0, 2]
    assert (buses[1].lat, buses[1].lon) == (40.2, 49.2)


def test_bus_moves_between_stops(route):
    bus = simulator.create_buses(route, count=1)[0]
    simulator.step_bus(bus, route)
    assert bus.path_index == 0
    assert 40.0 < bus.lat < 40.1
    assert 49.0 < bus.lon < 49.1


def test_bus_reaches_next_stop(route):
    bus = simulator.create_buses(route, count=1)[0]
    step_n(bus, route, config.STEPS_PER_SEGMENT)
    assert bus.path_index == 1
    assert bus.progress == 0.0
    assert (bus.lat, bus.lon) == pytest.approx((40.1, 49.1))


def test_bus_turns_back_at_terminus(route):
    bus = simulator.create_buses(route, count=1)[0]
    step_n(bus, route, 2 * config.STEPS_PER_SEGMENT)  # now at C
    assert simulator.next_stop(bus, route).name == "B"


def test_bus_completes_full_loop(route):
    bus = simulator.create_buses(route, count=1)[0]
    step_n(bus, route, 4 * config.STEPS_PER_SEGMENT)
    assert bus.path_index == 0
    assert (bus.lat, bus.lon) == pytest.approx((40.0, 49.0))


def test_seed_and_tick_move_all_buses():
    store = Store()
    simulator.seed(store, ROUTES)
    assert len(store.routes) == len(ROUTES)
    assert len(store.buses) == sum(r.bus_count for r in ROUTES)
    before = {b.id: (b.lat, b.lon) for b in store.buses.values()}
    simulator.tick(store)
    assert all((b.lat, b.lon) != before[b.id] for b in store.buses.values())


def test_run_loop_ticks_in_background():
    store = Store()
    simulator.seed(store, ROUTES)

    async def run_briefly():
        task = asyncio.create_task(simulator.run(store, interval=0.01))
        await asyncio.sleep(0.05)
        task.cancel()

    asyncio.run(run_briefly())
    assert any(b.progress > 0 or b.path_index > 0 for b in store.buses.values())


def test_each_route_gets_its_own_fleet_size():
    store = Store()
    simulator.seed(store, ROUTES)
    for route in ROUTES:
        assert len(store.buses_on_route(route.id)) == route.bus_count


def test_segment_takes_about_30_seconds_on_the_map():
    assert config.STEPS_PER_SEGMENT * config.TICK_SECONDS == 30
