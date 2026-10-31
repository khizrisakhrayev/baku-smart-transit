"""In-memory state: routes, live bus positions and density reports.

(SQLite persistence for reports and alerts will be added here later.)
"""
from datetime import datetime, timezone

from app.models import Bus, Report, ReportIn, Route


class Store:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Clear all state (used by tests)."""
        self.routes: dict[str, Route] = {}
        self.buses: dict[str, Bus] = {}
        self.reports: list[Report] = []

    def add_route(self, route: Route) -> None:
        self.routes[route.id] = route

    def add_bus(self, bus: Bus) -> None:
        self.buses[bus.id] = bus

    def buses_on_route(self, route_id: str) -> list[Bus]:
        return [b for b in self.buses.values() if b.route_id == route_id]

    def routes_with_stop(self, stop_id: str) -> list[Route]:
        return [r for r in self.routes.values() if any(s.id == stop_id for s in r.stops)]

    def add_report(self, report_in: ReportIn) -> Report:
        """Timestamp and save a report, and set it as the bus's current density."""
        report = Report(**report_in.model_dump(), timestamp=datetime.now(timezone.utc))
        self.reports.append(report)
        self.buses[report.bus_id].density = report.level
        return report


# Shared app-wide instance.
store = Store()
