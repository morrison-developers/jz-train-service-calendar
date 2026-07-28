from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jz_calendar.calendar_client import event_body
from jz_calendar.models import DesiredEvent, DisruptionCategory
from jz_calendar.sync import synchronize

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def desired(key: str = "key", updated: datetime | None = NOW) -> DesiredEvent:
    return DesiredEvent(
        key=key,
        alert_id="lmm:planned_work:1",
        title="[J] No trains",
        description="Details",
        start=NOW + timedelta(days=1),
        end=NOW + timedelta(days=2),
        updated_at=updated,
        routes=frozenset({"J"}),
        stations=frozenset(),
        category=DisruptionCategory.SUSPENSION,
    )


def google_event(event: DesiredEvent, event_id: str = "google-1") -> dict[str, Any]:
    return {"id": event_id, **event_body(event)}


class FakeCalendar:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = events
        self.created = []
        self.updated = []
        self.deleted = []

    def managed_events(self, time_min: str):
        yield from self.events

    def create(self, event):
        self.created.append(event)
        return {}

    def update(self, event_id, event):
        self.updated.append((event_id, event))
        return {}

    def delete(self, event_id):
        self.deleted.append(event_id)


def test_alert_updated_after_creation():
    old = desired(updated=NOW - timedelta(hours=1))
    new = desired(updated=NOW)
    calendar = FakeCalendar([google_event(old)])
    result = synchronize(calendar, [new], now=NOW)
    assert result.updates == 1
    assert calendar.updated[0][0] == "google-1"


def test_alert_removed_before_scheduled_date():
    calendar = FakeCalendar([google_event(desired())])
    result = synchronize(calendar, [], now=NOW)
    assert result.deletes == 1
    assert calendar.deleted == ["google-1"]


def test_historical_removed_event_is_preserved():
    event = google_event(desired())
    event["end"]["dateTime"] = (NOW - timedelta(days=1)).isoformat()
    calendar = FakeCalendar([event])
    result = synchronize(calendar, [], now=NOW)
    assert result.deletes == 0


def test_idempotent_noop():
    event = desired()
    calendar = FakeCalendar([google_event(event)])
    result = synchronize(calendar, [event], now=NOW)
    assert result.unchanged == 1
    assert not calendar.created and not calendar.updated and not calendar.deleted


def test_dry_run_reports_without_mutating():
    calendar = FakeCalendar([])
    result = synchronize(calendar, [desired()], now=NOW, dry_run=True)
    assert result.creates == 1
    assert not calendar.created
