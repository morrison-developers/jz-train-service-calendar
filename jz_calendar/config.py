from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be true or false")
    return normalized in {"true", "1", "yes"}


@dataclass(frozen=True)
class Settings:
    calendar_id: str
    service_account_json: str
    target_routes: frozenset[str]
    include_realtime: bool
    dry_run: bool
    log_level: str

    @classmethod
    def from_env(cls, *, require_google: bool = True) -> Settings:
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "")
        credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if require_google and not calendar_id:
            raise ValueError("GOOGLE_CALENDAR_ID is required")
        routes = frozenset(
            route.strip().upper()
            for route in os.getenv("TARGET_ROUTES", "J,Z").split(",")
            if route.strip()
        )
        if not routes:
            raise ValueError("TARGET_ROUTES cannot be empty")
        return cls(
            calendar_id,
            credentials,
            routes,
            _bool("INCLUDE_REALTIME_ALERTS", False),
            _bool("DRY_RUN", False),
            os.getenv("LOG_LEVEL", "INFO").upper(),
        )
