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
SIM_SEED = int(os.getenv("SIM_SEED", "42"))  # random start offsets; same seed = same layout

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

# --- Synthetic background reports (demo traffic, see synthetic.py) ---
SYNTHETIC_REPORTS = os.getenv("SYNTHETIC_REPORTS", "1") == "1"
SYNTHETIC_INTERVAL_SEC = 5
SYNTHETIC_REPORTS_PER_TICK = 5
# Rush-hour wave length: builds for half, eases for half. Demo: 6 (early warnings in ~2 min).
RUSH_PERIOD_MIN = float(os.getenv("RUSH_PERIOD_MIN", "30"))
CENTRAL_STOP_IDS = ("28-may", "koroglu", "genclik")

# --- Forecast (see forecast.py) ---
FORECAST_BUCKET_SEC = 60  # one-minute buckets...
FORECAST_BUCKETS = 10     # ...over the last 10 minutes
FORECAST_HORIZON_MIN = 15
TREND_THRESHOLD = 0.05    # score change per minute that counts as rising/falling

# --- Analytics (see analytics.py) ---
ANALYTICS_MINUTES = 30
ANALYTICS_TOP_ROUTES = 10

# --- Live stream (Server-Sent Events, see events.py) ---
STREAM_KEEPALIVE_SEC = 15  # comment line sent when nothing else happened

# --- Report trust ---
REPORT_COOLDOWN_SEC = 60  # one report per client per bus per minute
# Proximity check: reject a report whose location is farther than this from the bus.
# 0 = disabled (default): bus positions are simulated, so a real phone is never near them.
# With real bus GPS, set e.g. MAX_REPORT_DISTANCE_M=500 to enable it.
MAX_REPORT_DISTANCE_M = float(os.getenv("MAX_REPORT_DISTANCE_M", "0"))
CONFIDENT_CLIENTS = 5     # unique reporters needed for full confidence
