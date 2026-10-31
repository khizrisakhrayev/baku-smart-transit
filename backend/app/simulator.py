"""GPS simulator: moves buses along their routes every 2 seconds.

Each route is driven as a round trip: A→B→C→D→C→B→(A again). A bus sits between two
consecutive stops of that path and advances 1/STEPS_PER_SEGMENT of the way each tick,
so it reaches the next stop every STEPS_PER_SEGMENT * TICK_SECONDS seconds (see config.py).
"""
import asyncio

from app import config
from app.models import Bus, Route, Stop
from app.store import Store


def route_path(route: Route) -> list[Stop]:
    """Round-trip stop sequence: forward, then back without repeating the end stops."""
    return route.stops + route.stops[-2:0:-1]


def interpolate(a: Stop, b: Stop, t: float) -> tuple[float, float]:
    """Point `t` (0..1) of the way from stop a to stop b."""
    return a.lat + (b.lat - a.lat) * t, a.lon + (b.lon - a.lon) * t


def next_stop(bus: Bus, route: Route) -> Stop:
    path = route_path(route)
    return path[(bus.path_index + 1) % len(path)]


def create_buses(route: Route, count: int = config.BUSES_PER_ROUTE) -> list[Bus]:
    """Create `count` buses spread evenly around the route's round trip."""
    path = route_path(route)
    buses = []
    for n in range(count):
        index = n * len(path) // count
        stop = path[index]
        buses.append(Bus(id=f"{route.id}-{n + 1}", route_id=route.id,
                         path_index=index, lat=stop.lat, lon=stop.lon))
    return buses


def step_bus(bus: Bus, route: Route) -> None:
    """Advance one tick and update the bus's coordinates."""
    path = route_path(route)
    bus.progress += 1 / config.STEPS_PER_SEGMENT
    if bus.progress >= 1 - 1e-9:  # arrived at next stop
        bus.path_index = (bus.path_index + 1) % len(path)
        bus.progress = 0.0
    current = path[bus.path_index]
    following = path[(bus.path_index + 1) % len(path)]
    bus.lat, bus.lon = interpolate(current, following, bus.progress)


def tick(store: Store) -> None:
    """Move every bus in the store one step."""
    for bus in store.buses.values():
        step_bus(bus, store.routes[bus.route_id])


def seed(store: Store, routes: list[Route]) -> None:
    """Load routes into the store and place their buses."""
    for route in routes:
        store.add_route(route)
        for bus in create_buses(route):
            store.add_bus(bus)


async def run(store: Store, interval: float = config.TICK_SECONDS) -> None:
    """Background loop: tick forever until cancelled."""
    while True:
        await asyncio.sleep(interval)
        tick(store)
