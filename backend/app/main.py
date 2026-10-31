"""FastAPI entry point: API routes + static frontend.

Run from the backend/ folder:  uvicorn app.main:app --reload
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import simulator
from app.models import Bus, Route
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


# Mounted last so /api/* routes take priority over static files.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
