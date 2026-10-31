"""Anomaly rule tests using fake timestamps (no sleeping)."""
from datetime import datetime, timedelta, timezone

import pytest

from app import anomaly, config
from app.models import Report, ReportIn
from app.routes_data import ROUTES
from app.store import Store

T0 = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
WINDOW = 600  # 10 minutes


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def reports(*items: tuple[str, float]) -> list[Report]:
    """Build reports from (level, minutes after T0) pairs."""
    return [Report(client_id="test", route_id="5", bus_id="5-1", level=level, timestamp=at(m)) for level, m in items]


# --- Pure rule ---

def test_three_high_spanning_window_is_anomalous():
    assert anomaly.is_anomalous(reports(("high", 0), ("high", 5), ("high", 10)), WINDOW)


def test_span_shorter_than_window_is_not():
    assert not anomaly.is_anomalous(reports(("high", 0), ("high", 5), ("high", 9.9)), WINDOW)


def test_fewer_than_three_reports_is_not():
    assert not anomaly.is_anomalous(reports(("high", 0), ("high", 20)), WINDOW)


def test_medium_in_between_breaks_the_run():
    data = reports(("high", 0), ("medium", 5), ("high", 10), ("high", 11))
    assert not anomaly.is_anomalous(data, WINDOW)


def test_latest_report_not_high_is_not():
    data = reports(("high", 0), ("high", 5), ("high", 10), ("low", 11))
    assert not anomaly.is_anomalous(data, WINDOW)


def test_run_after_earlier_low_is_anomalous():
    data = reports(("low", -5), ("high", 0), ("high", 5), ("high", 10))
    assert anomaly.is_anomalous(data, WINDOW)


def test_no_reports_is_not():
    assert not anomaly.is_anomalous([], WINDOW)


# --- Alerts via the store ---

@pytest.fixture
def store(monkeypatch) -> Store:
    monkeypatch.setattr(config, "ANOMALY_WINDOW_SEC", WINDOW)
    return Store()


def add(store: Store, level: str, minutes: float, route_id: str = "5") -> None:
    store.add_report(ReportIn(client_id="test", route_id=route_id, bus_id="x", level=level), timestamp=at(minutes))


def add_high_run(store: Store, start: float = 0, route_id: str = "5") -> None:
    for m in (start, start + 5, start + 10):
        add(store, "high", m, route_id)


def test_alert_created_with_message_and_time(store):
    add_high_run(store)
    alert = anomaly.check_route(store, "5", now=at(10))
    assert alert.route_id == "5"
    assert alert.message == "Əlavə avtobus ehtiyatı ayrılmalıdır"
    assert alert.created_at == at(10)
    assert alert.resolved_at is None


def test_no_duplicate_active_alert(store):
    add_high_run(store)
    assert anomaly.check_route(store, "5", now=at(10))
    add(store, "high", 11)
    assert anomaly.check_route(store, "5", now=at(11)) is None
    assert len(store.list_alerts()) == 1


def test_no_alert_when_not_anomalous(store):
    add(store, "high", 0)
    add(store, "high", 2)
    add(store, "high", 4)
    assert anomaly.check_route(store, "5", now=at(4)) is None


def test_resolved_alert_not_reopened_without_new_report(store):
    add_high_run(store)
    alert = anomaly.check_route(store, "5", now=at(10))
    store.resolve_alert(alert.id, resolved_at=at(12))
    assert anomaly.check_route(store, "5", now=at(13)) is None


def test_new_high_report_after_resolve_reopens(store):
    add_high_run(store)
    alert = anomaly.check_route(store, "5", now=at(10))
    store.resolve_alert(alert.id, resolved_at=at(12))
    add(store, "high", 14)
    new_alert = anomaly.check_route(store, "5", now=at(14))
    assert new_alert is not None and new_alert.id != alert.id


def test_check_all_covers_every_route(store):
    for route in ROUTES:
        store.add_route(route)
    add_high_run(store, route_id="1")
    add_high_run(store, route_id="88")
    alerts = anomaly.check_all(store, now=at(10))
    assert sorted(a.route_id for a in alerts) == ["1", "88"]


def test_alerts_listed_active_first(store):
    add_high_run(store, route_id="1")
    add_high_run(store, route_id="5")
    first = anomaly.check_route(store, "1", now=at(10))
    anomaly.check_route(store, "5", now=at(11))
    store.resolve_alert(first.id, resolved_at=at(12))
    listed = store.list_alerts()
    assert [a.route_id for a in listed] == ["5", "1"]
    assert listed[0].resolved_at is None


def test_reports_persist_in_sqlite_file(tmp_path):
    db_file = str(tmp_path / "test.db")
    Store(db_file).add_report(ReportIn(client_id="test", route_id="5", bus_id="5-1", level="low"), timestamp=T0)
    reopened = Store(db_file)
    assert [r.level for r in reopened.reports_for_route("5")] == ["low"]
    assert reopened.reports_for_route("5")[0].timestamp == T0


# --- Pending ("being watched") status ---

def test_pending_status_counts_run_and_time_left():
    data = reports(("low", 0), ("high", 1), ("high", 3))
    count, seconds = anomaly.pending_status(data, WINDOW, now=at(4))
    assert count == 2
    assert seconds == pytest.approx(7 * 60)  # run started at minute 1, window ends at minute 11


def test_pending_status_resets_after_non_high_report():
    data = reports(("high", 0), ("high", 2), ("medium", 3), ("high", 4))
    assert anomaly.pending_status(data, WINDOW, now=at(4)) == (1, pytest.approx(10 * 60))


def test_pending_status_none_when_latest_is_not_high():
    assert anomaly.pending_status(reports(("high", 0), ("low", 1)), WINDOW, now=at(2)) is None
    assert anomaly.pending_status([], WINDOW, now=at(0)) is None


def test_pending_seconds_never_negative():
    count, seconds = anomaly.pending_status(reports(("high", 0), ("high", 12)), WINDOW, now=at(13))
    assert (count, seconds) == (2, 0)  # window reached; it only needs a 3rd report


@pytest.fixture
def network(store) -> Store:
    for route in ROUTES:
        store.add_route(route)
    return store


def test_pending_lists_watched_routes(network):
    add(network, "high", 0, "5")
    add(network, "high", 2, "88")
    add(network, "low", 2, "1")
    summary = anomaly.pending(network, now=at(3))
    assert (summary.window_sec, summary.required_reports) == (WINDOW, config.MIN_HIGH_REPORTS)
    by_route = {p.route_id: p for p in summary.routes}
    assert set(by_route) == {"5", "88"}
    assert (by_route["5"].high_reports, by_route["5"].seconds_remaining) == (1, 7 * 60)
    assert by_route["88"].seconds_remaining == 9 * 60


def test_pending_skips_routes_with_active_alert(network):
    add_high_run(network, route_id="5")
    anomaly.check_route(network, "5", now=at(10))
    assert anomaly.pending(network, now=at(11)).routes == []


def test_pending_skips_handled_run_until_new_report(network):
    add_high_run(network, route_id="5")
    alert = anomaly.check_route(network, "5", now=at(10))
    network.resolve_alert(alert.id, resolved_at=at(11))
    assert anomaly.pending(network, now=at(12)).routes == []
    add(network, "high", 13, "5")  # a new high report: the route is watched again
    assert [p.route_id for p in anomaly.pending(network, now=at(13)).routes] == ["5"]
