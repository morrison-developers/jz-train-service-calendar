from __future__ import annotations

import json
import re
from importlib.resources import files

from jz_calendar.models import Classification, DisruptionCategory, ParsedAlert

SUPPORTED_TYPES: dict[str, DisruptionCategory] = {
    "Planned - Part Suspended": DisruptionCategory.SUSPENSION,
    "Planned - Suspended": DisruptionCategory.SUSPENSION,
    "Planned - Reroute": DisruptionCategory.REROUTE,
    "Planned - Express to Local": DisruptionCategory.SERVICE_PATTERN,
    "Planned - Local to Express": DisruptionCategory.SERVICE_PATTERN,
    "Planned - Stops Skipped": DisruptionCategory.SKIPPED_STATIONS,
    "Reduced Service": DisruptionCategory.REDUCED_SERVICE,
    "Special Schedule": DisruptionCategory.SERVICE_PATTERN,
}

TEXT_CATEGORIES: tuple[tuple[re.Pattern[str], DisruptionCategory], ...] = (
    (
        re.compile(r"\b(skip[- ]stop|z service).{0,45}\b(suspend|not run)", re.I),
        DisruptionCategory.SKIP_STOP_SUSPENDED,
    ),
    (
        re.compile(r"\b(shuttle bus|free shuttle|buses replace)\b", re.I),
        DisruptionCategory.SHUTTLE_BUS,
    ),
    (re.compile(r"\b(terminate|ends? at|last stop)\b", re.I), DisruptionCategory.EARLY_TERMINATION),
    (
        re.compile(r"\b(no trains?|suspend(?:ed|sion)?|not running)\b", re.I),
        DisruptionCategory.SUSPENSION,
    ),
    (re.compile(r"\b(run(?:s|ning)? via|reroute|re-route)\b", re.I), DisruptionCategory.REROUTE),
    (
        re.compile(r"\b(skip(?:s|ping)?|bypass).{0,25}\bstation", re.I),
        DisruptionCategory.SKIPPED_STATIONS,
    ),
    (re.compile(r"\b(express|local service)\b", re.I), DisruptionCategory.SERVICE_PATTERN),
    (
        re.compile(r"\b(every \d+ minutes|reduced service|less frequent)\b", re.I),
        DisruptionCategory.REDUCED_SERVICE,
    ),
)


def load_station_map() -> dict[str, str]:
    path = files("jz_calendar").joinpath("data/jz_stations.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["stop_id"]: item["name"] for item in payload["stations"]}


def _routes_named_in_text(text: str, targets: frozenset[str]) -> frozenset[str]:
    named = {
        route
        for route in targets
        if re.search(
            rf"(?:\[{re.escape(route)}\]|\b{re.escape(route)}(?: trains?| service)\b)", text, re.I
        )
    }
    if re.search(r"\bJ\s*/\s*Z\b|\bJ\s+and\s+Z\b", text, re.I):
        named.update({"J", "Z"} & targets)
    return frozenset(named)


def classify(
    alert: ParsedAlert,
    target_routes: frozenset[str],
    include_realtime: bool = False,
    station_ids: frozenset[str] | None = None,
) -> Classification:
    if not alert.planned_work and not include_realtime:
        return Classification(False, frozenset(), reason="not planned work")
    text = f"{alert.header}\n{alert.description}"
    direct_routes = alert.routes & target_routes
    stations = station_ids if station_ids is not None else frozenset(load_station_map())
    text_routes = _routes_named_in_text(text, target_routes)
    station_fallback = bool(alert.stations & stations and text_routes)
    if not direct_routes and not station_fallback:
        return Classification(False, frozenset(), reason="no structured or explicit J/Z impact")
    affected = direct_routes or text_routes
    category = SUPPORTED_TYPES.get(alert.alert_type)
    if alert.alert_type == "Extra Service" and re.search(r"\bvia (?:the )?\[?J\]?\b", text, re.I):
        category = DisruptionCategory.REROUTE
    for pattern, fallback_category in TEXT_CATEGORIES:
        if pattern.search(text):
            if fallback_category == DisruptionCategory.SKIP_STOP_SUSPENDED or category is None:
                category = fallback_category
            break
    if category is None:
        return Classification(False, affected, reason="not a material disruption category")
    return Classification(True, affected, category, "material J/Z planned service change")
