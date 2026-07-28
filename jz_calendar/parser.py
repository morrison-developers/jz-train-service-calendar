from __future__ import annotations

from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any

from jz_calendar.models import ActivePeriod, ParsedAlert

MERCURY_ALERT = "transit_realtime.mercury_alert"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_html(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return " ".join(unescape("".join(parser.parts)).split())


def _translation(field: object) -> str:
    if not isinstance(field, dict):
        return ""
    translations = field.get("translation")
    if not isinstance(translations, list):
        return ""
    candidates = [item for item in translations if isinstance(item, dict)]
    for language in ("en", "en-html", ""):
        for item in candidates:
            if item.get("language", "") == language and isinstance(item.get("text"), str):
                text = item["text"]
                return _plain_html(text) if "html" in language else text.strip()
    return ""


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, UTC)
    return None


def parse_feed(payload: dict[str, Any]) -> list[ParsedAlert]:
    parsed: list[ParsedAlert] = []
    for entity in payload["entity"]:
        if not isinstance(entity, dict) or not isinstance(entity.get("alert"), dict):
            continue
        alert = entity["alert"]
        raw_id = str(entity.get("id", ""))
        extension = alert.get(MERCURY_ALERT, {})
        extension = extension if isinstance(extension, dict) else {}
        periods: list[ActivePeriod] = []
        for raw_period in alert.get("active_period", []):
            if not isinstance(raw_period, dict):
                continue
            start = _timestamp(raw_period.get("start"))
            end = _timestamp(raw_period.get("end"))
            if start and end and end > start:
                periods.append(ActivePeriod(start=start, end=end))
        routes: set[str] = set()
        stations: set[str] = set()
        for informed in alert.get("informed_entity", []):
            if not isinstance(informed, dict):
                continue
            if informed.get("route_id"):
                routes.add(str(informed["route_id"]).upper())
            if informed.get("stop_id"):
                stations.add(str(informed["stop_id"]).removesuffix("N").removesuffix("S"))
        source_url = _translation(alert.get("url")) or None
        parsed.append(
            ParsedAlert(
                alert_id=raw_id,
                alert_type=str(extension.get("alert_type", "")),
                header=_translation(alert.get("header_text")),
                description=_translation(alert.get("description_text")),
                routes=frozenset(routes),
                stations=frozenset(stations),
                periods=tuple(periods),
                updated_at=_timestamp(extension.get("updated_at")),
                source_url=source_url,
                planned_work=":planned_work:" in raw_id,
            )
        )
    return parsed
