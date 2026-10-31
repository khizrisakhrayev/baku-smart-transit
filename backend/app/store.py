"""Application state.

- Routes and live bus positions live in memory (rebuilt by the simulator on startup).
- Density reports and operator alerts are persisted in SQLite (stdlib sqlite3).
Timestamps are stored as UTC ISO-8601 strings, which sort correctly as text.
"""
import sqlite3
from datetime import datetime, timezone

from app.models import Alert, Bus, Report, ReportIn, Route

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id  TEXT NOT NULL,
    bus_id    TEXT NOT NULL,
    level     TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    client_id TEXT NOT NULL DEFAULT 'unknown'
);
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id    TEXT NOT NULL,
    message     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    resolved_at TEXT
);
"""

# Columns added after the first release; added to older data.db files on open.
EXTRA_COLUMNS = {
    "alerts": {"donor_route_id": "TEXT", "recommendation": "TEXT", "dispatched_bus_id": "TEXT"},
    "reports": {"client_id": "TEXT NOT NULL DEFAULT 'unknown'"},
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_text(moment: datetime) -> str:
    return moment.isoformat(timespec="microseconds")


class Store:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.open(db_path)

    def open(self, db_path: str) -> None:
        """(Re)open the SQLite database and clear in-memory routes and buses."""
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self._add_missing_columns()
        self.routes: dict[str, Route] = {}
        self.buses: dict[str, Bus] = {}

    def _add_missing_columns(self) -> None:
        with self.db:
            for table, columns in EXTRA_COLUMNS.items():
                existing = {row["name"] for row in self.db.execute(f"PRAGMA table_info({table})")}
                for column, definition in columns.items():
                    if column not in existing:
                        self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def reset(self) -> None:
        """Start from an empty in-memory database (used by tests)."""
        self.open(":memory:")

    # --- Routes and buses (in memory) ---

    def add_route(self, route: Route) -> None:
        self.routes[route.id] = route

    def add_bus(self, bus: Bus) -> None:
        self.buses[bus.id] = bus

    def buses_on_route(self, route_id: str) -> list[Bus]:
        return [b for b in self.buses.values() if b.route_id == route_id]

    def routes_with_stop(self, stop_id: str) -> list[Route]:
        return [r for r in self.routes.values() if any(s.id == stop_id for s in r.stops)]

    # --- Density reports (SQLite) ---

    def add_report(self, report_in: ReportIn, timestamp: datetime | None = None) -> Report:
        """Timestamp and save a report, and set it as the bus's current density."""
        report = Report(**report_in.model_dump(), timestamp=timestamp or utcnow())
        with self.db:
            self.db.execute(
                "INSERT INTO reports (route_id, bus_id, level, timestamp, client_id) VALUES (?, ?, ?, ?, ?)",
                (report.route_id, report.bus_id, report.level, _to_text(report.timestamp), report.client_id),
            )
        if report.bus_id in self.buses:
            self.buses[report.bus_id].density = report.level
        return report

    def reports_for_route(self, route_id: str) -> list[Report]:
        """All reports of a route, oldest first."""
        rows = self.db.execute(
            "SELECT route_id, bus_id, level, timestamp, client_id FROM reports "
            "WHERE route_id = ? ORDER BY timestamp, id",
            (route_id,),
        )
        return [Report(**dict(row)) for row in rows]

    def last_report_time(self, client_id: str, bus_id: str) -> datetime | None:
        """When this client last reported on this bus (for rate limiting)."""
        row = self.db.execute(
            "SELECT MAX(timestamp) FROM reports WHERE client_id = ? AND bus_id = ?",
            (client_id, bus_id),
        ).fetchone()
        return datetime.fromisoformat(row[0]) if row[0] else None

    # --- Operator alerts (SQLite) ---

    def create_alert(self, route_id: str, message: str, created_at: datetime | None = None,
                     donor_route_id: str | None = None, recommendation: str | None = None) -> Alert:
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO alerts (route_id, message, created_at, donor_route_id, recommendation) "
                "VALUES (?, ?, ?, ?, ?)",
                (route_id, message, _to_text(created_at or utcnow()), donor_route_id, recommendation),
            )
        return self.get_alert(cursor.lastrowid)

    def get_alert(self, alert_id: int) -> Alert | None:
        row = self.db.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        return Alert(**dict(row)) if row else None

    def active_alert(self, route_id: str) -> Alert | None:
        row = self.db.execute(
            "SELECT * FROM alerts WHERE route_id = ? AND resolved_at IS NULL", (route_id,)
        ).fetchone()
        return Alert(**dict(row)) if row else None

    def last_resolved_at(self, route_id: str) -> datetime | None:
        row = self.db.execute(
            "SELECT MAX(resolved_at) FROM alerts WHERE route_id = ?", (route_id,)
        ).fetchone()
        return datetime.fromisoformat(row[0]) if row[0] else None

    def list_alerts(self) -> list[Alert]:
        """Active alerts first, newest first within each group."""
        rows = self.db.execute(
            "SELECT * FROM alerts ORDER BY resolved_at IS NOT NULL, created_at DESC, id DESC"
        )
        return [Alert(**dict(row)) for row in rows]

    def resolve_alert(self, alert_id: int, resolved_at: datetime | None = None,
                      dispatched_bus_id: str | None = None) -> Alert | None:
        """Mark an alert resolved (no-op if already resolved); None if it doesn't exist.
        `dispatched_bus_id` records the bus sent to the route, if any."""
        with self.db:
            self.db.execute(
                "UPDATE alerts SET resolved_at = ?, dispatched_bus_id = ? "
                "WHERE id = ? AND resolved_at IS NULL",
                (_to_text(resolved_at or utcnow()), dispatched_bus_id, alert_id),
            )
        return self.get_alert(alert_id)


# Shared app-wide instance (in-memory until main.py opens the real database file).
store = Store()
