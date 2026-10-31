"""Pydantic models for routes, stops, buses, density reports, alerts and ETAs."""
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


class Alert(BaseModel):
    """Operator alert; active while `resolved_at` is None."""
    id: int
    route_id: str
    message: str
    created_at: datetime
    resolved_at: datetime | None = None


class RouteDensity(BaseModel):
    """Operator overview of one route's recent passenger reports."""
    route_id: str
    route_name: str
    dominant_level: DensityLevel | None
    counts: dict[str, int]
    bus_count: int
    last_report_at: datetime | None


class BusEta(BaseModel):
    bus_id: str
    route_id: str
    eta_minutes: float
    density: DensityLevel | None
