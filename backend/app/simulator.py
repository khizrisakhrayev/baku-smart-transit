"""GPS simulator: moves buses along their routes every 2 seconds.

Each route is driven as a round trip: A→B→C→D→C→B→(A again). A bus sits between two
consecutive stops of that path and advances 1/STEPS_PER_SEGMENT of the way each tick,
so it reaches the next stop every STEPS_PER_SEGMENT * TICK_SECONDS seconds (see config.py).
"""
import asyncio
import random

from app import config, events
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


def create_buses(route: Route, count: int | None = None,
                 rng: random.Random | None = None) -> list[Bus]:
    """Create `count` buses (default: the route's bus_count) spread evenly around its round trip.

    With `rng`, the route's buses are shifted together by a random number of simulator
    steps, so different routes don't all reach their stops in sync (no bunching at hubs).
    """
    count = count or route.bus_count
    path = route_path(route)
    total_steps = len(path) * config.STEPS_PER_SEGMENT
    shift = rng.randrange(total_steps) if rng else 0
    buses = []
    for n in range(count):
        step = (n * total_steps // count + shift) % total_steps
        bus = Bus(id=f"{route.id}-{n + 1}", route_id=route.id,
                  path_index=step // config.STEPS_PER_SEGMENT,
                  progress=(step % config.STEPS_PER_SEGMENT) / config.STEPS_PER_SEGMENT,
                  lat=0, lon=0)
        update_position(bus, path)
        buses.append(bus)
    return buses


def update_position(bus: Bus, path: list[Stop]) -> None:
    """Set lat/lon from the bus's place on the path."""
    current = path[bus.path_index]
    following = path[(bus.path_index + 1) % len(path)]
    bus.lat, bus.lon = interpolate(current, following, bus.progress)


def step_bus(bus: Bus, route: Route) -> None:
    """Advance one tick and update the bus's coordinates."""
    path = route_path(route)
    bus.progress += 1 / config.STEPS_PER_SEGMENT
    if bus.progress >= 1 - 1e-9:  # arrived at next stop
        bus.path_index = (bus.path_index + 1) % len(path)
        bus.progress = 0.0
    update_position(bus, path)


def tick(store: Store) -> None:
    """Move every bus in the store one step."""
    for bus in store.buses.values():
        step_bus(bus, store.routes[bus.route_id])


def seed(store: Store, routes: list[Route]) -> None:
    """Load routes into the store and place their buses (random offsets, seeded)."""
    rng = random.Random(config.SIM_SEED)
    for route in routes:
        store.add_route(route)
        for bus in create_buses(route, rng=rng):
            store.add_bus(bus)


async def run(store: Store, interval: float = config.TICK_SECONDS) -> None:
    """Background loop: tick forever until cancelled; push new positions to live streams."""
    while True:
        await asyncio.sleep(interval)
        tick(store)
        if events.has_subscribers():
            events.publish("buses", buses_payload(store))


def buses_payload(store: Store) -> list[dict]:
    return [bus.model_dump(mode="json") for bus in store.buses.values()]
