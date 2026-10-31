"""All tunable settings in one place. Env vars override the ones useful for demos.

Modules read these as `config.NAME` at call time, so tests can monkeypatch them.
"""
import os
from pathlib import Path

# --- Storage ---
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parents[1] / "data.db"))

# --- GPS simulator ---
TICK_SECONDS = 2.0       # buses move every 2s
STEPS_PER_SEGMENT = 5    # ticks to get from one stop to the next (10s)
BUSES_PER_ROUTE = 3

# --- ETA display ---
# The simulator runs fast so the demo map stays lively; passengers see realistic times:
# each simulated second counts as SIM_TIME_SCALE real seconds (one segment = 2.5 min).
SIM_TIME_SCALE = 15

# --- Anomaly detection ---
ANOMALY_WINDOW_SEC = int(os.getenv("ANOMALY_WINDOW_SEC", "600"))  # demo: 30
MIN_HIGH_REPORTS = 3
CHECK_INTERVAL_SEC = 10

# --- Smart dispatch ---
MIN_DONOR_BUSES = 3

# --- Passenger alternatives ---
MAX_EXTRA_WAIT_MIN = 10    # suggest a less crowded bus only if it's at most this much later
COMFORT_HORIZON_MIN = 15   # "Ən rahat seçim" considers buses arriving within this time

# --- Report trust ---
REPORT_COOLDOWN_SEC = 60  # one report per client per bus per minute
MAX_REPORT_DISTANCE_M = float(os.getenv("MAX_REPORT_DISTANCE_M", "500"))  # 0 disables the check
CONFIDENT_CLIENTS = 5     # unique reporters needed for full confidence
