"""Application state.

- Routes and live bus positions live in memory (rebuilt by the simulator on startup).
- Density reports and operator alerts are persisted in SQLite (stdlib sqlite3).
Timestamps are stored as UTC ISO-8601 strings, which sort correctly as text.

Thread safety: one SQLite connection is shared by the request thread pool and the
background tasks, so every statement runs through _query/_write while holding a lock,
and rows are fully fetched before the lock is released.
"""
import sqlite3
import threading
from datetime import datetime, timezone

from app import events
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

# Indexes for the time-range queries below (created after the column migration,
# since the client index needs the newer client_id column).
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_reports_route_time ON reports (route_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_reports_time ON reports (timestamp);
CREATE INDEX IF NOT EXISTS idx_reports_client_bus ON reports (client_id, bus_id, timestamp);
"""

# Columns added after the first release; added to older data.db files on open.
EXTRA_COLUMNS = {
    "alerts": {"donor_route_id": "TEXT", "recommendation": "TEXT", "dispatched_bus_id": "TEXT"},
    "reports": {"client_id": "TEXT NOT NULL DEFAULT 'unknown'"},
}

REPORT_COLUMNS = "route_id, bus_id, level, timestamp, client_id"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_text(moment: datetime) -> str:
    return moment.isoformat(timespec="microseconds")


def _to_datetime(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


class Store:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.open(db_path)

    def open(self, db_path: str) -> None:
        """(Re)open the SQLite database and clear in-memory routes and buses."""
        self.lock = threading.RLock()
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.executescript(SCHEMA)
            self._add_missing_columns()
            self.db.executescript(INDEXES)
        self.routes: dict[str, Route] = {}
        self.buses: dict[str, Bus] = {}

    def reset(self) -> None:
        """Start from an empty in-memory database (used by tests)."""
        self.open(":memory:")

    # --- SQL helpers: the only places that touch the connection ---

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a SELECT and fetch every row while holding the lock."""
        with self.lock:
            return self.db.execute(sql, params).fetchall()

    def _write(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Run an INSERT/UPDATE/ALTER in its own transaction while holding the lock."""
        with self.lock, self.db:
            return self.db.execute(sql, params)

    def _add_missing_columns(self) -> None:
        for table, columns in EXTRA_COLUMNS.items():
            existing = {row["name"] for row in self._query(f"PRAGMA table_info({table})")}
            for column, definition in columns.items():
                if column not in existing:
                    self._write(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

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
        self._write(
            f"INSERT INTO reports ({REPORT_COLUMNS}) VALUES (?, ?, ?, ?, ?)",
            (report.route_id, report.bus_id, report.level, _to_text(report.timestamp), report.client_id),
        )
        if report.bus_id in self.buses:
            self.buses[report.bus_id].density = report.level
        return report

    def reports_for_route(self, route_id: str, since: datetime | None = None) -> list[Report]:
        """Reports of a route, oldest first; only those at or after `since` if given."""
        rows = self._query(
            f"SELECT {REPORT_COLUMNS} FROM reports WHERE route_id = ? AND timestamp >= ? ORDER BY timestamp, id",
            (route_id, _to_text(since) if since else ""),
        )
        return [Report(**dict(row)) for row in rows]

    def reports_since(self, since: datetime) -> list[Report]:
        """Reports of all routes at or after `since`, oldest first (one query for the network)."""
        rows = self._query(
            f"SELECT {REPORT_COLUMNS} FROM reports WHERE timestamp >= ? ORDER BY timestamp, id",
            (_to_text(since),),
        )
        return [Report(**dict(row)) for row in rows]

    def last_report_at(self, route_id: str) -> datetime | None:
        row = self._query("SELECT MAX(timestamp) FROM reports WHERE route_id = ?", (route_id,))[0]
        return _to_datetime(row[0])

    def last_report_times(self) -> dict[str, datetime]:
        """Latest report time of every route, in one query."""
        rows = self._query("SELECT route_id, MAX(timestamp) FROM reports GROUP BY route_id")
        return {row[0]: _to_datetime(row[1]) for row in rows}

    def last_report_time(self, client_id: str, bus_id: str) -> datetime | None:
        """When this client last reported on this bus (for rate limiting)."""
        row = self._query(
            "SELECT MAX(timestamp) FROM reports WHERE client_id = ? AND bus_id = ?", (client_id, bus_id)
        )[0]
        return _to_datetime(row[0])

    # --- Operator alerts (SQLite) ---

    def create_alert(self, route_id: str, message: str, created_at: datetime | None = None,
                     donor_route_id: str | None = None, recommendation: str | None = None) -> Alert:
        cursor = self._write(
            "INSERT INTO alerts (route_id, message, created_at, donor_route_id, recommendation) "
            "VALUES (?, ?, ?, ?, ?)",
            (route_id, message, _to_text(created_at or utcnow()), donor_route_id, recommendation),
        )
        alert = self.get_alert(cursor.lastrowid)
        events.publish("alert", {"action": "created", "alert": alert.model_dump(mode="json")})
        return alert

    def get_alert(self, alert_id: int) -> Alert | None:
        rows = self._query("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        return Alert(**dict(rows[0])) if rows else None

    def active_alert(self, route_id: str) -> Alert | None:
        rows = self._query("SELECT * FROM alerts WHERE route_id = ? AND resolved_at IS NULL", (route_id,))
        return Alert(**dict(rows[0])) if rows else None

    def last_resolved_at(self, route_id: str) -> datetime | None:
        row = self._query("SELECT MAX(resolved_at) FROM alerts WHERE route_id = ?", (route_id,))[0]
        return _to_datetime(row[0])

    def list_alerts(self) -> list[Alert]:
        """Active alerts first, newest first within each group."""
        rows = self._query("SELECT * FROM alerts ORDER BY resolved_at IS NOT NULL, created_at DESC, id DESC")
        return [Alert(**dict(row)) for row in rows]

    def resolve_alert(self, alert_id: int, resolved_at: datetime | None = None,
                      dispatched_bus_id: str | None = None) -> Alert | None:
        """Mark an alert resolved (no-op if already resolved); None if it doesn't exist.
        `dispatched_bus_id` records the bus sent to the route, if any."""
        cursor = self._write(
            "UPDATE alerts SET resolved_at = ?, dispatched_bus_id = ? WHERE id = ? AND resolved_at IS NULL",
            (_to_text(resolved_at or utcnow()), dispatched_bus_id, alert_id),
        )
        alert = self.get_alert(alert_id)
        if cursor.rowcount:  # only announce an actual change
            events.publish("alert", {"action": "resolved", "alert": alert.model_dump(mode="json")})
        return alert


# Shared app-wide instance (in-memory until main.py opens the real database file).
store = Store()
