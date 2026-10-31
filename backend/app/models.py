"""Pydantic models for routes, stops, buses, density reports and ETAs."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DensityLevel = Literal["low", "medium", "high"]


class Stop(BaseModel):
    id: str
    name: str
    lat: float
    lon: float


class Route(BaseModel):
    id: str
    name: str
    stops: list[Stop]


class Bus(BaseModel):
    """A simulated bus.

    `path_index` points into the route's round-trip path (see simulator.route_path):
    the bus is between path[path_index] and the next stop, `progress` (0..1) of the way.
    `density` is the latest crowd level reported by passengers (None = no reports yet).
    """
    id: str
    route_id: str
    path_index: int = 0
    progress: float = 0.0
    lat: float
    lon: float
    density: DensityLevel | None = None


class ReportIn(BaseModel):
    """Passenger density report, as submitted."""
    route_id: str
    bus_id: str
    level: DensityLevel


class Report(ReportIn):
    timestamp: datetime


class BusEta(BaseModel):
    bus_id: str
    route_id: str
    eta_minutes: float
    density: DensityLevel | None
