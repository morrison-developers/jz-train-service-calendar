from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from jz_calendar.calendar_client import CalendarClient, event_body
from jz_calendar.models import DesiredEvent, SyncResult


def _private(event: dict[str, Any]) -> dict[str, str]:
    return event.get("extendedProperties", {}).get("private", {})


def _changed(existing: dict[str, Any], desired: DesiredEvent) -> bool:
    body = event_body(desired)
    return any(
        (
            existing.get("summary") != body["summary"],
            existing.get("description") != body["description"],
            existing.get("start", {}).get("dateTime") != body["start"]["dateTime"],
            existing.get("end", {}).get("dateTime") != body["end"]["dateTime"],
            _private(existing).get("mtaUpdatedAt")
            != body["extendedProperties"]["private"]["mtaUpdatedAt"],
        )
    )


def synchronize(
    client: CalendarClient,
    desired_events: list[DesiredEvent],
    *,
    dry_run: bool = False,
    now: datetime | None = None,
) -> SyncResult:
    log = logging.getLogger(__name__)
    now = now or datetime.now(UTC)
    existing_list = list(client.managed_events(now.isoformat()))
    existing: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for item in existing_list:
        key = _private(item).get("eventKey")
        if not key:
            continue
        if key in existing:
            duplicates.append(item)
        else:
            existing[key] = item
    desired = {event.key: event for event in desired_events}
    creates = updates = deletes = unchanged = 0
    for key, event in desired.items():
        current = existing.get(key)
        if current is None:
            creates += 1
            log.info(
                "calendar_create",
                extra={
                    "event": "calendar_create",
                    "key": key,
                    "title": event.title,
                    "dry_run": dry_run,
                },
            )
            if not dry_run:
                client.create(event)
        elif _changed(current, event):
            updates += 1
            log.info(
                "calendar_update",
                extra={
                    "event": "calendar_update",
                    "key": key,
                    "title": event.title,
                    "dry_run": dry_run,
                },
            )
            if not dry_run:
                client.update(current["id"], event)
        else:
            unchanged += 1
    obsolete = [item for key, item in existing.items() if key not in desired]
    obsolete.extend(duplicates)
    for item in obsolete:
        end_value = item.get("end", {}).get("dateTime")
        if not end_value:
            continue
        end = datetime.fromisoformat(end_value.replace("Z", "+00:00"))
        if end <= now:
            continue
        deletes += 1
        log.info(
            "calendar_delete",
            extra={
                "event": "calendar_delete",
                "google_event_id": item.get("id"),
                "dry_run": dry_run,
            },
        )
        if not dry_run:
            client.delete(item["id"])
    return SyncResult(creates, updates, deletes, unchanged)
