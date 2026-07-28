from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DisruptionCategory(StrEnum):
    SUSPENSION = "suspension"
    REROUTE = "reroute"
    SERVICE_PATTERN = "service_pattern"
    EARLY_TERMINATION = "early_termination"
    SKIPPED_STATIONS = "skipped_stations"
    SHUTTLE_BUS = "shuttle_bus"
    REDUCED_SERVICE = "reduced_service"
    SKIP_STOP_SUSPENDED = "skip_stop_suspended"


@dataclass(frozen=True)
class ActivePeriod:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class ParsedAlert:
    alert_id: str
    alert_type: str
    header: str
    description: str
    routes: frozenset[str]
    stations: frozenset[str]
    periods: tuple[ActivePeriod, ...]
    updated_at: datetime | None
    source_url: str | None
    planned_work: bool


@dataclass(frozen=True)
class Classification:
    included: bool
    affected_routes: frozenset[str]
    category: DisruptionCategory | None = None
    reason: str = ""


@dataclass(frozen=True)
class DesiredEvent:
    key: str
    alert_id: str
    title: str
    description: str
    start: datetime
    end: datetime
    updated_at: datetime | None
    routes: frozenset[str]
    stations: frozenset[str]
    category: DisruptionCategory


@dataclass(frozen=True)
class SyncResult:
    creates: int = 0
    updates: int = 0
    deletes: int = 0
    unchanged: int = 0
