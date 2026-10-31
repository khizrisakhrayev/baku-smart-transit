"""FastAPI entry point: API routes + static frontend.

Run from the backend/ folder:  uvicorn app.main:app --reload
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="Baku Smart Transit")


@app.get("/api/health")
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


# Mounted last so /api/* routes take priority over static files.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
