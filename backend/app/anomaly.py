"""Sliding-window anomaly detection on crowd density reports.

If a route stays "high" for ANOMALY_WINDOW_SEC (default 600), raise an operator alert.
"""
import os

ANOMALY_WINDOW_SEC = int(os.getenv("ANOMALY_WINDOW_SEC", "600"))
ALERT_MESSAGE = "Əlavə avtobus ehtiyatı ayrılmalıdır"
