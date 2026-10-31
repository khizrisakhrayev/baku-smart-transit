"""FastAPI entry point: API routes + static frontend.

Run from the backend/ folder:  uvicorn app.main:app --reload
"""
import asyncio
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app import anomaly, density, dispatch, eta, simulator
from app.models import Alert, Bus, BusEta, Report, ReportIn, Route, RouteDensity, Stop
from app.routes_data import ROUTES
from app.store import store, utcnow

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parents[1] / "data.db"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database, seed routes/buses, and run the background loops."""
    store.open(DB_PATH)
    simulator.seed(store, ROUTES)
    tasks = [
        asyncio.create_task(simulator.run(store)),
        asyncio.create_task(anomaly.run(store)),
    ]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="Baku Smart Transit", lifespan=lifespan)


def get_route_or_404(route_id: str) -> Route:
    route = store.routes.get(route_id)
    if route is None:
        raise HTTPException(404, "Marşrut tapılmadı")
    return route


@app.get("/api/health")
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


# --- Passenger API ---

@app.get("/api/routes")
def list_routes() -> list[Route]:
    return list(store.routes.values())


@app.get("/api/buses")
def list_buses(route_id: str | None = None) -> list[Bus]:
    """All buses, or only those of `route_id` if given."""
    if route_id is not None:
        return store.buses_on_route(route_id)
    return list(store.buses.values())


@app.get("/api/stops")
def list_stops(route_id: str) -> list[Stop]:
    return get_route_or_404(route_id).stops


@app.get("/api/stops/{stop_id}/eta")
def stop_eta(stop_id: str) -> list[BusEta]:
    if not store.routes_with_stop(stop_id):
        raise HTTPException(404, "Dayanacaq tapılmadı")
    return eta.etas_for_stop(store, stop_id)


@app.post("/api/reports", status_code=201)
def create_report(report_in: ReportIn) -> Report:
    bus = store.buses.get(report_in.bus_id)
    if bus is None or bus.route_id != report_in.route_id:
        raise HTTPException(422, "Avtobus bu marşruta aid deyil")
    report = store.add_report(report_in)
    anomaly.check_route(store, report.route_id)
    return report


# --- Operator API ---

@app.get("/api/operator/density")
def operator_density() -> list[RouteDensity]:
    return density.summary(store)


@app.get("/api/operator/alerts")
def operator_alerts() -> list[Alert]:
    return store.list_alerts()


@app.post("/api/operator/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int) -> Alert:
    alert = store.resolve_alert(alert_id)
    if alert is None:
        raise HTTPException(404, "Xəbərdarlıq tapılmadı")
    return alert


@app.post("/api/operator/alerts/{alert_id}/dispatch")
def dispatch_alert(alert_id: int) -> dict:
    """Confirm the alert's recommendation: move one bus from the donor route and resolve."""
    alert = store.get_alert(alert_id)
    if alert is None:
        raise HTTPException(404, "Xəbərdarlıq tapılmadı")
    try:
        resolved, bus = dispatch.dispatch_bus(store, alert)
    except dispatch.DispatchError as error:
        raise HTTPException(409, str(error))
    return {"alert": resolved, "bus": bus}


# --- Demo helper ---

@app.post("/api/demo/flood-high")
def demo_flood_high(route_id: str) -> dict:
    """Add backdated "high" reports so the alert fires right away instead of after
    waiting the full window: one at the window start (so the high run spans the whole
    window) plus MIN_HIGH_REPORTS spread inside it (so the density overview counts them)."""
    get_route_or_404(route_id)
    buses = store.buses_on_route(route_id)
    window = anomaly.ANOMALY_WINDOW_SEC
    count = anomaly.MIN_HIGH_REPORTS
    ages = [window * k / count for k in range(count, -1, -1)]  # e.g. 600, 400, 200, 0 s
    now = utcnow()
    for i, age in enumerate(ages):
        report_in = ReportIn(route_id=route_id, bus_id=buses[i % len(buses)].id, level="high")
        store.add_report(report_in, timestamp=now - timedelta(seconds=age))
    alert = anomaly.check_route(store, route_id, now)
    return {"reports_added": len(ages), "alert": alert}


# Mounted last so /api/* routes take priority over static files.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
