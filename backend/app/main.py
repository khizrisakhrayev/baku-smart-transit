"""FastAPI entry point: API routes + static frontend.

Run from the backend/ folder:  uvicorn app.main:app --reload
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app import eta, simulator
from app.models import Bus, BusEta, Report, ReportIn, Route, Stop
from app.routes_data import ROUTES
from app.store import store

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seed routes/buses and run the GPS simulator while the app is up."""
    simulator.seed(store, ROUTES)
    task = asyncio.create_task(simulator.run(store))
    yield
    task.cancel()


app = FastAPI(title="Baku Smart Transit", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


@app.get("/api/routes")
def list_routes() -> list[Route]:
    return list(store.routes.values())


@app.get("/api/buses")
def list_buses() -> list[Bus]:
    return list(store.buses.values())


@app.get("/api/stops")
def list_stops(route_id: str) -> list[Stop]:
    route = store.routes.get(route_id)
    if route is None:
        raise HTTPException(404, "Marşrut tapılmadı")
    return route.stops


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
    return store.add_report(report_in)


# Mounted last so /api/* routes take priority over static files.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
