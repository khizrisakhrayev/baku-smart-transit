"""Synthetic background reports and seeded start offsets."""
import random
from collections import Counter

import pytest

from app import config, simulator, synthetic
from app.routes_data import ROUTES
from app.store import Store

PEAK = config.RUSH_PERIOD_MIN * 60 / 2


@pytest.fixture
def db() -> Store:
    db = Store()
    simulator.seed(db, ROUTES)
    return db


def test_synthetic_reports_are_off_in_tests():
    assert config.SYNTHETIC_REPORTS is False


def test_rush_wave_goes_up_and_down():
    assert synthetic.rush_intensity(0) == pytest.approx(0)
    assert synthetic.rush_intensity(PEAK) == pytest.approx(1)
    assert synthetic.rush_intensity(config.RUSH_PERIOD_MIN * 60) == pytest.approx(0)


def test_central_routes_detected():
    central = {r.id for r in ROUTES if synthetic.is_central(r)}
    assert {"1", "5", "H1", "30"} <= central  # 28 May / Gənclik / Koroğlu
    assert "65" not in central and "3" in central  # 3 ends at 28 May


def test_weights_are_probabilities():
    for central in (True, False):
        for intensity in (0, 0.5, 1):
            weights = synthetic.level_weights(central, intensity)
            assert sum(weights.values()) == pytest.approx(1)
            assert all(w >= 0 for w in weights.values())


def test_rush_hour_makes_central_routes_crowded(db):
    reports = synthetic.generate(db, random.Random(1), elapsed_sec=PEAK, count=2000)
    central = Counter(r.level for r in reports if synthetic.is_central(db.routes[r.route_id]))
    outer = Counter(r.level for r in reports if not synthetic.is_central(db.routes[r.route_id]))
    assert central.most_common(1)[0][0] == "high"
    assert outer.most_common(1)[0][0] == "low"


def test_each_synthetic_report_has_its_own_client(db):
    reports = synthetic.generate(db, random.Random(2), elapsed_sec=0, count=50)
    assert len({r.client_id for r in reports}) == 50
    assert all(r.client_id.startswith("sim-") for r in reports)


# --- Seeded start offsets ---

def positions(store: Store) -> dict[str, tuple[int, float]]:
    return {b.id: (b.path_index, b.progress) for b in store.buses.values()}


def test_start_offsets_are_deterministic(db):
    other = Store()
    simulator.seed(other, ROUTES)
    assert positions(db) == positions(other)


def test_routes_do_not_all_start_in_sync(db):
    first_buses = [db.buses[f"{r.id}-1"] for r in ROUTES]
    assert len({(b.path_index, b.progress) for b in first_buses}) > len(ROUTES) // 2


def test_hub_arrivals_are_spread_out(db):
    from app import eta
    minutes = [e.eta_minutes for e in eta.etas_for_stop(db, "28-may")]
    assert len(set(minutes)) > 0.8 * len(minutes)
