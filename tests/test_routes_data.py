"""Sanity checks for the static route network."""
from collections import Counter

from app import config
from app.routes_data import ROUTE_DATA, ROUTES, STOP_DATA, STOPS


def test_stop_ids_are_unique():
    duplicates = [i for i, n in Counter(s[0] for s in STOP_DATA).items() if n > 1]
    assert duplicates == []


def test_stop_names_are_unique():
    duplicates = [i for i, n in Counter(s[1] for s in STOP_DATA).items() if n > 1]
    assert duplicates == []


def test_every_route_references_existing_stops():
    missing = {(route_id, s) for route_id, stop_ids in ROUTE_DATA for s in stop_ids if s not in STOPS}
    assert missing == set()


def test_every_stop_is_used_by_a_route():
    used = {s for _, stop_ids in ROUTE_DATA for s in stop_ids}
    assert set(STOPS) - used == set()


def test_network_size():
    assert len(ROUTES) == 25
    assert 80 <= len(STOPS) <= 120
    assert all(8 <= len(route.stops) <= 12 for route in ROUTES)


def test_route_ids_unique_and_no_repeated_stops_within_a_route():
    assert len({r.id for r in ROUTES}) == len(ROUTES)
    for route in ROUTES:
        ids = [s.id for s in route.stops]
        assert len(ids) == len(set(ids)), route.id


def test_stops_are_in_baku_area():
    for stop in STOPS.values():
        assert 40.25 < stop.lat < 40.60 and 49.65 < stop.lon < 50.15, stop.id


def test_routes_share_hub_stops():
    for hub in ("28-may", "sahil", "koroglu", "genclik", "nizami", "elmler", "icerisheher"):
        assert sum(hub in stop_ids for _, stop_ids in ROUTE_DATA) >= 2, hub


def test_busy_routes_get_bigger_fleets():
    hubs = {"28-may", "koroglu", "genclik", "nizami"}
    for route in ROUTES:
        hub_count = len(hubs & {s.id for s in route.stops})
        expected = 5 if hub_count >= 2 else 4 if hub_count == 1 else config.BUSES_PER_ROUTE
        assert route.bus_count == expected, route.id
