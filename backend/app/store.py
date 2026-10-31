"""In-memory state: routes and live bus positions.

(SQLite persistence for density reports and alerts will be added here later.)
"""
from app.models import Bus, Route


class Store:
    def __init__(self) -> None:
        self.routes: dict[str, Route] = {}
        self.buses: dict[str, Bus] = {}

    def add_route(self, route: Route) -> None:
        self.routes[route.id] = route

    def add_bus(self, bus: Bus) -> None:
        self.buses[bus.id] = bus

    def buses_on_route(self, route_id: str) -> list[Bus]:
        return [b for b in self.buses.values() if b.route_id == route_id]


# Shared app-wide instance.
store = Store()
