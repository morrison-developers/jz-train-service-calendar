from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from jz_calendar.models import Classification, DesiredEvent, ParsedAlert

NYC = ZoneInfo("America/New_York")
DISCLAIMER = "Information is sourced from the MTA and may change. Check mta.info before travel."


def event_key(alert_id: str, start: datetime, end: datetime) -> str:
    material = f"{alert_id}|{int(start.timestamp())}|{int(end.timestamp())}".encode()
    return hashlib.sha256(material).hexdigest()[:40]


def _title(header: str, routes: frozenset[str]) -> str:
    prefix = "/".join(route for route in ("J", "Z") if route in routes)
    cleaned = re.sub(r"^\s*(?:\[(?:J|Z|J/Z)\]\s*(?:and\s*)?)+", "", header, flags=re.I)
    cleaned = re.sub(r"\bNo \[(?:J|Z|J/Z)\](?=\s+between)", "No trains", cleaned, flags=re.I)
    return f"[{prefix}] {cleaned.strip()}"[:300]


def build_events(
    alert: ParsedAlert,
    classification: Classification,
    now: datetime | None = None,
) -> list[DesiredEvent]:
    now = now or datetime.now(UTC)
    routes = classification.affected_routes
    station_names = load_names(alert.stations)
    lines = [
        alert.description or alert.header,
        "",
        f"Affected routes: {', '.join(sorted(routes))}",
    ]
    if station_names:
        lines.append(f"Affected stations: {', '.join(station_names)}")
    lines.extend(
        [
            f"MTA alert ID: {alert.alert_id}",
            "Alert last updated: "
            + (
                alert.updated_at.astimezone(NYC).isoformat() if alert.updated_at else "Not supplied"
            ),
        ]
    )
    if alert.source_url:
        lines.append(f"Source: {alert.source_url}")
    lines.extend(["", DISCLAIMER])
    return [
        DesiredEvent(
            key=event_key(alert.alert_id, period.start, period.end),
            alert_id=alert.alert_id,
            title=_title(alert.header, routes),
            description="\n".join(lines),
            start=period.start.astimezone(NYC),
            end=period.end.astimezone(NYC),
            updated_at=alert.updated_at,
            routes=routes,
            stations=alert.stations,
            category=classification.category,  # type: ignore[arg-type]
        )
        for period in alert.periods
        if period.end > now
    ]


def load_names(station_ids: frozenset[str]) -> list[str]:
    from jz_calendar.classifier import load_station_map

    names = load_station_map()
    return sorted({names[station] for station in station_ids if station in names})
